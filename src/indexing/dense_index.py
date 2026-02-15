from __future__ import annotations

import json
import os
import hashlib
import re
from pathlib import Path
from typing import List

import numpy as np

from src.common.io import write_jsonl, read_jsonl
from src.common.schemas import DocumentChunk, RetrievalHit


class EmbeddingBackend:
    _TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹà-ỹ_]+", flags=re.UNICODE)
    _TOKEN_ALIASES = {
        "branch": "nhanh",
        "team": "nhom",
        "thuat": "engineering",
    }

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._st_model = None
        if model_name.startswith("hash://"):
            return
        if os.getenv("DISABLE_EXTERNAL_MODELS", "").strip() == "1":
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer(model_name)
        except Exception:
            self._st_model = None

    @staticmethod
    def _hash_embed(texts: List[str], dim: int = 384) -> np.ndarray:
        arr = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in EmbeddingBackend._TOKEN_RE.findall(text.lower()):
                tok = EmbeddingBackend._TOKEN_ALIASES.get(tok, tok)
                digest = hashlib.md5(tok.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:8], byteorder="little", signed=False) % dim
                arr[i, idx] += 1.0
            norm = np.linalg.norm(arr[i])
            if norm > 0:
                arr[i] /= norm
        return arr

    def encode(self, texts: List[str]) -> np.ndarray:
        if self._st_model is not None:
            vec = self._st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            vec = vec.astype(np.float32)
            norms = np.linalg.norm(vec, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return vec / norms
        dim = 384
        if self.model_name.startswith("hash://"):
            try:
                dim = int(self.model_name.split("://", 1)[1])
            except Exception:
                dim = 384
        return self._hash_embed(texts, dim=dim)


class DenseIndex:
    def __init__(self, chunks: List[DocumentChunk], embeddings: np.ndarray, embedding_model_name: str) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.embedding_model_name = embedding_model_name
        self._faiss_index = None
        try:
            import faiss  # type: ignore

            self._faiss_index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._faiss_index.add(self.embeddings)
        except Exception:
            self._faiss_index = None

    @classmethod
    def build(cls, chunks: List[DocumentChunk], backend: EmbeddingBackend) -> "DenseIndex":
        embeddings = backend.encode([cls._index_text(c) for c in chunks])
        return cls(chunks=chunks, embeddings=embeddings, embedding_model_name=backend.model_name)

    @staticmethod
    def _index_text(chunk: DocumentChunk) -> str:
        return f"{chunk.title} {chunk.section_path} {chunk.text}"

    def search(
        self,
        query: str,
        top_k: int,
        backend: EmbeddingBackend,
        department_filter: str | None = None,
        access_level: str | None = None,
    ) -> List[RetrievalHit]:
        q = backend.encode([query])

        if self._faiss_index is not None:
            distances, indices = self._faiss_index.search(q, top_k * 4)
            idxs = indices[0].tolist()
            vals = distances[0].tolist()
        else:
            sims = (self.embeddings @ q[0]).astype(np.float32)
            idxs = np.argsort(sims)[::-1].tolist()[: top_k * 4]
            vals = [float(sims[i]) for i in idxs]

        hits: List[RetrievalHit] = []
        for idx, score in zip(idxs, vals):
            if idx < 0:
                continue
            chunk = self.chunks[idx]
            if department_filter and chunk.department != department_filter:
                continue
            if access_level and chunk.access_level == "restricted" and access_level != "restricted":
                continue
            hits.append(
                RetrievalHit(
                    chunk_ref=chunk,
                    retrieval_source="dense",
                    score=float(score),
                    dense_score=float(score),
                )
            )
            if len(hits) >= top_k:
                break
        return hits

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "embeddings.npy", self.embeddings)
        write_jsonl(index_dir / "chunks.jsonl", [c.to_dict() for c in self.chunks])
        metadata = {"embedding_model_name": self.embedding_model_name}
        (index_dir / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")

    @staticmethod
    def load(index_dir: Path) -> "DenseIndex":
        embeddings = np.load(index_dir / "embeddings.npy")
        rows = read_jsonl(index_dir / "chunks.jsonl")
        chunks = [DocumentChunk(**row) for row in rows]
        meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
        return DenseIndex(chunks=chunks, embeddings=embeddings, embedding_model_name=meta["embedding_model_name"])
