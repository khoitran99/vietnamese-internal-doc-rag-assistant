# Tuning Notes

## Goal
Improve retrieval relevance and guardrail strictness for Vietnamese internal-doc QA, while keeping citation grounding and `NOT_FOUND` behavior stable.

## Key Decisions
- Indexed metadata with content (`title + section_path + text`) for both BM25 and dense retrieval.
- Added query-aware metadata boosting (doc/section phrase matching, section token overlap count).
- Normalized tokens with Vietnamese accent handling and targeted aliases for mixed-language queries (`branch -> nhanh`, `team -> nhom`, `thuat -> engineering`).
- Switched overlap filtering to use `max(text_overlap, metadata_overlap)` to avoid dropping correct section hits.
- Tightened citation filtering by reranking candidate citations against:
  - retrieval score,
  - question-text overlap,
  - doc-title/section phrase match,
  - duplicate-signature suppression.
- Added guardrail gates for safer `NOT_FOUND`:
  - yes/no question stricter relevance,
  - number support check,
  - acronym support check (exact uppercase token match, e.g. `AI`, `SLA`),
  - open-query token coverage,
  - top-document consistency,
  - top-two score-ratio tie handling.

## Config/Threshold Direction
- Retrieval tuned toward stronger metadata usage and recall.
- Guardrails tuned to reject unsupported but lexically-similar evidence while preserving paraphrased positives.
- Debug payload now exposes the main guardrail signals used in decisions.

## Evaluation Workflow
- Added split datasets (`train`/`holdout`) and an extra unseen challenge set.
- Added error report generator for failure buckets:
  - retrieval miss,
  - citation mismatch,
  - false refusal,
  - negative hallucination.

## Current Snapshot (local eval)
- `qa_eval_train.jsonl`: retrieval recall@5 = `1.0`, false refusal = `0.0`, negative hallucination = `0.0`
- `qa_eval_holdout.jsonl`: retrieval recall@5 = `1.0`, false refusal = `0.0`, negative hallucination = `0.0`
- `qa_eval_unseen_challenge.jsonl`: retrieval recall@5 = `1.0`, false refusal = `0.0`, negative hallucination = `0.0`

## Notes
- Current results are very strong on local datasets; maintain a separate external/unseen benchmark to monitor overfitting risk.
