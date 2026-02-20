# Tuning Notes (Current)

## Active Baseline

Current baseline is intentionally conservative and stable:

- `llm_backend: heuristic`
- `embedding_model_name: hash://384`
- `fusion_method: weighted`
- `lexical_weight: 0.62`
- `dense_weight: 0.38`

## Retrieval Decisions

Implemented tuning decisions:

- Index text uses `title + section_path + text` for BM25 and dense index build.
- Query-aware lexical/dense reweighting in hybrid retrieval.
- Metadata boost from title/section overlap.
- Recency boost from `updated_at`.
- Threshold filtering on:
  - absolute score
  - relative score
  - query-token overlap

## Guardrail Decisions

Implemented guardrails include:

- Citation relevance filtering and deduplication.
- Confidence levels (`High`/`Medium`/`Low`) from evidence strength + citation coverage.
- Strict `NOT_FOUND` on insufficient support.
- Extra checks:
  - yes/no relevance
  - number support
  - acronym support
  - token coverage
  - top-document consistency

## Latest Verified Baseline Metrics (default config)

Command:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_eval.py --config config/default.yaml --top_k 5
```

Observed output (current sample corpus):

- Retrieval
  - BM25: recall@5 `1.0`, MRR `0.9778`
  - Dense (hash backend): recall@5 `0.1222`, MRR `0.0526`
  - Hybrid: recall@5 `1.0`, MRR `0.9944`
- Answer guardrail
  - no-answer precision `1.0`
  - no-answer recall `1.0`
  - no-answer F1 `1.0`

## Transformer Experiment Summary

`transformers` backend was tested with local Qwen and compared against heuristic.

Result:

- No measurable quality gain on the project metrics in current evaluation scripts.
- Runtime was significantly slower and less stable on local CPU profile.

Decision:

- Keep heuristic as default and primary demo/eval path.
- Keep transformer path as optional experimentation mode only.

## Practical Next Tuning Targets

1. Improve dense semantic retrieval while keeping offline reproducibility.
2. Reduce residual false-positive risk on hard negative queries.
3. Add explicit fallback-rate instrumentation (`transformers` parse fallback vs native generation) if LLM comparison is revisited.
