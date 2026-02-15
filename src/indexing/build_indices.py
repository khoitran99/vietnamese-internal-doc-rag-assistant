from __future__ import annotations

from typing import List

from src.common.io import read_jsonl
from src.common.schemas import DocumentChunk
from src.config.settings import AppSettings
from src.indexing.bm25_index import BM25Index
from src.indexing.dense_index import DenseIndex, EmbeddingBackend


def load_chunks(settings: AppSettings) -> List[DocumentChunk]:
    rows = read_jsonl(settings.chunk_output_path)
    return [DocumentChunk(**row) for row in rows]


def build_all_indices(settings: AppSettings) -> None:
    chunks = load_chunks(settings)

    bm25 = BM25Index(chunks)
    bm25.save(settings.bm25_index_path)

    backend = EmbeddingBackend(settings.embedding_model_name)
    dense = DenseIndex.build(chunks, backend)
    dense.save(settings.dense_index_dir)
