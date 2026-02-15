#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from src.app.service import QAService
from src.config.settings import load_settings
from src.eval.dataset import load_eval_dataset


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, report: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# Holdout Error Analysis Report")
    lines.append("")
    lines.append("## Summary")
    summary = report["summary"]
    lines.append(f"- Total items: {summary['total_items']}")
    lines.append(f"- Positive items: {summary['positive_items']}")
    lines.append(f"- Negative items: {summary['negative_items']}")
    lines.append(f"- Retrieval Recall@k: {summary['retrieval_recall_at_k']:.4f}")
    lines.append(f"- False refusal rate (positive queries): {summary['false_refusal_rate']:.4f}")
    lines.append(f"- Hallucination rate on negative queries: {summary['negative_hallucination_rate']:.4f}")
    lines.append("")

    lines.append("## Failure Counts")
    for key, value in sorted(report["failure_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Failures By Query Type")
    for key, value in sorted(report["failures_by_query_type"].items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Failures By Difficulty")
    for key, value in sorted(report["failures_by_difficulty"].items()):
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Sample Failures")
    samples = report.get("failure_samples", {})
    if not samples:
        lines.append("- No failures found.")
    else:
        for failure_type, rows in sorted(samples.items()):
            lines.append(f"### {failure_type}")
            for row in rows:
                lines.append(f"- `{row['id']}` | {row['query_type']} | {row['difficulty']} | {row['domain']}")
                lines.append(f"  - Question: {row['question']}")
                lines.append(f"  - Gold: {row['gold_chunk_ids']}")
                lines.append(f"  - Retrieved: {row['retrieved_ids']}")
                lines.append(f"  - Status: {row['answer_status']} | Confidence: {row['confidence']}")
                lines.append(f"  - Citations: {row['citation_ids']}")
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def build_report(config_path: Path, dataset_path: Path, top_k: int, sample_limit: int) -> Dict[str, Any]:
    settings = load_settings(config_path)
    service = QAService(settings)
    items = load_eval_dataset(dataset_path)

    total_items = len(items)
    positive_items = sum(1 for item in items if item.gold_chunk_ids)
    negative_items = total_items - positive_items

    retrieval_hits_on_positive = 0
    false_refusals = 0
    negative_hallucinations = 0

    failure_counts: Counter[str] = Counter()
    failures_by_query_type: Counter[str] = Counter()
    failures_by_difficulty: Counter[str] = Counter()
    failure_samples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for item in items:
        search_payload = service.search(
            query=item.question,
            top_k=top_k,
            department_filter=None,
            access_level="restricted",
            debug=False,
        )
        retrieved_ids = [hit["chunk_id"] for hit in search_payload.get("hits", [])]

        answer = service.ask(
            question=item.question,
            top_k=top_k,
            department_filter=None,
            access_level="restricted",
            debug=False,
        )
        answer_payload = answer.to_dict()
        citations = answer_payload.get("citations", []) or []
        citation_ids = [c.get("chunk_id") for c in citations if c.get("chunk_id")]

        is_positive = len(item.gold_chunk_ids) > 0
        query_type = item.query_type
        difficulty = item.difficulty
        domain = item.domain or "General"

        def record_failure(failure_type: str) -> None:
            failure_counts[failure_type] += 1
            failures_by_query_type[query_type] += 1
            failures_by_difficulty[difficulty] += 1
            if len(failure_samples[failure_type]) < sample_limit:
                failure_samples[failure_type].append(
                    {
                        "id": item.id,
                        "question": item.question,
                        "gold_chunk_ids": item.gold_chunk_ids,
                        "retrieved_ids": retrieved_ids,
                        "answer_status": answer_payload.get("status"),
                        "confidence": answer_payload.get("confidence"),
                        "citation_ids": citation_ids,
                        "query_type": query_type,
                        "difficulty": difficulty,
                        "domain": domain,
                    }
                )

        if is_positive:
            retrieval_hit = any(chunk_id in set(item.gold_chunk_ids) for chunk_id in retrieved_ids)
            if retrieval_hit:
                retrieval_hits_on_positive += 1
            else:
                record_failure("retrieval_miss_positive")

            if answer_payload.get("status") == "NOT_FOUND":
                false_refusals += 1
                record_failure("false_refusal_positive")
            else:
                if not citation_ids:
                    record_failure("missing_citations_positive")
                elif not any(cid in set(item.gold_chunk_ids) for cid in citation_ids):
                    record_failure("citation_mismatch_positive")
        else:
            if answer_payload.get("status") != "NOT_FOUND":
                negative_hallucinations += 1
                record_failure("answered_negative_query")
            if citation_ids:
                record_failure("citations_on_negative_query")

    retrieval_recall = retrieval_hits_on_positive / max(1, positive_items)
    false_refusal_rate = false_refusals / max(1, positive_items)
    negative_hallucination_rate = negative_hallucinations / max(1, negative_items)

    report: Dict[str, Any] = {
        "summary": {
            "total_items": total_items,
            "positive_items": positive_items,
            "negative_items": negative_items,
            "top_k": top_k,
            "retrieval_recall_at_k": retrieval_recall,
            "false_refusal_rate": false_refusal_rate,
            "negative_hallucination_rate": negative_hallucination_rate,
        },
        "failure_counts": dict(sorted(failure_counts.items())),
        "failures_by_query_type": dict(sorted(failures_by_query_type.items())),
        "failures_by_difficulty": dict(sorted(failures_by_difficulty.items())),
        "failure_samples": {k: v for k, v in sorted(failure_samples.items())},
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate holdout error analysis report.")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--dataset", default="data/eval/qa_eval_holdout.jsonl")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--sample_limit", type=int, default=5)
    parser.add_argument("--output_json", default="artifacts/holdout_error_report.json")
    parser.add_argument("--output_md", default="artifacts/holdout_error_report.md")
    args = parser.parse_args()

    report = build_report(
        config_path=Path(args.config),
        dataset_path=Path(args.dataset),
        top_k=args.top_k,
        sample_limit=args.sample_limit,
    )

    json_path = Path(args.output_json)
    md_path = Path(args.output_md)
    _write_json(json_path, report)
    _write_markdown(md_path, report)

    print(f"Wrote JSON report -> {json_path}")
    print(f"Wrote Markdown report -> {md_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
