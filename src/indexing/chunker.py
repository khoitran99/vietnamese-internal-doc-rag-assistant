from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from src.common.schemas import DocumentChunk


@dataclass
class SectionBlock:
    section_path: str
    text: str


def extract_section_blocks(text: str) -> List[SectionBlock]:
    lines = text.splitlines()
    stack: List[str] = []
    buffer: List[str] = []
    blocks: List[SectionBlock] = []

    def flush() -> None:
        if not buffer:
            return
        section_path = " > ".join(stack) if stack else "General"
        block_text = "\n".join(buffer).strip()
        if block_text:
            blocks.append(SectionBlock(section_path=section_path, text=block_text))
        buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            flush()
            level = len(stripped) - len(stripped.lstrip("#"))
            heading = stripped[level:].strip()
            if not heading:
                continue
            while len(stack) >= level and stack:
                stack.pop()
            stack.append(heading)
            continue
        buffer.append(stripped)

    flush()
    if not blocks and text.strip():
        blocks.append(SectionBlock(section_path="General", text=text.strip()))
    return blocks


def _window_tokens(tokens: List[str], chunk_size: int, overlap: int) -> Iterable[List[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    step = chunk_size - overlap
    for start in range(0, len(tokens), step):
        part = tokens[start : start + chunk_size]
        if part:
            yield part
        if start + chunk_size >= len(tokens):
            break


def build_chunks(
    doc_id: str,
    title: str,
    text: str,
    department: str,
    updated_at: str,
    access_level: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> List[DocumentChunk]:
    blocks = extract_section_blocks(text)
    chunks: List[DocumentChunk] = []
    idx = 0

    for block in blocks:
        tokens = block.text.split()
        for token_window in _window_tokens(tokens, chunk_size_tokens, overlap_tokens):
            chunk_text = " ".join(token_window).strip()
            if not chunk_text:
                continue
            digest = hashlib.md5(f"{doc_id}:{idx}:{chunk_text}".encode("utf-8")).hexdigest()[:8]
            chunk_id = f"{doc_id}-{idx}-{digest}"
            chunks.append(
                DocumentChunk(
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    text=chunk_text,
                    title=title,
                    section_path=block.section_path,
                    department=department,
                    updated_at=updated_at,
                    access_level=access_level,
                )
            )
            idx += 1

    return chunks


def chunk_from_rows(rows: List[Tuple[str, str, str, str, str, str]], chunk_size_tokens: int, overlap_tokens: int) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []
    for doc_id, title, text, department, updated_at, access_level in rows:
        chunks.extend(
            build_chunks(
                doc_id=doc_id,
                title=title,
                text=text,
                department=department,
                updated_at=updated_at,
                access_level=access_level,
                chunk_size_tokens=chunk_size_tokens,
                overlap_tokens=overlap_tokens,
            )
        )
    return chunks
