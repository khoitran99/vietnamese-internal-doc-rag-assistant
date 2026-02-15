from __future__ import annotations

from pathlib import Path
from typing import List

from src.common.schemas import RetrievalHit
from src.indexing.dense_index import DenseIndex, EmbeddingBackend


class DenseRetriever:
    def __init__(self, index: DenseIndex, backend: EmbeddingBackend) -> None:
        self.index = index
        self.backend = backend

    @classmethod
    def from_path(cls, index_dir: Path, embedding_model_name: str) -> "DenseRetriever":
        index = DenseIndex.load(index_dir)
        backend = EmbeddingBackend(embedding_model_name)
        return cls(index=index, backend=backend)

    def retrieve(self, query: str, top_k: int, department_filter: str | None = None, access_level: str | None = None) -> List[RetrievalHit]:
        return self.index.search(
            query=query,
            top_k=top_k,
            backend=self.backend,
            department_filter=department_filter,
            access_level=access_level,
        )
