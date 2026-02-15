from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    department_filter: Optional[str] = None
    access_level: Optional[str] = "public"
    debug: bool = False


class SearchHit(BaseModel):
    doc_id: str
    title: str
    section_path: str
    chunk_id: str
    score: float
    retrieval_source: str
    snippet: str


class SearchResponse(BaseModel):
    hits: List[SearchHit]
    debug: Optional[Dict[str, Any]] = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    department_filter: Optional[str] = None
    access_level: Optional[str] = "public"
    debug: bool = False


class AskResponse(BaseModel):
    answer: str
    citations: List[Dict[str, str]]
    confidence: str
    status: str
    clarifying_question: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    indices_loaded: bool
    llm_loaded: bool
