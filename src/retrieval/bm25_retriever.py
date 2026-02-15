from __future__ import annotations

from pathlib import Path
from typing import List

from src.common.schemas import RetrievalHit
from src.indexing.bm25_index import BM25Index


class BM25Retriever:
    def __init__(self, index: BM25Index) -> None:
        self.index = index

    @classmethod
    def from_path(cls, index_path: Path) -> "BM25Retriever":
        return cls(BM25Index.load(index_path))

    def retrieve(self, query: str, top_k: int, department_filter: str | None = None, access_level: str | None = None) -> List[RetrievalHit]:
        return self.index.search(query=query, top_k=top_k, department_filter=department_filter, access_level=access_level)
