from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDocument:
    doc_id: str
    title: str
    text: str


def _parse_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf is required to parse PDF files") from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _parse_docx(path: Path) -> str:
    try:
        import docx2txt
    except Exception as exc:
        raise RuntimeError("docx2txt is required to parse DOCX files") from exc
    return docx2txt.process(str(path)) or ""


def _parse_text_like(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _parse_pdf(path)
    elif suffix == ".docx":
        text = _parse_docx(path)
    elif suffix in {".md", ".markdown", ".txt", ".html", ".htm"}:
        text = _parse_text_like(path)
    else:
        raise ValueError(f"Unsupported document type: {path.suffix}")

    title = path.stem.replace("_", " ").strip() or path.name
    return ParsedDocument(doc_id=path.stem, title=title, text=text)
