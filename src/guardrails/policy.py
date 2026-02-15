from __future__ import annotations

import re
from typing import List

from src.common.schemas import RetrievalHit


_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹà-ỹ_]+", flags=re.UNICODE)
_STOPWORDS = {
    "la",
    "va",
    "voi",
    "cua",
    "cho",
    "trong",
    "theo",
    "duoc",
    "can",
    "mot",
    "nhieu",
    "bao",
    "nhieu",
    "khi",
    "nao",
    "gi",
    "thong",
    "tin",
    "dang",
    "moi",
    "quy",
    "dinh",
    "chinh",
    "sach",
    "noi",
    "bo",
    "phai",
    "su",
    "co",
    "lau",
    "is",
    "are",
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
}


def tokenize_for_overlap(text: str) -> List[str]:
    tokens = [tok.lower() for tok in _TOKEN_RE.findall(text)]
    return [tok for tok in tokens if tok not in _STOPWORDS and len(tok) > 1]


def query_chunk_overlap_score(query: str, chunk_text: str) -> float:
    q_tokens = set(tokenize_for_overlap(query))
    if not q_tokens:
        return 0.0
    c_tokens = set(tokenize_for_overlap(chunk_text))
    if not c_tokens:
        return 0.0
    overlap = q_tokens.intersection(c_tokens)
    return len(overlap) / len(q_tokens)


def filter_retrieval_hits(
    query: str,
    hits: List[RetrievalHit],
    min_score_threshold: float,
    min_relative_score: float,
    min_query_token_overlap: float,
    top_k: int,
) -> List[RetrievalHit]:
    if not hits:
        return []

    top_score = max(hit.score for hit in hits)
    filtered: List[RetrievalHit] = []
    for hit in hits:
        relative_score = hit.score / top_score if top_score > 0 else 0.0
        overlap = query_chunk_overlap_score(query, hit.chunk_ref.text)
        if hit.score < min_score_threshold:
            continue
        if relative_score < min_relative_score:
            continue
        if overlap < min_query_token_overlap:
            continue
        filtered.append(hit)

    return filtered[:top_k]


def filter_irrelevant_citations(
    question: str,
    citations: List[dict],
    retrieval_hits: List[RetrievalHit],
    min_citation_relevance: float,
    min_score_threshold: float,
    max_citations: int,
) -> tuple[List[dict], float]:
    if not citations:
        return [], 0.0

    hit_by_chunk_id = {hit.chunk_ref.chunk_id: hit for hit in retrieval_hits}
    valid: List[dict] = []
    seen_signatures = set()
    candidate_signatures = set()
    for citation in citations:
        chunk_id = citation.get("chunk_id")
        if not chunk_id or chunk_id not in hit_by_chunk_id:
            continue
        hit = hit_by_chunk_id[chunk_id]
        signature = " ".join(hit.chunk_ref.text.lower().split())[:160]
        overlap = query_chunk_overlap_score(question, hit.chunk_ref.text)
        if hit.score < min_score_threshold:
            continue
        if overlap < min_citation_relevance:
            continue
        candidate_signatures.add(signature)
        if signature in seen_signatures:
            continue
        valid.append(citation)
        seen_signatures.add(signature)
        if len(valid) >= max_citations:
            break

    coverage = len(seen_signatures) / max(1, len(candidate_signatures))
    return valid, coverage


def compute_confidence(hits: List[RetrievalHit], citation_coverage: float) -> str:
    if not hits:
        return "Low"

    top = hits[0].score
    if top >= 0.75 and citation_coverage >= 1.0:
        return "High"
    if top >= 0.35 and citation_coverage >= 0.5:
        return "Medium"
    return "Low"


def should_return_not_found(
    hits: List[RetrievalHit],
    citation_coverage: float,
    min_score_threshold: float,
    min_citation_coverage: float,
    top_relevance: float = 1.0,
    min_top_relevance: float = 0.0,
) -> bool:
    if not hits:
        return True
    top = hits[0].score
    if top < min_score_threshold:
        return True
    if citation_coverage < min_citation_coverage:
        return True
    if top_relevance < min_top_relevance:
        return True
    return False


def build_clarifying_question(question: str) -> str:
    return (
        "Ban co the lam ro them bo phan, chinh sach, hoac moc thoi gian lien quan cho cau hoi nay khong? "
        f"(Cau hoi goc: {question})"
    )
