import unittest

from src.common.schemas import DocumentChunk, RetrievalHit
from src.guardrails.policy import (
    content_token_coverage,
    compute_confidence,
    extract_query_targets,
    filter_irrelevant_citations,
    filter_retrieval_hits,
    question_acronyms_supported,
    tokenize_for_overlap,
    has_explicit_reference,
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

    def test_extract_query_targets(self) -> None:
        targets = extract_query_targets(
            "Theo tài liệu 'engineering onboarding public', mục 'Code Review' quy định gì?"
        )
        self.assertIn("engineering onboarding public", targets.doc_titles)
        self.assertIn("Code Review", targets.sections)
        self.assertTrue(has_explicit_reference("Theo tài liệu 'a', mục 'b'"))
        self.assertFalse(has_explicit_reference("chinh sach nay la gi"))

    def test_filter_irrelevant_citations_prefers_matching_doc_and_section(self) -> None:
        hit_wrong = self._hit(0.85, chunk_id="wrong", text="mo ta tong quan")
        hit_wrong.chunk_ref.title = "finance expense reimbursement internal 2024-12-20"
        hit_wrong.chunk_ref.section_path = "Finance > Hồ sơ bắt buộc"

        hit_right = self._hit(0.55, chunk_id="right", text="Tất cả pull request cần reviewer phê duyệt.")
        hit_right.chunk_ref.title = "engineering onboarding public"
        hit_right.chunk_ref.section_path = "Engineering > Code Review"

        filtered, _ = filter_irrelevant_citations(
            question="Theo tài liệu 'engineering onboarding public', mục 'Code Review' quy định gì?",
            citations=[{"chunk_id": "wrong", "title": "x", "section_path": "y"}],
            retrieval_hits=[hit_wrong, hit_right],
            min_citation_relevance=0.0,
            min_score_threshold=0.1,
            max_citations=1,
        )
        self.assertEqual(filtered[0]["chunk_id"], "right")

    def test_content_token_coverage(self) -> None:
        coverage_low = content_token_coverage(
            question="Quy dinh su dung drone trong cong ty la gi?",
            evidence_texts=["Nhan vien lam viec tu xa toi da 2 ngay moi tuan."],
            min_token_len=5,
        )
        coverage_high = content_token_coverage(
            question="Quy dinh su dung drone trong cong ty la gi?",
            evidence_texts=["Thiet bi drone chi duoc su dung khi co phe duyet."],
            min_token_len=5,
        )
        self.assertLess(coverage_low, 0.34)
        self.assertGreaterEqual(coverage_high, 0.34)

    def test_token_alias_for_branch(self) -> None:
        tokens = tokenize_for_overlap("branch nhánh")
        self.assertIn("nhanh", tokens)

    def test_question_acronyms_supported(self) -> None:
        self.assertFalse(
            question_acronyms_supported(
                question="Chinh sach thuong AI cap cong ty la gi?",
                evidence_texts=["Thuong gioi thieu duoc chi tra sau 2 thang thu viec."],
            )
        )
        self.assertTrue(
            question_acronyms_supported(
                question="SLA ho tro IT la bao nhieu?",
                evidence_texts=["SLA ho tro IT duoc phan loai theo P1, P2, P3, P4."],
            )
        )
        self.assertFalse(
            question_acronyms_supported(
                question="Chinh sach AI la gi?",
                evidence_texts=["Tai lieu huong dan noi bo ve thuong gioi thieu."],
            )
        )


if __name__ == "__main__":
    unittest.main()
