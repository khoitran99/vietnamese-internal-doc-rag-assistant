import tempfile
import unittest
from pathlib import Path

from src.app.service import QAService
from src.config.settings import load_settings
from src.indexing.build_indices import build_all_indices
from src.ingestion.pipeline import ingest_and_chunk


class TestEndToEnd(unittest.TestCase):
    def test_pipeline_search_and_ask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "hr_policy_internal.md").write_text(
                "# HR\n## Leave\nNhan vien duoc nghi phep 12 ngay moi nam.",
                encoding="utf-8",
            )

            cfg = root / "config.yaml"
            cfg.write_text(
                """
app:
  version: "0.1.0"
paths:
  raw_data_dir: "{raw_data}"
  chunk_output_path: "{chunks}"
  bm25_index_path: "{bm25}"
  dense_index_dir: "{dense}"
  eval_dataset_path: "{eval}"
chunking:
  chunk_size_tokens: 64
  overlap_tokens: 10
retrieval:
  default_top_k: 5
  fusion_method: "weighted"
  lexical_weight: 0.5
  dense_weight: 0.5
  min_score_threshold: 0.1
models:
  embedding_model_name: "hash://128"
  llm_backend: "heuristic"
  llm_model_name: "none"
  max_new_tokens: 64
guardrails:
  min_score_threshold: 0.1
  min_citation_coverage: 1.0
""".format(
                    raw_data=str(raw),
                    chunks=str(root / "chunks.jsonl"),
                    bm25=str(root / "bm25.pkl"),
                    dense=str(root / "dense"),
                    eval=str(root / "eval.jsonl"),
                ),
                encoding="utf-8",
            )

            settings = load_settings(cfg)
            chunks = ingest_and_chunk(settings)
            self.assertGreater(len(chunks), 0)
            build_all_indices(settings)

            service = QAService(settings)
            search = service.search("nghi phep", top_k=3, department_filter=None, access_level="internal", debug=True)
            self.assertGreater(len(search["hits"]), 0)

            ans = service.ask(
                "Nhan vien duoc nghi phep bao nhieu ngay?",
                top_k=3,
                department_filter=None,
                access_level="internal",
                debug=True,
            )
            self.assertIn(ans.status, {"ANSWERED", "NOT_FOUND"})

            unsupported = service.ask(
                "Quy dinh an toan bay noi bo la gi?",
                top_k=3,
                department_filter=None,
                access_level="internal",
                debug=True,
            )
            self.assertEqual(unsupported.status, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
