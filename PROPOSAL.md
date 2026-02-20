# Project Proposal (Aligned With Current Implementation)

## 1. Project Title

Vietnamese Internal Docs QA Assistant (RAG, Citation-Grounded, Guardrailed)

## 2. Problem Statement

Internal policy knowledge is spread across many documents (HR, Engineering, Security, Operations). Manual lookup is slow, and free-form LLM answers can hallucinate.

This project builds a local-first QA system that:

- retrieves relevant internal evidence,
- answers with citations,
- and returns `NOT_FOUND` when support is insufficient.

## 3. Current Implementation Scope

Implemented:

1. Ingestion for `PDF`, `DOCX`, `MD`, `HTML`, `TXT`
2. Unicode normalization and deterministic section-aware chunking
3. Metadata extraction from filenames (`department`, `access_level`, `updated_at`)
4. Index build pipeline:
   - BM25 index
   - Dense index (hash embedding default; sentence-transformers optional)
5. Hybrid retrieval with score fusion and filtering
6. RAG answer packaging with citations
7. Guardrail policy with confidence + strict no-answer logic
8. FastAPI endpoints: `/health`, `/search`, `/ask`
9. Streamlit UI for QA demo and debug visualization
10. Evaluation scripts and error-analysis reports
11. Manual test checklist with 20 scenarios

Not implemented yet (future work):

1. Enterprise auth/SSO and IAM integration
2. Deployment-grade monitoring/observability
3. Production infra hardening (autoscaling, SLO alerts)
4. Full model-serving optimization for transformer inference

## 4. Technical Design (As-Built)

### 4.1 Offline Pipeline

1. Parse raw docs from `data/raw/`
2. Normalize text and split into section-aware chunks
3. Persist chunks to `data/processed/chunks.jsonl`
4. Build BM25 index (`data/indices/bm25.pkl`)
5. Build dense index (`data/indices/dense/`)

### 4.2 Online Pipeline

1. Receive query via `/search` or `/ask`
2. Retrieve BM25 and dense candidates
3. Apply weighted hybrid fusion + boosts + threshold filters
4. Generate draft answer via local LLM wrapper (heuristic by default)
5. Filter citations and compute confidence
6. Apply guardrail checks
7. Return `ANSWERED` or `NOT_FOUND`

## 5. API Contracts (Implemented)

### GET `/health`

Response fields:

- `status`
- `version`
- `indices_loaded`
- `llm_loaded`

### POST `/search`

Request:

- `query`, `top_k`, `department_filter`, `access_level`, `debug`

Response:

- `hits[]`: `doc_id`, `title`, `section_path`, `chunk_id`, `score`, `retrieval_source`, `snippet`
- optional `debug`

### POST `/ask`

Request:

- `question`, `top_k`, `department_filter`, `access_level`, `debug`

Response:

- `answer`, `citations[]`, `confidence`, `status`, `clarifying_question`, optional `debug`

## 6. Default Runtime Decisions

From `config/default.yaml`:

- `llm_backend = heuristic`
- `embedding_model_name = hash://384`
- retrieval fusion = weighted (`0.62 lexical / 0.38 dense`)

Rationale:

- stable local execution,
- reproducible offline behavior,
- fast iteration for MVP demo.

## 7. Evaluation Approach

Implemented metrics:

1. Retrieval:
   - Recall@k
   - MRR
   - Evidence Hit Rate
2. No-answer behavior:
   - no-answer precision
   - no-answer recall
   - no-answer F1
3. Error report:
   - retrieval misses
   - false refusals
   - negative hallucinations
   - citation mismatch patterns

Core scripts:

- `scripts/run_eval.py`
- `scripts/holdout_error_report.py`
- `scripts/verify_pipeline.py`

## 8. Current Maturity Statement

This implementation is an MVP that demonstrates the complete idea end-to-end:

- ingestion -> indexing -> retrieval -> answering -> guardrails -> API/UI -> evaluation.

It is suitable for:

- coursework demo,
- technical presentation,
- controlled internal prototype.

It is not yet production-ready without auth, monitoring, and deployment hardening.

## 9. Next-Phase Plan

1. Dense retrieval quality upgrade (while preserving reproducibility)
2. Better calibration for hard negative queries
3. Add structured runtime telemetry (fallback rates, guardrail reasons)
4. Add deployment checklist and CI quality gates

## 10. Solo Execution Model

This repository is maintained as a solo implementation.

- Design, code, eval, and documentation are serialized for consistency.
- All scope and timelines should be interpreted in this solo-delivery context.
