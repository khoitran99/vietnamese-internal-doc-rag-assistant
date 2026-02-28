import unittest

from src.common.schemas import DocumentChunk, RetrievalHit
from src.config.settings import load_settings
from src.rag.answerer import RAGAnswerer


class TestRAGAnswerer(unittest.TestCase):
    def test_section_title_query_with_conversational_prefix_is_answered(self) -> None:
        settings = load_settings("config/default.yaml")
        answerer = RAGAnswerer(settings)

        chunk = DocumentChunk(
            doc_id="engineering_branching_strategy_public_2024-10-12",
            chunk_id="engineering_branching_strategy_public_2024-10-12-1-1a138cde",
            text="Nhánh tính năng đặt theo mẫu `feat/<ticket-id>-<mota-ngan>`. Nhánh sửa lỗi đặt theo mẫu `fix/<ticket-id>-<mota-ngan>`.",
            title="engineering branching strategy public 2024-10-12",
            section_path="Engineering > Quy tắc đặt tên nhánh",
            department="Engineering",
            updated_at="2024-10-12",
            access_level="public",
        )
        hit = RetrievalHit(chunk_ref=chunk, retrieval_source="hybrid", score=1.2, fused_score=1.2)

        result = answerer.answer("Cho tôi biết về cách đặt tên nhánh", [hit], debug=True)
        self.assertEqual(result.status, "ANSWERED")
        self.assertGreaterEqual(result.debug.get("top_meta_relevance", 0.0), 0.5)


if __name__ == "__main__":
    unittest.main()
