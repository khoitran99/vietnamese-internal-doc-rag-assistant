# Vietnamese Internal Docs RAG Assistant

A local, production-minded Retrieval-Augmented Generation (RAG) QA system for Vietnamese internal documentation.

## Current Implementation (As-Built)

- Ingestion for `PDF`, `DOCX`, `MD`, `HTML`, `TXT`
- Text normalization + deterministic section-aware chunking
- Hybrid retrieval pipeline:
  - BM25 retriever
  - Dense retriever (hash embedding by default)
  - Weighted fusion + metadata/recency boosts + threshold filters
- RAG answering with citation packaging
- Guardrails with strict `ANSWERED` / `NOT_FOUND` behavior
- FastAPI service:
  - `GET /health`
  - `POST /search`
  - `POST /ask`
- Streamlit UI (`src/ui/streamlit_app.py`)
- Evaluation and error analysis scripts
- Manual test checklist (20 scenarios)

## Default Runtime Profile

From `config/default.yaml`:

- `models.llm_backend: "heuristic"`
- `models.llm_model_name: "Qwen/Qwen2.5-3B-Instruct"` (used only if backend is `transformers`)
- `models.embedding_model_name: "hash://384"`
- `retrieval.fusion_method: "weighted"`
- `retrieval.lexical_weight: 0.62`
- `retrieval.dense_weight: 0.38`

Important:

- `llm_model_name` is only used when backend is `transformers`.
- With default heuristic mode, the system runs fully offline when you set `DISABLE_EXTERNAL_MODELS=1`.

## Repository Layout

- `config/default.yaml`: runtime config
- `data/raw/`: source documents
- `data/processed/chunks.jsonl`: generated chunk corpus
- `data/indices/`: generated BM25 + dense indices
- `data/eval/`: eval datasets (`qa_eval*.jsonl`)
- `src/`: ingestion, indexing, retrieval, rag, guardrails, api, ui, eval
- `scripts/`: run/ops utilities
- `tests/`: unit + integration tests
- `IMPLEMENTATION_GUIDE.md`: implementation phases and verification
- `MANUAL_TEST_CHECKLIST.md`: 20 manual scenarios with expected outcomes
- `SYSTEM_DIAGRAMS_AND_LEARNING_CURVE.md`: diagrams + learning roadmap
- `TUNING_NOTES.md`: retrieval/guardrail tuning decisions and results

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

1. Build chunks and indices:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```

2. Start API:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```

3. Open UI (new terminal):

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 streamlit run src/ui/streamlit_app.py
```

## API Smoke Examples

Health:

```bash
curl -s http://127.0.0.1:8000/health
```

Search:

```bash
curl -s -X POST http://127.0.0.1:8000/search \
  -H 'content-type: application/json' \
  -d '{"query":"nghi phep","top_k":5,"access_level":"internal","debug":true}'
```

Ask:

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Nhan vien duoc nghi phep bao nhieu ngay?","top_k":5,"access_level":"internal","debug":true}'
```

## Verification

Run automated verification for Steps 2/4/5/7:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/verify_pipeline.py
```

Expected output style:

- `[PASS]`/`[FAIL]` per step
- final `OVERALL: PASS` or `OVERALL: FAIL`

Run tests directly:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
```

## Evaluation

Full eval:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --top_k 5
```

Holdout error report:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/holdout_error_report.py \
  --config config/default.yaml \
  --dataset data/eval/qa_eval_holdout.jsonl \
  --top_k 5 \
  --sample_limit 5
```

Split dataset:

```bash
PYTHONPATH=. python3 scripts/split_eval_dataset.py \
  --input data/eval/qa_eval.jsonl \
  --train-output data/eval/qa_eval_train.jsonl \
  --holdout-output data/eval/qa_eval_holdout.jsonl \
  --holdout-ratio 0.2 \
  --seed 42
```

## Optional Transformer Backend

Supported but non-default.

- Set `models.llm_backend: "transformers"`
- Set a valid local or HF model in `models.llm_model_name`
- Remove `DISABLE_EXTERNAL_MODELS=1` if your embedding model must be pulled from HF

If transformer loading or JSON parsing fails, the local LLM wrapper falls back to heuristic generation.

## Known Behavior Notes

- Dense retrieval quality depends on embedding backend:
  - `hash://384` is stable/offline-first, but weaker semantically than sentence-transformers.
- Guardrails can return `NOT_FOUND` for vague/unsupported/low-evidence queries even if lexical matches exist.
- `POST /ask` status values are strictly `ANSWERED` or `NOT_FOUND`.

## Primary Project Docs

- `IMPLEMENTATION_GUIDE.md`
- `MANUAL_TEST_CHECKLIST.md`
- `SYSTEM_DIAGRAMS_AND_LEARNING_CURVE.md`
- `TUNING_NOTES.md`
