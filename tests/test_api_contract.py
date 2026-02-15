import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed")
class TestAPIContract(unittest.TestCase):
    def test_health_search_ask_contract(self) -> None:
        from fastapi.testclient import TestClient

        from src.api.app import create_app
        from src.config.settings import load_settings
        from src.indexing.build_indices import build_all_indices
        from src.ingestion.pipeline import ingest_and_chunk

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "eng_onboarding.md").write_text(
                "# Engineering\n## Onboarding\nKy su moi can hoan thanh checklist onboarding trong 7 ngay dau.",
                encoding="utf-8",
            )

            cfg = root / "config.yaml"
            cfg.write_text(
                f"""
app:
  version: \"0.1.0\"
paths:
  raw_data_dir: \"{raw}\"
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
  lexical_weight: 0.5
  dense_weight: 0.5
  min_score_threshold: 0.1
models:
  embedding_model_name: \"hash://128\"
  llm_backend: \"heuristic\"
  llm_model_name: \"none\"
  max_new_tokens: 64
guardrails:
  min_score_threshold: 0.1
  min_citation_coverage: 1.0
""",
                encoding="utf-8",
            )

            settings = load_settings(cfg)
            ingest_and_chunk(settings)
            build_all_indices(settings)

            os.environ["APP_CONFIG_PATH"] = str(cfg)
            app = create_app()
            client = TestClient(app)

            h = client.get("/health")
            self.assertEqual(h.status_code, 200)
            self.assertIn("indices_loaded", h.json())

            s = client.post("/search", json={"query": "onboarding", "top_k": 3})
            self.assertEqual(s.status_code, 200)
            self.assertIn("hits", s.json())

            a = client.post("/ask", json={"question": "Onboarding can hoan thanh khi nao?", "top_k": 3})
            self.assertEqual(a.status_code, 200)
            self.assertIn("answer", a.json())
            self.assertIn("status", a.json())


if __name__ == "__main__":
    unittest.main()
