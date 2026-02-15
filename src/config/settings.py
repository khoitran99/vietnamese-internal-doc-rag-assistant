from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class AppSettings:
    version: str
    raw_data_dir: Path
    chunk_output_path: Path
    bm25_index_path: Path
    dense_index_dir: Path
    eval_dataset_path: Path
    chunk_size_tokens: int
    overlap_tokens: int
    default_top_k: int
    fusion_method: str
    lexical_weight: float
    dense_weight: float
    min_score_threshold: float
    min_relative_score: float
    min_query_token_overlap: float
    retrieval_candidate_size: int
    recency_weight: float
    embedding_model_name: str
    llm_backend: str
    llm_model_name: str
    max_new_tokens: int
    min_citation_coverage: float
    min_citation_relevance: float
    min_top_relevance: float
    max_citations: int


_REQUIRED_PATHS = (
    "paths.raw_data_dir",
    "paths.chunk_output_path",
    "paths.bm25_index_path",
    "paths.dense_index_dir",
    "paths.eval_dataset_path",
)


def _get(cfg: Dict[str, Any], dotted_key: str) -> Any:
    current: Any = cfg
    for key in dotted_key.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"Missing required config key: {dotted_key}")
        current = current[key]
    return current


def _get_optional(cfg: Dict[str, Any], dotted_key: str, default: Any) -> Any:
    try:
        return _get(cfg, dotted_key)
    except ValueError:
        return default


def load_settings(config_path: str | Path) -> AppSettings:
    with Path(config_path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    for key in _REQUIRED_PATHS:
        _get(cfg, key)

    settings = AppSettings(
        version=str(_get(cfg, "app.version")),
        raw_data_dir=Path(_get(cfg, "paths.raw_data_dir")),
        chunk_output_path=Path(_get(cfg, "paths.chunk_output_path")),
        bm25_index_path=Path(_get(cfg, "paths.bm25_index_path")),
        dense_index_dir=Path(_get(cfg, "paths.dense_index_dir")),
        eval_dataset_path=Path(_get(cfg, "paths.eval_dataset_path")),
        chunk_size_tokens=int(_get(cfg, "chunking.chunk_size_tokens")),
        overlap_tokens=int(_get(cfg, "chunking.overlap_tokens")),
        default_top_k=int(_get(cfg, "retrieval.default_top_k")),
        fusion_method=str(_get(cfg, "retrieval.fusion_method")),
        lexical_weight=float(_get(cfg, "retrieval.lexical_weight")),
        dense_weight=float(_get(cfg, "retrieval.dense_weight")),
        min_score_threshold=float(_get(cfg, "retrieval.min_score_threshold")),
        min_relative_score=float(_get_optional(cfg, "retrieval.min_relative_score", 0.45)),
        min_query_token_overlap=float(_get_optional(cfg, "retrieval.min_query_token_overlap", 0.12)),
        retrieval_candidate_size=int(_get_optional(cfg, "retrieval.candidate_size", 20)),
        recency_weight=float(_get_optional(cfg, "retrieval.recency_weight", 0.08)),
        embedding_model_name=str(_get(cfg, "models.embedding_model_name")),
        llm_backend=str(_get(cfg, "models.llm_backend")),
        llm_model_name=str(_get(cfg, "models.llm_model_name")),
        max_new_tokens=int(_get(cfg, "models.max_new_tokens")),
        min_citation_coverage=float(_get(cfg, "guardrails.min_citation_coverage")),
        min_citation_relevance=float(_get_optional(cfg, "guardrails.min_citation_relevance", 0.2)),
        min_top_relevance=float(_get_optional(cfg, "guardrails.min_top_relevance", 0.1)),
        max_citations=int(_get_optional(cfg, "guardrails.max_citations", 3)),
    )

    return settings


def ensure_directories(settings: AppSettings) -> None:
    for path in (
        settings.raw_data_dir,
        settings.chunk_output_path.parent,
        settings.bm25_index_path.parent,
        settings.dense_index_dir,
        settings.eval_dataset_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
