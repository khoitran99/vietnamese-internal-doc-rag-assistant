from __future__ import annotations

from typing import Dict, List

import numpy as np

from src.common.schemas import RetrievalHit


def _normalize_scores(values: List[float]) -> List[float]:
    if not values:
        return []
    arr = np.array(values, dtype=np.float32)
    min_v = float(arr.min())
    max_v = float(arr.max())
    if max_v - min_v < 1e-8:
        return [1.0 for _ in values]
    return [float((v - min_v) / (max_v - min_v)) for v in arr]


def reciprocal_rank_fusion(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def fuse_hits(
    bm25_hits: List[RetrievalHit],
    dense_hits: List[RetrievalHit],
    top_k: int,
    method: str = "weighted",
    lexical_weight: float = 0.5,
    dense_weight: float = 0.5,
) -> List[RetrievalHit]:
    merged: Dict[str, RetrievalHit] = {}

    if method == "rrf":
        for rank, hit in enumerate(bm25_hits, start=1):
            key = hit.chunk_ref.chunk_id
            score = reciprocal_rank_fusion(rank)
            if key not in merged:
                merged[key] = RetrievalHit(chunk_ref=hit.chunk_ref, retrieval_source="hybrid", score=0.0)
            merged[key].bm25_score = score

        for rank, hit in enumerate(dense_hits, start=1):
            key = hit.chunk_ref.chunk_id
            score = reciprocal_rank_fusion(rank)
            if key not in merged:
                merged[key] = RetrievalHit(chunk_ref=hit.chunk_ref, retrieval_source="hybrid", score=0.0)
            merged[key].dense_score = score
    else:
        bm25_norm = _normalize_scores([h.score for h in bm25_hits])
        dense_norm = _normalize_scores([h.score for h in dense_hits])

        for hit, normalized in zip(bm25_hits, bm25_norm):
            key = hit.chunk_ref.chunk_id
            if key not in merged:
                merged[key] = RetrievalHit(chunk_ref=hit.chunk_ref, retrieval_source="hybrid", score=0.0)
            merged[key].bm25_score = normalized

        for hit, normalized in zip(dense_hits, dense_norm):
            key = hit.chunk_ref.chunk_id
            if key not in merged:
                merged[key] = RetrievalHit(chunk_ref=hit.chunk_ref, retrieval_source="hybrid", score=0.0)
            merged[key].dense_score = normalized

    for hit in merged.values():
        hit.fused_score = lexical_weight * hit.bm25_score + dense_weight * hit.dense_score
        hit.score = hit.fused_score

    ranked = sorted(merged.values(), key=lambda x: x.fused_score, reverse=True)
    return ranked[:top_k]
