# Vietnamese Internal Docs RAG Assistant

A production-minded Retrieval-Augmented Generation (RAG) assistant for Vietnamese internal company documentation.

## What Is Implemented

- Local document ingestion for `PDF`, `DOCX`, `MD`, `HTML`
- Unicode-safe normalization and deterministic section-aware chunking
- Hybrid retrieval (`BM25` + dense embeddings + fusion)
- Retrieval tuning with thresholds, overlap filtering, and recency boost
- Guardrails for confidence, citation relevance, and strict `NOT_FOUND`
- FastAPI endpoints: `GET /health`, `POST /search`, `POST /ask`
- Streamlit demo UI
- Evaluation pipeline with BM25/dense/hybrid metric summaries
- Manual QA checklist with 20 scenarios
- One-command verification script for steps 2/4/5/7

## Project Layout

- `config/default.yaml`: runtime and tuning configuration
- `data/raw/`: source documents
- `data/processed/chunks.jsonl`: chunked corpus (generated)
- `data/indices/`: BM25 + dense indices (generated)
- `data/eval/qa_eval.jsonl`: evaluation dataset
- `src/`: application code (ingestion, retrieval, RAG, guardrails, API, UI, eval)
- `scripts/`: operational scripts (`ingest_and_index`, `run_api`, `run_eval`, `verify_pipeline`, `generate_eval_dataset`, `split_eval_dataset`, `holdout_error_report`)
- `tests/`: unit/integration coverage
- `MANUAL_TEST_CHECKLIST.md`: exact manual test requests and expected outputs
- `IMPLEMENTATION_GUIDE.md`: phase-oriented implementation and verification guide
- `SYSTEM_DIAGRAMS_AND_LEARNING_CURVE.md`: visual architecture diagrams + student learning path

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Run

1. Build chunks and indices.

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```

2. Start API.

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```

3. Start UI (new terminal).

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 streamlit run src/ui/streamlit_app.py
```

## One-Command Verification

Run automated verification for:
- Step 2: rebuild chunks/indices
- Step 4: tests
- Step 5: eval
- Step 7: API smoke checks

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/verify_pipeline.py
```

Expected output format:
- per-step `[PASS]` / `[FAIL]`
- final `OVERALL: PASS` or `OVERALL: FAIL`

## Evaluation

Run retrieval eval summary:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --top_k 5
```

Output includes metrics for:
- `bm25`
- `dense`
- `hybrid`

Generate curated eval dataset (120 items):

```bash
PYTHONPATH=. python3 scripts/generate_eval_dataset.py --chunks data/processed/chunks.jsonl --output data/eval/qa_eval.jsonl --target 120
```

Current curated distribution:
- `positive_single`: 78
- `positive_multi`: 12
- `negative`: 30

Create deterministic train/holdout split:

```bash
PYTHONPATH=. python3 scripts/split_eval_dataset.py \
  --input data/eval/qa_eval.jsonl \
  --train-output data/eval/qa_eval_train.jsonl \
  --holdout-output data/eval/qa_eval_holdout.jsonl \
  --holdout-ratio 0.2 \
  --seed 42
```

Evaluate train split:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --dataset data/eval/qa_eval_train.jsonl --top_k 5
```

Evaluate holdout split:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --dataset data/eval/qa_eval_holdout.jsonl --top_k 5
```

Generate holdout error analysis report:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/holdout_error_report.py \
  --config config/default.yaml \
  --dataset data/eval/qa_eval_holdout.jsonl \
  --top_k 5 \
  --sample_limit 5
```

## Manual QA

Use:

- `MANUAL_TEST_CHECKLIST.md`

It contains all 20 scenarios with exact request payloads and expected outputs.

## Config and Tuning

Main tuning knobs are in `config/default.yaml`.

Retrieval knobs:
- `lexical_weight`
- `dense_weight`
- `min_score_threshold`
- `min_relative_score`
- `min_query_token_overlap`
- `candidate_size`
- `recency_weight`

Guardrail knobs:
- `min_citation_coverage`
- `min_citation_relevance`
- `min_top_relevance`
- `max_citations`

## Notes

- Default embedding backend is `hash://384` for offline-safe execution.
- To force offline mode, keep `DISABLE_EXTERNAL_MODELS=1`.
- If you switch to external models, remove that env var and set an embedding model name in config.
- Output statuses are `ANSWERED` and `NOT_FOUND`.

## Troubleshooting

- If verification fails at Step 7 with missing FastAPI client support, install dependencies:

```bash
pip install -r requirements.txt
```

- If chunk IDs change after editing raw docs, re-run ingest/index and update eval gold IDs/checklist references accordingly.
