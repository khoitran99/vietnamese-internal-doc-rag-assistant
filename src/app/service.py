from __future__ import annotations

from dataclasses import dataclass

from src.common.schemas import AnswerPackage
from src.config.settings import AppSettings
from src.rag.answerer import RAGAnswerer
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.service import RetrievalService


@dataclass
class HealthStatus:
    status: str
    version: str
    indices_loaded: bool
    llm_loaded: bool


class QAService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.bm25 = BM25Retriever.from_path(settings.bm25_index_path)
        self.dense = DenseRetriever.from_path(settings.dense_index_dir, settings.embedding_model_name)
        self.retrieval = RetrievalService(settings, self.bm25, self.dense)
        self.answerer = RAGAnswerer(settings)

    def health(self) -> HealthStatus:
        llm_loaded = self.answerer.llm.backend in {"heuristic", "transformers"}
        return HealthStatus(
            status="ok",
            version=self.settings.version,
            indices_loaded=True,
            llm_loaded=llm_loaded,
        )

    def search(self, query: str, top_k: int, department_filter: str | None, access_level: str | None, debug: bool = False) -> dict:
        hits, retrieval_debug = self.retrieval.retrieve(
            query=query,
            top_k=top_k,
            department_filter=department_filter,
            access_level=access_level,
        )

        response_hits = []
        for h in hits:
            chunk = h.chunk_ref
            response_hits.append(
                {
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "section_path": chunk.section_path,
                    "chunk_id": chunk.chunk_id,
                    "score": h.score,
                    "retrieval_source": h.retrieval_source,
                    "snippet": chunk.text[:250],
                }
            )

        payload = {"hits": response_hits}
        if debug:
            payload["debug"] = {
                "bm25": [{"chunk_id": h.chunk_ref.chunk_id, "score": h.score} for h in retrieval_debug.bm25_hits[:top_k]],
                "dense": [{"chunk_id": h.chunk_ref.chunk_id, "score": h.score} for h in retrieval_debug.dense_hits[:top_k]],
                "fusion": {
                    "lexical_weight": retrieval_debug.lexical_weight,
                    "dense_weight": retrieval_debug.dense_weight,
                    "candidate_size": retrieval_debug.candidate_size,
                },
                "thresholds": {
                    "min_score_threshold": self.settings.min_score_threshold,
                    "min_relative_score": self.settings.min_relative_score,
                    "min_query_token_overlap": self.settings.min_query_token_overlap,
                },
            }
        return payload

    def ask(
        self,
        question: str,
        top_k: int,
        department_filter: str | None,
        access_level: str | None,
        debug: bool = False,
    ) -> AnswerPackage:
        hits, retrieval_debug = self.retrieval.retrieve(
            query=question,
            top_k=top_k,
            department_filter=department_filter,
            access_level=access_level,
        )
        answer = self.answerer.answer(question, hits, debug=debug)

        if debug:
            answer.debug["bm25"] = [{"chunk_id": h.chunk_ref.chunk_id, "score": h.score} for h in retrieval_debug.bm25_hits[:top_k]]
            answer.debug["dense"] = [{"chunk_id": h.chunk_ref.chunk_id, "score": h.score} for h in retrieval_debug.dense_hits[:top_k]]
            answer.debug["fusion"] = {
                "lexical_weight": retrieval_debug.lexical_weight,
                "dense_weight": retrieval_debug.dense_weight,
                "candidate_size": retrieval_debug.candidate_size,
            }
            answer.debug["thresholds"] = {
                "min_score_threshold": self.settings.min_score_threshold,
                "min_relative_score": self.settings.min_relative_score,
                "min_query_token_overlap": self.settings.min_query_token_overlap,
                "min_citation_relevance": self.settings.min_citation_relevance,
                "min_top_relevance": self.settings.min_top_relevance,
                "min_yesno_relevance": self.settings.min_yesno_relevance,
                "min_open_query_token_coverage": self.settings.min_open_query_token_coverage,
                "top_doc_token_coverage_min": 0.5,
            }
        return answer
