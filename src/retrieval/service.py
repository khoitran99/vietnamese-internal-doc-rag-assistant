from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from src.common.schemas import RetrievalHit
from src.config.settings import AppSettings
from src.guardrails.policy import filter_retrieval_hits
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.hybrid import fuse_hits


@dataclass
class RetrievalDebug:
    bm25_hits: List[RetrievalHit]
    dense_hits: List[RetrievalHit]
    lexical_weight: float
    dense_weight: float
    candidate_size: int


class RetrievalService:
    def __init__(self, settings: AppSettings, bm25: BM25Retriever, dense: DenseRetriever) -> None:
        self.settings = settings
        self.bm25 = bm25
        self.dense = dense

    @staticmethod
    def _parse_date(value: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return datetime(1970, 1, 1)

    def _apply_recency_boost(self, hits: List[RetrievalHit]) -> List[RetrievalHit]:
        if not hits or self.settings.recency_weight <= 0:
            return hits

        dates = [self._parse_date(hit.chunk_ref.updated_at) for hit in hits]
        min_ts = min(dates)
        max_ts = max(dates)
        span_seconds = (max_ts - min_ts).total_seconds()
        if span_seconds <= 0:
            return hits

        for hit, dt in zip(hits, dates):
            recency_norm = (dt - min_ts).total_seconds() / span_seconds
            hit.fused_score = hit.fused_score + self.settings.recency_weight * recency_norm
            hit.score = hit.fused_score
        return sorted(hits, key=lambda h: h.fused_score, reverse=True)

    def _compute_query_weights(self, query: str) -> tuple[float, float]:
        lexical = self.settings.lexical_weight
        dense = self.settings.dense_weight
        tokens = query.split()

        has_code_like_token = any(any(ch.isdigit() for ch in tok) or (tok.isupper() and len(tok) >= 2) for tok in tokens)
        if has_code_like_token:
            lexical += 0.15
            dense -= 0.15

        if len(tokens) >= 10:
            dense += 0.10
            lexical -= 0.10

        lexical = max(0.1, lexical)
        dense = max(0.1, dense)
        total = lexical + dense
        return lexical / total, dense / total

    def retrieve(
        self,
        query: str,
        top_k: int,
        department_filter: str | None = None,
        access_level: str | None = None,
    ) -> tuple[List[RetrievalHit], RetrievalDebug]:
        candidate_size = max(self.settings.retrieval_candidate_size, top_k * 3, 10)
        bm25_hits = self.bm25.retrieve(query, candidate_size, department_filter, access_level)
        dense_hits = self.dense.retrieve(query, candidate_size, department_filter, access_level)
        lexical_weight, dense_weight = self._compute_query_weights(query)

        fused_candidates = fuse_hits(
            bm25_hits=bm25_hits,
            dense_hits=dense_hits,
            top_k=candidate_size,
            method=self.settings.fusion_method,
            lexical_weight=lexical_weight,
            dense_weight=dense_weight,
        )
        recency_boosted = self._apply_recency_boost(fused_candidates)
        fused = filter_retrieval_hits(
            query=query,
            hits=recency_boosted,
            min_score_threshold=self.settings.min_score_threshold,
            min_relative_score=self.settings.min_relative_score,
            min_query_token_overlap=self.settings.min_query_token_overlap,
            top_k=top_k,
        )
        return fused, RetrievalDebug(
            bm25_hits=bm25_hits,
            dense_hits=dense_hits,
            lexical_weight=lexical_weight,
            dense_weight=dense_weight,
            candidate_size=candidate_size,
        )
