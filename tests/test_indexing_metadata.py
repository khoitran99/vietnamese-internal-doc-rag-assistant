import unittest

from src.common.schemas import DocumentChunk
from src.indexing.bm25_index import BM25Index


class TestIndexingMetadata(unittest.TestCase):
    def test_bm25_indexes_title_and_section_path(self) -> None:
        chunks = [
            DocumentChunk(
                doc_id="eng_onboarding",
                chunk_id="c1",
                text="Tat ca pull request can reviewer phe duyet.",
                title="engineering onboarding public",
                section_path="Engineering > Code Review",
                department="Engineering",
                updated_at="1970-01-01",
                access_level="public",
            ),
            DocumentChunk(
                doc_id="finance_policy",
                chunk_id="c2",
                text="Chi phi can hoa don hop le.",
                title="finance expense reimbursement internal",
                section_path="Finance > Ho so bat buoc",
                department="General",
                updated_at="1970-01-01",
                access_level="internal",
            ),
            DocumentChunk(
                doc_id="security_policy",
                chunk_id="c3",
                text="Thong tin mat khau phai duoc thay dinh ky.",
                title="security password policy",
                section_path="Security > Password Rotation",
                department="Security",
                updated_at="1970-01-01",
                access_level="internal",
            ),
        ]

        index = BM25Index(chunks)
        hits = index.search(query="Code Review engineering onboarding public", top_k=2)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].chunk_ref.chunk_id, "c1")


if __name__ == "__main__":
    unittest.main()
