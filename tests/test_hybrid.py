import unittest

from src.common.schemas import DocumentChunk, RetrievalHit
from src.retrieval.hybrid import fuse_hits


class TestHybridFusion(unittest.TestCase):
    def _make_hit(self, chunk_id: str, score: float, source: str) -> RetrievalHit:
        chunk = DocumentChunk(
            doc_id="d",
            chunk_id=chunk_id,
            text="content",
            title="title",
            section_path="sec",
            department="General",
            updated_at="1970-01-01",
            access_level="public",
        )
        return RetrievalHit(chunk_ref=chunk, retrieval_source=source, score=score)

    def test_weighted_fusion_merges_sources(self) -> None:
        bm25 = [self._make_hit("a", 10.0, "bm25"), self._make_hit("b", 8.0, "bm25")]
        dense = [self._make_hit("b", 0.9, "dense"), self._make_hit("c", 0.8, "dense")]

        fused = fuse_hits(bm25, dense, top_k=3, method="weighted", lexical_weight=0.5, dense_weight=0.5)
        ids = [h.chunk_ref.chunk_id for h in fused]
        self.assertIn("a", ids)
        self.assertIn("b", ids)
        self.assertIn("c", ids)


if __name__ == "__main__":
    unittest.main()
