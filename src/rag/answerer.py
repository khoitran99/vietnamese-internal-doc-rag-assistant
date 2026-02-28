from __future__ import annotations

import re
from typing import List

from src.common.schemas import AnswerPackage, RetrievalHit
from src.config.settings import AppSettings
from src.guardrails.policy import (
    build_clarifying_question,
    content_token_coverage,
    contains_yes_no_question,
    compute_confidence,
    filter_irrelevant_citations,
    has_explicit_reference,
    question_acronyms_supported,
    question_numbers_supported,
    query_chunk_overlap_score,
    should_return_not_found,
)
from src.rag.local_llm import LocalLLM
from src.rag.prompt import build_prompt


class RAGAnswerer:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.llm = LocalLLM(
            backend=settings.llm_backend,
            model_name=settings.llm_model_name,
            max_new_tokens=settings.max_new_tokens,
        )

    def answer(self, question: str, evidence_hits: List[RetrievalHit], debug: bool = False) -> AnswerPackage:
        prompt = build_prompt(question, evidence_hits)
        generation = self.llm.generate(question=question, prompt=prompt, hits=evidence_hits)
        has_reference = has_explicit_reference(question)
        top_text_relevance = query_chunk_overlap_score(question, evidence_hits[0].chunk_ref.text) if evidence_hits else 0.0
        if evidence_hits:
            top_chunk = evidence_hits[0].chunk_ref
            top_meta_relevance = max(
                query_chunk_overlap_score(question, top_chunk.title),
                query_chunk_overlap_score(question, top_chunk.section_path),
                query_chunk_overlap_score(question, f"{top_chunk.title} {top_chunk.section_path}"),
            )
        else:
            top_meta_relevance = 0.0
        top_relevance = max(top_text_relevance, top_meta_relevance)

        citations, citation_coverage = filter_irrelevant_citations(
            question=question,
            citations=generation.citations,
            retrieval_hits=evidence_hits,
            min_citation_relevance=self.settings.min_citation_relevance,
            min_score_threshold=self.settings.min_score_threshold,
            max_citations=self.settings.max_citations,
        )
        confidence = compute_confidence(evidence_hits, citation_coverage)

        not_found = should_return_not_found(
            hits=evidence_hits,
            citation_coverage=citation_coverage,
            min_score_threshold=self.settings.min_score_threshold,
            min_citation_coverage=self.settings.min_citation_coverage,
            top_relevance=top_relevance,
            min_top_relevance=self.settings.min_top_relevance,
        )

        if generation.answer.strip().upper() == "NOT_FOUND":
            not_found = True

        answer_text = generation.answer
        hit_map = {h.chunk_ref.chunk_id: h for h in evidence_hits}
        selected_hits = [hit_map[c["chunk_id"]] for c in citations if c.get("chunk_id") in hit_map]

        if contains_yes_no_question(question) and top_relevance < self.settings.min_yesno_relevance:
            not_found = True
        if contains_yes_no_question(question) and not has_reference and top_text_relevance < 0.75:
            not_found = True
        if not has_reference and top_relevance < max(self.settings.min_top_relevance, 0.18):
            not_found = True

        top_doc_support_count = 0
        top_doc_texts: List[str] = []
        if evidence_hits:
            top_doc_id = evidence_hits[0].chunk_ref.doc_id
            top_doc_support_count = sum(
                1 for hit in evidence_hits[: max(5, self.settings.max_citations)] if hit.chunk_ref.doc_id == top_doc_id
            )
            top_doc_texts = [
                f"{hit.chunk_ref.title} {hit.chunk_ref.section_path} {hit.chunk_ref.text}"
                for hit in evidence_hits[: max(5, self.settings.max_citations)]
                if hit.chunk_ref.doc_id == top_doc_id
            ]
        top_two_score_ratio = 0.0
        if len(evidence_hits) >= 2 and evidence_hits[0].score > 0:
            top_two_score_ratio = evidence_hits[1].score / evidence_hits[0].score

        if (
            not has_reference
            and top_text_relevance <= 0.5
            and top_meta_relevance < 0.5
            and top_doc_support_count < 2
            and top_two_score_ratio < 0.95
        ):
            not_found = True

        support_hits = selected_hits if selected_hits else evidence_hits[: self.settings.max_citations]
        evidence_texts = [f"{h.chunk_ref.title} {h.chunk_ref.section_path} {h.chunk_ref.text}" for h in support_hits]
        if not question_numbers_supported(question, evidence_texts):
            not_found = True
        if not question_acronyms_supported(question, evidence_texts):
            not_found = True
        open_query_token_coverage = content_token_coverage(question, evidence_texts, min_token_len=5)
        if not has_reference and open_query_token_coverage < self.settings.min_open_query_token_coverage:
            not_found = True
        top_doc_token_coverage = content_token_coverage(question, top_doc_texts, min_token_len=4)
        if not has_reference and top_doc_support_count >= 2 and top_doc_token_coverage < 0.5:
            not_found = True

        if self.llm.backend == "heuristic":
            bullets: List[str] = []
            for hit in selected_hits:
                text = hit.chunk_ref.text.strip()
                parts = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]
                if parts:
                    snippet = " ".join(parts[:2])
                else:
                    snippet = text
                snippet = snippet[:320].rstrip()
                bullets.append(f"- {snippet}")
            answer_text = "\n".join(bullets) if bullets else "NOT_FOUND"
            if answer_text == "NOT_FOUND":
                not_found = True

        if not_found:
            return AnswerPackage(
                answer_text="I couldn't find this in the current documents.",
                citations=[],
                confidence="Low",
                status="NOT_FOUND",
                clarifying_question=build_clarifying_question(question),
                debug={
                    "top_score": evidence_hits[0].score if evidence_hits else 0.0,
                    "citation_coverage": citation_coverage,
                    "top_relevance": top_relevance,
                    "top_text_relevance": top_text_relevance,
                    "top_meta_relevance": top_meta_relevance,
                    "top_doc_support_count": top_doc_support_count,
                    "top_two_score_ratio": top_two_score_ratio,
                    "open_query_token_coverage": open_query_token_coverage,
                    "top_doc_token_coverage": top_doc_token_coverage,
                }
                if debug
                else {},
            )

        return AnswerPackage(
            answer_text=answer_text,
            citations=citations,
            confidence=confidence,
            status="ANSWERED",
            clarifying_question=None,
            debug={
                "top_score": evidence_hits[0].score if evidence_hits else 0.0,
                "citation_coverage": citation_coverage,
                "top_relevance": top_relevance,
                "top_text_relevance": top_text_relevance,
                "top_meta_relevance": top_meta_relevance,
                "top_doc_support_count": top_doc_support_count,
                "top_two_score_ratio": top_two_score_ratio,
                "open_query_token_coverage": open_query_token_coverage,
                "top_doc_token_coverage": top_doc_token_coverage,
            }
            if debug
            else {},
        )
