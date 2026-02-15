from __future__ import annotations

import re
from pathlib import Path
from typing import List

from src.common.io import write_jsonl
from src.common.schemas import DocumentChunk
from src.config.settings import AppSettings
from src.ingestion.cleaning import normalize_text
from src.ingestion.parsers import parse_document
from src.indexing.chunker import build_chunks


SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".markdown", ".txt", ".html", ".htm"}
_DATE_RE = re.compile(r"(20\\d{2}-\\d{2}-\\d{2})")


def _infer_department(file_name: str) -> str:
    low = file_name.lower()
    if "hr" in low:
        return "HR"
    if "security" in low:
        return "Security"
    if "engineering" in low or "eng" in low:
        return "Engineering"
    return "General"


def _infer_access_level(file_name: str) -> str:
    low = file_name.lower()
    if "restricted" in low:
        return "restricted"
    if "internal" in low:
        return "internal"
    return "public"


def _infer_updated_at(file_name: str) -> str:
    match = _DATE_RE.search(file_name)
    if match:
        return match.group(1)
    return "1970-01-01"


def ingest_and_chunk(settings: AppSettings) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []
    files = sorted([p for p in settings.raw_data_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES])

    for path in files:
        parsed = parse_document(path)
        normalized = normalize_text(parsed.text)
        if not normalized:
            continue

        department = _infer_department(path.name)
        access_level = _infer_access_level(path.name)
        updated_at = _infer_updated_at(path.name)
        file_chunks = build_chunks(
            doc_id=parsed.doc_id,
            title=parsed.title,
            text=normalized,
            department=department,
            updated_at=updated_at,
            access_level=access_level,
            chunk_size_tokens=settings.chunk_size_tokens,
            overlap_tokens=settings.overlap_tokens,
        )
        chunks.extend(file_chunks)

    write_jsonl(settings.chunk_output_path, [chunk.to_dict() for chunk in chunks])
    return chunks
