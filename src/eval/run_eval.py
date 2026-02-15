from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.app.service import QAService
from src.config.settings import load_settings
from src.eval.dataset import EvalItem, load_eval_dataset
from src.eval.metrics import aggregate_retrieval_metrics, mrr, recall_at_k
from src.retrieval.hybrid import fuse_hits


def _retrieve_ids(service: QAService, question: str, top_k: int, mode: str) -> List[str]:
    if mode == "bm25":
        hits = service.bm25.retrieve(question, top_k=top_k, department_filter=None, access_level="restricted")
        return [h.chunk_ref.chunk_id for h in hits]
    if mode == "dense":
        hits = service.dense.retrieve(question, top_k=top_k, department_filter=None, access_level="restricted")
        return [h.chunk_ref.chunk_id for h in hits]
    if mode == "hybrid":
        hits, _ = service.retrieval.retrieve(
            query=question,
            top_k=top_k,
            department_filter=None,
            access_level="restricted",
        )
        return [h.chunk_ref.chunk_id for h in hits]

    bm25_hits = service.bm25.retrieve(question, top_k=max(10, top_k), department_filter=None, access_level="restricted")
    dense_hits = service.dense.retrieve(question, top_k=max(10, top_k), department_filter=None, access_level="restricted")
    fused_hits = fuse_hits(
        bm25_hits=bm25_hits,
        dense_hits=dense_hits,
        top_k=top_k,
        method=service.settings.fusion_method,
        lexical_weight=service.settings.lexical_weight,
        dense_weight=service.settings.dense_weight,
    )
    return [h.chunk_ref.chunk_id for h in fused_hits]


def run_retrieval_eval(service: QAService, items: List[EvalItem], top_k: int = 5, mode: str = "hybrid") -> Dict:
    positive_items = [item for item in items if item.gold_chunk_ids]
    if not positive_items:
        return {
            "summary": {"recall_at_k": 0.0, "mrr": 0.0, "evidence_hit_rate": 0.0},
            "rows": [],
            "meta": {"evaluated_items": 0, "total_items": len(items), "note": "No positive items found."},
        }

    rows = []
    for item in positive_items:
        ids = _retrieve_ids(service, item.question, top_k=top_k, mode=mode)
        row = {
            "id": item.id,
            "question": item.question,
            "retrieved_ids": ids,
            "gold_ids": item.gold_chunk_ids,
            "recall": recall_at_k(ids, item.gold_chunk_ids, top_k),
            "mrr": mrr(ids, item.gold_chunk_ids),
        }
        rows.append(row)

    summary = aggregate_retrieval_metrics(rows, k=top_k)
    return {"summary": summary, "rows": rows, "meta": {"evaluated_items": len(positive_items), "total_items": len(items)}}


def run_answer_eval(service: QAService, items: List[EvalItem], top_k: int = 5) -> Dict:
    rows = []
    tp_not_found = 0
    fp_not_found = 0
    fn_not_found = 0
    negative_items = 0
    for item in items:
        answer = service.ask(item.question, top_k=top_k, department_filter=None, access_level="restricted", debug=False)
        expected_not_found = len(item.gold_chunk_ids) == 0 or item.query_type == "negative"
        predicted_not_found = answer.status == "NOT_FOUND"
        if expected_not_found:
            negative_items += 1
        if predicted_not_found and expected_not_found:
            tp_not_found += 1
        elif predicted_not_found and not expected_not_found:
            fp_not_found += 1
        elif (not predicted_not_found) and expected_not_found:
            fn_not_found += 1

        rows.append(
            {
                "id": item.id,
                "status": answer.status,
                "confidence": answer.confidence,
                "citation_count": len(answer.citations),
                "reference_answer": item.reference_answer,
                "generated_answer": answer.answer_text,
                "difficulty": item.difficulty,
                "query_type": item.query_type,
                "expected_not_found": expected_not_found,
                "predicted_not_found": predicted_not_found,
            }
        )
    precision = tp_not_found / max(1, tp_not_found + fp_not_found)
    recall = tp_not_found / max(1, tp_not_found + fn_not_found)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    summary = {
        "total_items": len(items),
        "negative_items": negative_items,
        "no_answer_precision": precision,
        "no_answer_recall": recall,
        "no_answer_f1": f1,
    }
    return {"summary": summary, "rows": rows}


def run_full_eval(config_path: str, top_k: int = 5, dataset_path: str | None = None) -> Dict:
    settings = load_settings(config_path)
    service = QAService(settings)
    eval_path = Path(dataset_path) if dataset_path else Path(settings.eval_dataset_path)
    items = load_eval_dataset(eval_path)

    retrieval = {
        "bm25": run_retrieval_eval(service, items, top_k=top_k, mode="bm25"),
        "dense": run_retrieval_eval(service, items, top_k=top_k, mode="dense"),
        "hybrid": run_retrieval_eval(service, items, top_k=top_k, mode="hybrid"),
    }
    answer = run_answer_eval(service, items, top_k=top_k)
    return {"retrieval": retrieval, "answer": answer}
