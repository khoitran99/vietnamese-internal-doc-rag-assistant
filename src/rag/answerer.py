from __future__ import annotations

from typing import List

from src.common.schemas import AnswerPackage, RetrievalHit
from src.config.settings import AppSettings
from src.guardrails.policy import (
    build_clarifying_question,
    compute_confidence,
    filter_irrelevant_citations,
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
        top_relevance = query_chunk_overlap_score(question, evidence_hits[0].chunk_ref.text) if evidence_hits else 0.0

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
        if self.llm.backend == "heuristic":
            hit_map = {h.chunk_ref.chunk_id: h for h in evidence_hits}
            selected_hits = [hit_map[c["chunk_id"]] for c in citations if c.get("chunk_id") in hit_map]
            bullets: List[str] = []
            for hit in selected_hits:
                sentence = hit.chunk_ref.text.split(".")[0].strip()
                if not sentence:
                    sentence = hit.chunk_ref.text[:200].strip()
                bullets.append(f"- {sentence}")
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
            }
            if debug
            else {},
        )
