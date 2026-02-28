from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List

from src.common.schemas import RetrievalHit


_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹà-ỹ_]+", flags=re.UNICODE)
_QUOTED_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"|“([^”]+)”|‘([^’]+)’")
_TOKEN_ALIASES = {
    "branch": "nhanh",
    "team": "nhom",
    "thuat": "engineering",
}
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
    "nhu",
    "gi",
    "thong",
    "tin",
    "dang",
    "moi",
    "quy",
    "dinh",
    "chinh",
    "sach",
    "tai",
    "lieu",
    "muc",
    "noi",
    "dung",
    "huong",
    "dan",
    "quytrinh",
    "quatrinh",
    "nhan",
    "vien",
    "khong",
    "co",
    "cap",
    "dua",
    "tren",
    "noi",
    "bo",
    "phai",
    "yeu",
    "cau",
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


@dataclass(frozen=True)
class QueryTargets:
    doc_titles: List[str]
    sections: List[str]
    quoted_phrases: List[str]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped)


def _normalize_token(tok: str) -> str:
    normalized = _strip_accents(tok.lower()).strip()
    return _TOKEN_ALIASES.get(normalized, normalized)


def _dedup_keep_order(values: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        key = _strip_accents(value.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def tokenize_for_overlap(text: str) -> List[str]:
    tokens = [_normalize_token(tok) for tok in _TOKEN_RE.findall(text)]
    return [tok for tok in tokens if tok not in _STOPWORDS and len(tok) > 1]


def query_chunk_overlap_score(query: str, chunk_text: str) -> float:
    q_tokens = set(tokenize_for_overlap(query))
    if not q_tokens:
        return 0.0
    c_tokens = set(tokenize_for_overlap(chunk_text))
    if not c_tokens:
        return 0.0
    overlap = q_tokens.intersection(c_tokens)
    if not overlap:
        return 0.0

    # Dynamic scoring: keep query-coverage behavior, but when multiple content
    # tokens overlap, also consider chunk-side coverage to avoid penalizing
    # conversational filler in the query.
    query_coverage = len(overlap) / len(q_tokens)
    if len(overlap) < 2:
        return query_coverage
    chunk_coverage = len(overlap) / len(c_tokens)
    return max(query_coverage, chunk_coverage)


def contains_yes_no_question(text: str) -> bool:
    tokens = [_normalize_token(tok) for tok in _TOKEN_RE.findall(text)]
    # yes/no framing in Vietnamese often appears as "co ... khong".
    return "co" in tokens and "khong" in tokens


def extract_quoted_phrases(text: str) -> List[str]:
    phrases: List[str] = []
    for match in _QUOTED_RE.finditer(text):
        phrase = next((g for g in match.groups() if g), "")
        phrase = phrase.strip()
        if phrase:
            phrases.append(phrase)
    return _dedup_keep_order(phrases)


def extract_query_targets(question: str) -> QueryTargets:
    doc_titles: List[str] = []
    sections: List[str] = []
    unknown: List[str] = []
    normalized_question = _strip_accents(question.lower())

    for match in _QUOTED_RE.finditer(question):
        phrase = next((g for g in match.groups() if g), "").strip()
        if not phrase:
            continue

        start_idx = match.start()
        pre_ctx = normalized_question[max(0, start_idx - 40) : start_idx]
        phrase_norm = _strip_accents(phrase.lower())

        if "muc" in pre_ctx:
            sections.append(phrase)
            continue
        if "tai lieu" in pre_ctx or "trong" in pre_ctx:
            doc_titles.append(phrase)
            continue
        if any(key in phrase_norm for key in ("internal", "public", "policy")) or re.search(r"\d{4}", phrase_norm):
            doc_titles.append(phrase)
            continue
        unknown.append(phrase)

    if not doc_titles and unknown:
        ranked = sorted(unknown, key=lambda p: len(tokenize_for_overlap(p)), reverse=True)
        if ranked:
            doc_titles.append(ranked[0])
            sections.extend(ranked[1:])
    else:
        sections.extend(unknown)

    return QueryTargets(
        doc_titles=_dedup_keep_order(doc_titles),
        sections=_dedup_keep_order(sections),
        quoted_phrases=extract_quoted_phrases(question),
    )


def has_explicit_reference(question: str) -> bool:
    return len(extract_quoted_phrases(question)) > 0


def phrase_match_score(phrase: str, target_text: str) -> float:
    phrase_tokens = set(tokenize_for_overlap(phrase))
    if not phrase_tokens:
        return 0.0
    text_tokens = set(tokenize_for_overlap(target_text))
    if not text_tokens:
        return 0.0
    return len(phrase_tokens.intersection(text_tokens)) / len(phrase_tokens)


def max_phrase_match_score(phrases: List[str], target_text: str) -> float:
    if not phrases:
        return 0.0
    return max(phrase_match_score(phrase, target_text) for phrase in phrases)


def extract_number_tokens(text: str) -> List[str]:
    normalized = _strip_accents(text.lower())
    return re.findall(r"\d+(?:[.,]\d+)?", normalized)


def extract_acronym_tokens(text: str) -> List[str]:
    return re.findall(r"\b[A-Z]{2,}\b", text)


def question_numbers_supported(question: str, evidence_texts: List[str]) -> bool:
    q_numbers = set(extract_number_tokens(question))
    if not q_numbers:
        return True
    if not evidence_texts:
        return False
    evidence_numbers = set()
    for text in evidence_texts:
        evidence_numbers.update(extract_number_tokens(text))
    return any(num in evidence_numbers for num in q_numbers)


def question_acronyms_supported(question: str, evidence_texts: List[str]) -> bool:
    acronyms = set(extract_acronym_tokens(question))
    if not acronyms:
        return True
    if not evidence_texts:
        return False
    evidence_upper = " ".join(evidence_texts).upper()
    evidence_tokens = set(re.findall(r"\b[A-Z0-9]{2,}\b", evidence_upper))
    return any(acr in evidence_tokens for acr in acronyms)


def content_token_coverage(question: str, evidence_texts: List[str], min_token_len: int = 5) -> float:
    q_tokens = {tok for tok in tokenize_for_overlap(question) if len(tok) >= min_token_len}
    if not q_tokens:
        return 1.0
    if not evidence_texts:
        return 0.0

    evidence_tokens = set()
    for text in evidence_texts:
        evidence_tokens.update(tokenize_for_overlap(text))

    matched = sum(1 for tok in q_tokens if tok in evidence_tokens)
    return matched / max(1, len(q_tokens))


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
        text_overlap = query_chunk_overlap_score(query, hit.chunk_ref.text)
        metadata_overlap = query_chunk_overlap_score(query, f"{hit.chunk_ref.title} {hit.chunk_ref.section_path}")
        overlap = max(text_overlap, metadata_overlap)
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
    if not retrieval_hits:
        return [], 0.0

    targets = extract_query_targets(question)
    preferred_ids = {citation.get("chunk_id") for citation in citations if citation.get("chunk_id")}

    candidate_hits: List[tuple[float, RetrievalHit, float, float, float]] = []
    for hit in retrieval_hits:
        overlap = query_chunk_overlap_score(question, hit.chunk_ref.text)
        doc_match = max_phrase_match_score(targets.doc_titles, hit.chunk_ref.title)
        section_match = max_phrase_match_score(targets.sections, hit.chunk_ref.section_path)
        structural_match = max(doc_match, section_match)

        if hit.score < min_score_threshold:
            continue
        if overlap < min_citation_relevance and structural_match < 0.35:
            continue

        relevance = 0.55 * hit.score + 0.45 * overlap
        relevance += 0.65 * doc_match + 0.75 * section_match
        if hit.chunk_ref.chunk_id in preferred_ids:
            relevance += 0.05
        if targets.doc_titles and doc_match < 0.25:
            relevance -= 0.20
        if targets.sections and section_match < 0.20:
            relevance -= 0.10
        if relevance <= 0:
            continue

        candidate_hits.append((relevance, hit, overlap, doc_match, section_match))

    if not candidate_hits:
        return [], 0.0

    candidate_hits.sort(key=lambda item: item[0], reverse=True)
    selected: List[dict] = []
    seen_signatures = set()
    for _, hit, _, _, _ in candidate_hits:
        signature = " ".join(hit.chunk_ref.text.lower().split())[:160]
        if signature in seen_signatures:
            continue
        selected.append(
            {
                "title": hit.chunk_ref.title,
                "section_path": hit.chunk_ref.section_path,
                "chunk_id": hit.chunk_ref.chunk_id,
            }
        )
        seen_signatures.add(signature)
        if len(selected) >= max_citations:
            break

    coverage = len(selected) / max(1, min(max_citations, len(candidate_hits)))
    return selected, coverage


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
