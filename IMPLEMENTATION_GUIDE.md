# Implementation Guide (Current System)

This guide reflects the current as-built implementation in this repository.

## 1. Current Scope Status

Completed in code:

- Config loading and directory bootstrap
- Ingestion for `PDF`, `DOCX`, `MD`, `HTML`, `TXT`
- Text cleanup + section-aware deterministic chunking
- BM25 + dense retrieval + weighted hybrid fusion
- Retrieval filters (score, relative score, token overlap)
- Metadata and recency boosting
- RAG answer packaging with citations
- Guardrails for confidence and strict `NOT_FOUND`
- FastAPI endpoints (`/health`, `/search`, `/ask`)
- Streamlit QA UI
- Eval scripts and error-analysis report script
- Unit/integration tests

Not production-hardened yet:

- Authentication/authorization beyond metadata filtering
- Observability (structured logs, tracing, dashboards)
- Deployment hardening (containerization, CI/CD gates, SLO monitoring)

## 2. Default Runtime Mode

From `config/default.yaml`:

- `llm_backend = heuristic`
- `embedding_model_name = hash://384`

This is the stable offline-first profile.

## 3. Build and Run

### 3.1 Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Ingest and index

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```

### 3.3 Start API

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```

### 3.4 Start UI

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 streamlit run src/ui/streamlit_app.py
```

## 4. Verification Flow

### 4.1 Dry config/path check

```bash
PYTHONPATH=. python3 scripts/dry_check.py --config config/default.yaml
```

### 4.2 Test suite

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
```

### 4.3 Eval summary

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --top_k 5
```

### 4.4 Holdout error report

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/holdout_error_report.py \
  --config config/default.yaml \
  --dataset data/eval/qa_eval_holdout.jsonl \
  --top_k 5 \
  --sample_limit 5
```

### 4.5 One-command pipeline verification

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/verify_pipeline.py
```

This script runs Steps 2/4/5/7 automatically and prints overall PASS/FAIL.

## 5. API Contract (Implemented)

### 5.1 GET `/health`

Response fields:

- `status`
- `version`
- `indices_loaded`
- `llm_loaded`

### 5.2 POST `/search`

Request fields:

- `query`
- `top_k`
- `department_filter`
- `access_level`
- `debug`

Response fields:

- `hits[]` (`doc_id`, `title`, `section_path`, `chunk_id`, `score`, `retrieval_source`, `snippet`)
- optional `debug`

### 5.3 POST `/ask`

Request fields:

- `question`
- `top_k`
- `department_filter`
- `access_level`
- `debug`

Response fields:

- `answer`
- `citations[]`
- `confidence`
- `status` (`ANSWERED` or `NOT_FOUND`)
- `clarifying_question`
- optional `debug`

## 6. Manual QA Reference

Use `MANUAL_TEST_CHECKLIST.md` as the primary manual QA script.

- Includes 20 scenarios
- Includes Postman guidance
- Includes expected status/citation patterns

## 7. Optional Transformer Path

The code supports `llm_backend=transformers` in `src/rag/local_llm.py`.

Practical guidance:

- Treat this as optional experimentation mode.
- Keep heuristic as baseline for stable demos.
- Validate with `scripts/run_eval.py` and `scripts/holdout_error_report.py` before adopting.
