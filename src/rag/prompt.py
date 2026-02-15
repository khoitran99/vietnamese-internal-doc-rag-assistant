from __future__ import annotations

from typing import List

from src.common.schemas import RetrievalHit


def build_prompt(question: str, evidence_hits: List[RetrievalHit]) -> str:
    evidence_lines = []
    for i, hit in enumerate(evidence_hits, start=1):
        chunk = hit.chunk_ref
        evidence_lines.append(
            f"[{i}] title={chunk.title} | section={chunk.section_path} | chunk_id={chunk.chunk_id}\n{chunk.text}"
        )
    evidence_text = "\n\n".join(evidence_lines)

    return (
        "You are an enterprise-safe Vietnamese QA assistant.\n"
        "Only answer from provided evidence.\n"
        "If unsupported, output NOT_FOUND.\n"
        "Return JSON with keys: answer, citations, confidence.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE:\n{evidence_text}\n"
    )
