# Implementation Guide and Phase Verification

This guide maps directly to the approved 8-week plan and provides practical commands for each phase.

## Phase 0: Bootstrap

### Deliverables
- Config schema and defaults in `config/default.yaml`
- Shared schemas and module skeleton under `src/`
- Basic test harness under `tests/`

### Verify
- `PYTHONPATH=. python scripts/dry_check.py --config config/default.yaml`
- `PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py'`

### Manual test
1. Start API: `PYTHONPATH=. python scripts/run_api.py --config config/default.yaml`
2. Check health: `curl http://127.0.0.1:8000/health`

## Phase 1: Ingestion + Chunking

### Deliverables
- Parsers for `PDF`, `DOCX`, `MD`, `HTML`
- Text normalization and deterministic section-aware chunking
- Chunk output in `data/processed/chunks.jsonl`

### Verify
- `PYTHONPATH=. python scripts/ingest_and_index.py --config config/default.yaml`
- Inspect chunk schema and section paths in `data/processed/chunks.jsonl`

### Manual test
1. Add 10 docs in `data/raw/`
2. Re-run ingest.
3. Confirm restricted docs include `access_level=restricted`.

## Phase 2: BM25 baseline

### Deliverables
- BM25 index build/load
- `/search` endpoint returning scored evidence

### Verify
- `curl -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"nghi phep","top_k":5,"debug":true}'`

### Manual test
1. Test acronym-heavy query.
2. Test negative query and inspect low relevance results in debug output.

## Phase 3: Dense + Hybrid

### Deliverables
- Dense embedding index with fallback hash backend
- Hybrid fusion (`weighted` and `rrf`)

### Verify
- In API debug mode, compare `bm25` and `dense` lists.
- Confirm hybrid top hits contain semantic matches.

### Manual test
1. Query without exact keywords.
2. Compare `search` results with fusion method toggled in config.

## Phase 4: RAG + citations

### Deliverables
- Prompt contract
- Local LLM wrapper (`heuristic` default, optional `transformers`)
- Citation list in `/ask` response

### Verify
- `curl -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhan vien duoc nghi phep bao nhieu ngay?","top_k":5,"debug":true}'`

### Manual test
1. Ask 15 known questions and confirm citations exist.
2. Confirm answer format remains stable for multi-part questions.

## Phase 5: Guardrails

### Deliverables
- Confidence scoring
- `NOT_FOUND` policy with clarifying question fallback

### Verify
- Ask out-of-scope questions and verify `status=NOT_FOUND`.

### Manual test
1. Vague query should return clarifying question.
2. Unsupported query should not fabricate policy details.

## Phase 6: Evaluation

### Deliverables
- Eval dataset loader
- Retrieval metrics (`Recall@k`, `MRR`, `Evidence Hit Rate`)
- Evaluation runner

### Verify
- `PYTHONPATH=. python scripts/run_eval.py --config config/default.yaml --top_k 5`

### Manual test
1. Fill `gold_chunk_ids` in `data/eval/qa_eval.jsonl`.
2. Re-run eval and inspect summary metrics.

## Phase 7: API hardening + UI polish

### Deliverables
- Request validation and error handling
- Streamlit UI with confidence, citations, debug

### Verify
- `PYTHONPATH=. streamlit run src/ui/streamlit_app.py`

### Manual test
1. Dry-run a 10-minute demo script.
2. Validate restricted-content behavior via `access_level` setting.

## Phase 8: Packaging

### Deliverables
- Final runbook (`README.md`, this guide)
- Reproducible scripts for ingest/index/serve/eval
- Test suite and sample data

### Verify
- Fresh run sequence:
  1. `python scripts/dry_check.py`
  2. `python scripts/ingest_and_index.py`
  3. `python scripts/run_api.py`
  4. `python scripts/run_eval.py`

## Quality Gates

- Gate A: Search is stable and scored.
- Gate B: `/ask` returns citations.
- Gate C: `NOT_FOUND` and confidence guardrails operate correctly.
- Gate D: Retrieval metrics script reproducible.
- Gate E: API + UI demo pass complete scripted flow.

## Manual QA Checklist

- Use `MANUAL_TEST_CHECKLIST.md` for the 20-scenario manual validation script with exact expected outputs.
