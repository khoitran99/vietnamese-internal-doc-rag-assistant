from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import List

import numpy as np

from src.common.schemas import DocumentChunk, RetrievalHit


class BM25Index:
    _TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹà-ỹ_]+", flags=re.UNICODE)
    _TOKEN_ALIASES = {
        "branch": "nhanh",
        "team": "nhom",
        "thuat": "engineering",
    }

    def __init__(self, chunks: List[DocumentChunk]) -> None:
        self.chunks = chunks
        self.corpus_tokens = [self._tokenize(self._index_text(chunk)) for chunk in chunks]
        self._bm25 = None
        self._use_rank_bm25 = False

        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(self.corpus_tokens)
            self._use_rank_bm25 = True
        except Exception:
            self._bm25 = None
            self._idf = self._compute_idf(self.corpus_tokens)

    @staticmethod
    def _index_text(chunk: DocumentChunk) -> str:
        return f"{chunk.title} {chunk.section_path} {chunk.text}"

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        tokens = cls._TOKEN_RE.findall(text.lower())
        return [cls._TOKEN_ALIASES.get(tok, tok) for tok in tokens]

    @staticmethod
    def _compute_idf(corpus_tokens: List[List[str]]) -> dict:
        df = {}
        n_docs = max(1, len(corpus_tokens))
        for tokens in corpus_tokens:
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1
        return {tok: float(np.log((n_docs + 1) / (freq + 1)) + 1.0) for tok, freq in df.items()}

    def _simple_scores(self, query_tokens: List[str]) -> np.ndarray:
        scores = np.zeros(len(self.corpus_tokens), dtype=np.float32)
        for i, tokens in enumerate(self.corpus_tokens):
            token_counts = {}
            for tok in tokens:
                token_counts[tok] = token_counts.get(tok, 0) + 1
            score = 0.0
            for tok in query_tokens:
                tf = token_counts.get(tok, 0)
                if tf:
                    score += tf * self._idf.get(tok, 1.0)
            scores[i] = score
        return scores

    def search(
        self,
        query: str,
        top_k: int,
        department_filter: str | None = None,
        access_level: str | None = None,
    ) -> List[RetrievalHit]:
        query_tokens = self._tokenize(query)
        if self._use_rank_bm25 and self._bm25 is not None:
            scores = np.array(self._bm25.get_scores(query_tokens), dtype=np.float32)
        else:
            scores = self._simple_scores(query_tokens)

        ranked_idx = np.argsort(scores)[::-1]
        hits: List[RetrievalHit] = []

        for idx in ranked_idx:
            score = float(scores[idx])
            if score <= 0.0:
                continue
            chunk = self.chunks[int(idx)]
            if department_filter and chunk.department != department_filter:
                continue
            if access_level and chunk.access_level == "restricted" and access_level != "restricted":
                continue
            hits.append(
                RetrievalHit(
                    chunk_ref=chunk,
                    retrieval_source="bm25",
                    score=score,
                    bm25_score=score,
                )
            )
            if len(hits) >= top_k:
                break
        return hits

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "BM25Index":
        with path.open("rb") as f:
            return pickle.load(f)
