# Live Demo Runbook (8-10 min)

This runbook is the execution script for the post-presentation demo of the Vietnamese Internal Docs RAG Assistant.

## 1) Summary

Goal: run a controlled Streamlit demo that proves the full lifecycle:
- data/index readiness
- retrieval quality
- grounded answering with citations
- guardrail refusals
- access-control behavior
- debug transparency

## 2) Demo Goals and Success Criteria

1. Supported policy queries return `ANSWERED` with citations.
2. Conversational phrasing still works after robustness fix.
3. Restricted content with low access is blocked (`NOT_FOUND`).
4. Restricted content with allowed access succeeds (`ANSWERED`).
5. Unsupported question is safely refused with clarification.
6. Retrieval/debug evidence is visible and explainable.

Success condition: all 6 checkpoints pass in one live run.

## 3) API/Schema Impact

- No API contract changes.
- No schema/type changes.
- No endpoint changes.
- Existing interfaces only:
  - Streamlit: `src/ui/streamlit_app.py`
  - API: `GET /health`, `POST /ask`, `POST /search`
  - Request fields: `question/query`, `top_k`, `department_filter`, `access_level`, `debug`

## 4) Fixed Demo Configuration

- Config: `config/default.yaml`
- Runtime profile:
  - `llm_backend = heuristic`
  - `embedding_model_name = hash://384`
- Demo interface: Streamlit UI (primary)
- Timing: 8-10 minutes total
- Streamlit sidebar defaults:
  - `top_k = 5`
  - `Department = ""` (unless specified)
  - `Debug mode = true`

Safety rule: do not modify corpus/config during live demo.

## 5) Pre-Demo Preparation (T-30 to T-5)

1. Rebuild corpus and indices:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```

2. Run one-command verification:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/verify_pipeline.py
```

Required: final output must show `OVERALL: PASS`.

3. Start API:

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```

4. Start Streamlit (new terminal):

```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 streamlit run src/ui/streamlit_app.py
```

5. Keep a backup terminal open with curl commands from Section 9.

## 6) Live Demo Script (Minute-by-Minute)

### 0:00-0:40 — Readiness proof

- Show that system is ready (mention `verify_pipeline.py` passed).
- Optional quick command:

```bash
curl -s http://127.0.0.1:8000/health
```

- State contract: only `ANSWERED` or `NOT_FOUND`.

### 0:40-2:00 — Scenario A: Exact supported query

- Streamlit settings:
  - `Access Level = internal`
  - `Department = ""`
  - `top_k = 5`
- Ask:
  - `Theo tài liệu 'engineering branching strategy public 2024-10-12', mục 'Chiến lược nhánh mã nguồn' quy định gì?`
- Expect:
  - `status = ANSWERED`
  - `confidence = High` or `Medium`
  - `citations` includes `engineering_branching_strategy_public_2024-10-12-0-ebb6a5a6`

### 2:00-3:10 — Scenario B: Conversational robustness

- Streamlit settings:
  - `Access Level = public`
- Ask:
  - `Cho tôi biết về cách đặt tên nhánh`
- Expect:
  - `status = ANSWERED`
  - `citations` includes `engineering_branching_strategy_public_2024-10-12-1-1a138cde`

### 3:10-4:30 — Scenario C: Restricted denied

- Streamlit settings:
  - `Access Level = public`
- Ask:
  - `Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?`
- Expect:
  - `status = NOT_FOUND`
  - `confidence = Low`
  - `citations = []`
  - `clarifying_question` exists

### 4:30-5:40 — Scenario D: Restricted allowed

- Streamlit settings:
  - `Access Level = restricted`
- Ask same question:
  - `Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?`
- Expect:
  - `status = ANSWERED`
  - `citations` includes `security_access_restricted-0-1fa0a676`
  - answer contains `90`

### 5:40-6:50 — Scenario E: Unsupported question safety refusal

- Streamlit settings:
  - `Access Level = internal`
- Ask:
  - `Công ty quy định đồng phục bắt buộc vào thứ Hai như thế nào?`
- Expect:
  - `status = NOT_FOUND`
  - `clarifying_question` exists

### 6:50-8:00 — Scenario F: Retrieval transparency (`Search only`)

- Streamlit Search panel settings:
  - query: `đặt tên nhánh`
  - `Department = Engineering`
  - `Access Level = public`
  - `Debug mode = true`
- Expect:
  - `hits` non-empty
  - top hit includes `engineering_branching_strategy_public_2024-10-12-1-1a138cde`
  - debug section shows BM25 and dense candidates

## 7) Demo Scenario Matrix

| Scenario | UI Action | Query | Access Level | Expected Status | Must-Show Evidence |
| --- | --- | --- | --- | --- | --- |
| A Exact supported | Ask | Theo tài liệu ... Chiến lược nhánh mã nguồn ... | internal | ANSWERED | Citation `...-0-ebb6a5a6` |
| B Conversational | Ask | Cho tôi biết về cách đặt tên nhánh | public | ANSWERED | Citation `...-1-1a138cde` |
| C Restricted denied | Ask | Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu? | public | NOT_FOUND | `citations=[]`, clarifying question |
| D Restricted allowed | Ask | Same as C | restricted | ANSWERED | Citation `security_access_restricted-0-1fa0a676`, answer includes `90` |
| E Unsupported | Ask | Công ty quy định đồng phục bắt buộc vào thứ Hai như thế nào? | internal | NOT_FOUND | Clarifying question |
| F Retrieval debug | Search | đặt tên nhánh | public + Engineering | hits non-empty | Top hit `...-1-1a138cde`, debug candidates |

## 8) Presenter Role Split (4 Members)

- Member A (Data Pipeline): 30-second readiness intro (`ingest/index artifacts prepared`).
- Member B (Retrieval): runs Scenario F and explains BM25 + dense + hybrid evidence.
- Member C (RAG/Guardrails): runs Scenarios B and E, explains answer/refusal behavior.
- Member D (API/Eval/QA): opens with verification status, closes with reliability metrics.

## 9) Fallback Commands (If Streamlit Fails)

### Health

```bash
curl -s http://127.0.0.1:8000/health
```

### Scenario A

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Theo tài liệu \"engineering branching strategy public 2024-10-12\", mục \"Chiến lược nhánh mã nguồn\" quy định gì?","top_k":5,"access_level":"internal","debug":true}'
```

### Scenario B

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Cho tôi biết về cách đặt tên nhánh","top_k":5,"access_level":"public","debug":true}'
```

### Scenario C

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?","top_k":5,"access_level":"public","debug":true}'
```

### Scenario D

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?","top_k":5,"access_level":"restricted","debug":true}'
```

### Scenario E

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Công ty quy định đồng phục bắt buộc vào thứ Hai như thế nào?","top_k":5,"access_level":"internal","debug":true}'
```

### Scenario F (`/search`)

```bash
curl -s -X POST http://127.0.0.1:8000/search \
  -H 'content-type: application/json' \
  -d '{"query":"đặt tên nhánh","top_k":5,"department_filter":"Engineering","access_level":"public","debug":true}'
```

## 10) Failure Handling Rules

1. If Streamlit hangs:
   - switch to fallback curl commands (Section 9).
2. If result is unexpected:
   - re-run once with same settings;
   - verify `access_level`, `department_filter`, and `debug`.
3. If API unreachable:
   - restart API process;
   - confirm with `/health` before continuing.
4. If time overrun:
   - keep A, B, C, D mandatory;
   - skip F and summarize retrieval transparency verbally.

## 11) Acceptance Checklist Before Classroom

1. Dry-run all 6 scenarios once on presentation machine.
2. Confirm expected status and key citation IDs for each scenario.
3. Confirm Streamlit debug output appears for both Ask and Search.
4. Confirm restricted denied/allowed pair behaves exactly as expected.
5. Confirm unsupported query reliably returns `NOT_FOUND`.
6. Confirm fallback curl works for scenarios A-D at minimum.

## 12) Assumptions

- Audience: teacher evaluating technical completeness and reliability.
- Demo machine has dependencies installed and no environment conflicts.
- Corpus is baseline sample repo dataset.
- Explanation language can be Vietnamese; output/status/evidence IDs remain unchanged.
- This runbook introduces no code/API changes.

