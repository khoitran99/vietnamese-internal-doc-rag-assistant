import tempfile
import unittest
from pathlib import Path

from src.common.schemas import DocumentChunk, RetrievalHit
from src.config.settings import load_settings
from src.retrieval.service import RetrievalService


class _DummyRetriever:
    def retrieve(self, *args, **kwargs):
        return []


class TestRetrievalTuning(unittest.TestCase):
    def test_recency_boost_prefers_newer_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            cfg = root / "config.yaml"
            cfg.write_text(
                f"""
app:
  version: \"0.1.0\"
paths:
  raw_data_dir: \"{root / 'raw'}\"
  chunk_output_path: \"{root / 'chunks.jsonl'}\"
  bm25_index_path: \"{root / 'bm25.pkl'}\"
  dense_index_dir: \"{root / 'dense'}\"
  eval_dataset_path: \"{root / 'eval.jsonl'}\"
chunking:
  chunk_size_tokens: 64
  overlap_tokens: 10
retrieval:
  default_top_k: 5
  fusion_method: \"weighted\"
  lexical_weight: 0.6
  dense_weight: 0.4
  min_score_threshold: 0.1
  min_relative_score: 0.1
  min_query_token_overlap: 0.0
  candidate_size: 10
  recency_weight: 0.2
models:
  embedding_model_name: \"hash://128\"
  llm_backend: \"heuristic\"
  llm_model_name: \"none\"
  max_new_tokens: 64
guardrails:
  min_citation_coverage: 1.0
  min_citation_relevance: 0.2
  min_top_relevance: 0.1
  max_citations: 3
""",
                encoding="utf-8",
            )

            settings = load_settings(cfg)
            service = RetrievalService(settings, _DummyRetriever(), _DummyRetriever())

            old_chunk = DocumentChunk(
                doc_id="d1",
                chunk_id="old",
                text="policy",
                title="old",
                section_path="s",
                department="General",
                updated_at="2020-01-01",
                access_level="public",
            )
            new_chunk = DocumentChunk(
                doc_id="d2",
                chunk_id="new",
                text="policy",
                title="new",
                section_path="s",
                department="General",
                updated_at="2025-01-01",
                access_level="public",
            )
            hits = [
                RetrievalHit(chunk_ref=old_chunk, retrieval_source="hybrid", score=0.7, fused_score=0.7),
                RetrievalHit(chunk_ref=new_chunk, retrieval_source="hybrid", score=0.7, fused_score=0.7),
            ]

            boosted = service._apply_recency_boost(hits)
            self.assertEqual(boosted[0].chunk_ref.chunk_id, "new")
            self.assertGreater(boosted[0].score, boosted[1].score)


if __name__ == "__main__":
    unittest.main()
