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
    rows = []
    for item in items:
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
    return {"summary": summary, "rows": rows}


def run_answer_eval(service: QAService, items: List[EvalItem], top_k: int = 5) -> Dict:
    rows = []
    for item in items:
        answer = service.ask(item.question, top_k=top_k, department_filter=None, access_level="restricted", debug=False)
        rows.append(
            {
                "id": item.id,
                "status": answer.status,
                "confidence": answer.confidence,
                "citation_count": len(answer.citations),
                "reference_answer": item.reference_answer,
                "generated_answer": answer.answer_text,
            }
        )
    return {"rows": rows}


def run_full_eval(config_path: str, top_k: int = 5) -> Dict:
    settings = load_settings(config_path)
    service = QAService(settings)
    items = load_eval_dataset(Path(settings.eval_dataset_path))

    retrieval = {
        "bm25": run_retrieval_eval(service, items, top_k=top_k, mode="bm25"),
        "dense": run_retrieval_eval(service, items, top_k=top_k, mode="dense"),
        "hybrid": run_retrieval_eval(service, items, top_k=top_k, mode="hybrid"),
    }
    answer = run_answer_eval(service, items, top_k=top_k)
    return {"retrieval": retrieval, "answer": answer}
