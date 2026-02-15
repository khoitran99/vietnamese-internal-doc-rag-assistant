import unittest

from src.common.schemas import DocumentChunk, RetrievalHit
from src.guardrails.policy import (
    compute_confidence,
    filter_irrelevant_citations,
    filter_retrieval_hits,
    query_chunk_overlap_score,
    should_return_not_found,
)


class TestGuardrails(unittest.TestCase):
    def _hit(self, score: float, chunk_id: str = "c1", text: str = "text") -> RetrievalHit:
        chunk = DocumentChunk(
            doc_id="d1",
            chunk_id=chunk_id,
            text=text,
            title="t",
            section_path="s",
            department="General",
            updated_at="1970-01-01",
            access_level="public",
        )
        return RetrievalHit(chunk_ref=chunk, retrieval_source="hybrid", score=score, fused_score=score)

    def test_confidence_high(self) -> None:
        conf = compute_confidence([self._hit(0.9)], citation_coverage=1.0)
        self.assertEqual(conf, "High")

    def test_not_found_for_low_score(self) -> None:
        nf = should_return_not_found([self._hit(0.1)], citation_coverage=1.0, min_score_threshold=0.2, min_citation_coverage=1.0)
        self.assertTrue(nf)

    def test_not_found_for_missing_citation(self) -> None:
        nf = should_return_not_found([self._hit(0.9)], citation_coverage=0.0, min_score_threshold=0.2, min_citation_coverage=1.0)
        self.assertTrue(nf)

    def test_not_found_for_low_top_relevance(self) -> None:
        nf = should_return_not_found(
            [self._hit(0.9)],
            citation_coverage=1.0,
            min_score_threshold=0.2,
            min_citation_coverage=1.0,
            top_relevance=0.05,
            min_top_relevance=0.1,
        )
        self.assertTrue(nf)

    def test_query_chunk_overlap(self) -> None:
        score = query_chunk_overlap_score("chinh sach nghi phep nam", "Nhan vien duoc nghi phep nam 12 ngay moi nam")
        self.assertGreater(score, 0.2)

    def test_filter_retrieval_hits(self) -> None:
        hits = [
            self._hit(0.9, chunk_id="c1", text="nghi phep nam 12 ngay"),
            self._hit(0.4, chunk_id="c2", text="quy trinh code review"),
            self._hit(0.2, chunk_id="c3", text="lap lich incident response"),
        ]
        filtered = filter_retrieval_hits(
            query="nghi phep nam",
            hits=hits,
            min_score_threshold=0.25,
            min_relative_score=0.3,
            min_query_token_overlap=0.2,
            top_k=3,
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].chunk_ref.chunk_id, "c1")

    def test_filter_irrelevant_citations(self) -> None:
        hits = [
            self._hit(0.8, chunk_id="c1", text="nghi phep nam 12 ngay"),
            self._hit(0.8, chunk_id="c2", text="incident reporting trong 24 gio"),
        ]
        citations = [
            {"chunk_id": "c1", "title": "A", "section_path": "HR > Leave"},
            {"chunk_id": "c2", "title": "B", "section_path": "Security > Incident"},
        ]
        filtered, coverage = filter_irrelevant_citations(
            question="nghi phep nam la bao nhieu ngay",
            citations=citations,
            retrieval_hits=hits,
            min_citation_relevance=0.2,
            min_score_threshold=0.2,
            max_citations=3,
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["chunk_id"], "c1")
        self.assertGreaterEqual(coverage, 0.4)


if __name__ == "__main__":
    unittest.main()
