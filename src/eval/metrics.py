from __future__ import annotations

from typing import Dict, List, Sequence


def recall_at_k(retrieved_ids: Sequence[str], gold_ids: Sequence[str], k: int) -> float:
    retrieved = list(retrieved_ids)[:k]
    if not gold_ids:
        return 0.0
    return 1.0 if any(item in set(gold_ids) for item in retrieved) else 0.0


def mrr(retrieved_ids: Sequence[str], gold_ids: Sequence[str]) -> float:
    gold_set = set(gold_ids)
    for idx, item in enumerate(retrieved_ids, start=1):
        if item in gold_set:
            return 1.0 / idx
    return 0.0


def aggregate_retrieval_metrics(results: List[Dict], k: int = 5) -> Dict[str, float]:
    if not results:
        return {"recall_at_k": 0.0, "mrr": 0.0, "evidence_hit_rate": 0.0}

    recalls = [r["recall"] for r in results]
    mrrs = [r["mrr"] for r in results]
    return {
        "recall_at_k": sum(recalls) / len(recalls),
        "mrr": sum(mrrs) / len(mrrs),
        "evidence_hit_rate": sum(recalls) / len(recalls),
    }
