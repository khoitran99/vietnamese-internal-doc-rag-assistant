from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentChunk:
    doc_id: str
    chunk_id: str
    text: str
    title: str
    section_path: str
    department: str
    updated_at: str
    access_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalHit:
    chunk_ref: DocumentChunk
    retrieval_source: str
    score: float
    bm25_score: float = 0.0
    dense_score: float = 0.0
    fused_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["chunk_ref"] = self.chunk_ref.to_dict()
        return payload


@dataclass
class AnswerPackage:
    answer_text: str
    citations: List[Dict[str, str]]
    confidence: str
    status: str
    clarifying_question: Optional[str] = None
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer_text,
            "citations": self.citations,
            "confidence": self.confidence,
            "status": self.status,
            "clarifying_question": self.clarifying_question,
            "debug": self.debug,
        }
