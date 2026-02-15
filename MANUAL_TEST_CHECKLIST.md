# Manual Test Checklist (20 Scenarios, Updated)

This checklist is aligned with the current implementation and default config in `config/default.yaml`.

## Baseline Setup

1. Rebuild corpus and indices:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```
2. Start API:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```
3. Base URL: `http://127.0.0.1:8000`

Optional quick automated sanity check:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/verify_pipeline.py
```

## Postman Pack (Recommended)

- Import collection: `postman/Vietnamese_Internal_Docs_RAG_Manual_Scenarios.postman_collection.json`
- Import environment: `postman/Local_RAG_API.postman_environment.json`
- Select environment `Local RAG API`.
- Run scenarios `S01` to `S20` directly in Postman (no shell escaping needed).

## Assertion Rules (Important)

- Prefer `status`, `confidence`, and key citation presence over exact full citation arrays.
- Current heuristic answerer may return multiple citations; verify required `chunk_id` is present.
- If you use Postman, do **not** paste the entire `curl` command body directly.
  - The `curl` examples use shell escaping like `'"'"'` which is valid for terminal quoting, not JSON.
  - In Postman, use `Body -> raw -> JSON` and paste a clean JSON object only.
- For `NOT_FOUND`, assert:
  - `status == "NOT_FOUND"`
  - `confidence == "Low"`
  - `citations == []`
  - `answer == "I couldn't find this in the current documents."`

## Scenario 1: Exact keyword policy lookup

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'engineering branching strategy public 2024-10-12'"'"', mục '"'"'Chiến lược nhánh mã nguồn'"'"' quy định gì?","top_k":5,"access_level":"internal"}'
```
Postman raw JSON body (copy this, not the shell-escaped string):
```json
{
  "question": "Theo tài liệu 'engineering branching strategy public 2024-10-12', mục 'Chiến lược nhánh mã nguồn' quy định gì?",
  "top_k": 5,
  "access_level": "internal"
}
```
Expected:
- `status == "ANSWERED"`
- `confidence` is `"High"` or `"Medium"`
- `citations` contains `engineering_branching_strategy_public_2024-10-12-0-ebb6a5a6`

## Scenario 2: Paraphrased policy lookup

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Trong vận hành kỹ thuật, tài liệu '"'"'engineering branching strategy public 2024-10-12'"'"' yêu cầu gì ở mục '"'"'Chiến lược nhánh mã nguồn'"'"'?","top_k":5,"access_level":"internal"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains `engineering_branching_strategy_public_2024-10-12-0-ebb6a5a6`

## Scenario 3: Acronym-heavy query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'operations it helpdesk sla public 2024-09-25'"'"', mục '"'"'SLA hỗ trợ IT'"'"' quy định gì?","top_k":5,"access_level":"public"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains `operations_it_helpdesk_sla_public_2024-09-25-0-5d9e9188`

## Scenario 4: Multi-hop query across two sections

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Hãy tổng hợp yêu cầu chính ở mục '"'"'Hoàn ứng và thanh toán chi phí'"'"' và '"'"'Hồ sơ bắt buộc'"'"' trong tài liệu '"'"'finance expense reimbursement internal 2024-12-20'"'"'.","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains both:
  - `finance_expense_reimbursement_internal_2024-12-20-0-5c2e463b`
  - `finance_expense_reimbursement_internal_2024-12-20-1-e87e8e7c`

## Scenario 5: Outdated policy ambiguity trap

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Chính sách nghỉ phép năm 2020 là gì?","top_k":5,"access_level":"internal"}'
```
Expected (current strict guardrail behavior):
- `status == "NOT_FOUND"`

## Scenario 6: Unsupported question outside corpus

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Công ty quy định đồng phục bắt buộc vào thứ Hai như thế nào?","top_k":5,"access_level":"internal"}'
```
Expected:
- `status == "NOT_FOUND"`
- `clarifying_question` is not `null`

## Scenario 7: Vague question requiring clarification

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Chính sách?","top_k":5,"access_level":"internal"}'
```
Expected:
- `status == "NOT_FOUND"`
- `clarifying_question` contains `Cau hoi goc`

## Scenario 8: Contradictory query phrasing

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nghỉ phép mỗi năm vừa 12 ngày vừa 20 ngày đúng không?","top_k":5,"access_level":"internal"}'
```
Expected (current behavior):
- `status == "ANSWERED"`
- `citations` contains `hr_leave_policy_internal-0-c735e348`
- `answer` contains `12`

## Scenario 9: Long multi-part query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Hãy tổng hợp yêu cầu chính ở mục '"'"'Thời hạn lưu trữ hồ sơ'"'"' và '"'"'Lưu trữ và truy xuất'"'"' trong tài liệu '"'"'legal document retention policy internal 2024-10-28'"'"'.","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains both:
  - `legal_document_retention_policy_internal_2024-10-28-0-8122b39d`
  - `legal_document_retention_policy_internal_2024-10-28-1-711e692f`

## Scenario 10: Restricted-document query under low access

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?","top_k":5,"access_level":"public"}'
```
Expected:
- `status == "NOT_FOUND"`

## Scenario 11: Restricted-document query under allowed access

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains `security_access_restricted-0-1fa0a676`
- `answer` contains `90`

## Scenario 12: Similar policy section disambiguation

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'operations procurement policy internal 2025-01-08'"'"', mục '"'"'Kiểm soát nhà cung cấp'"'"' quy định gì?","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains `operations_procurement_policy_internal_2025-01-08-2-ca599ae7`

## Scenario 13: English-Vietnamese mixed query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Policy annual leave trong tài liệu '"'"'hr leave policy internal'"'"' là gì?","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- `citations` contains `hr_leave_policy_internal-0-c735e348`

## Scenario 14: Typo-containing Vietnamese query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhaan vien duoc nghi phepp bao nhieu ngay?","top_k":5,"access_level":"restricted"}'
```
Expected (current strict behavior):
- `status == "NOT_FOUND"`

## Scenario 15: Duplicate chunk collision case

Setup (scenario-only):
1. Add `data/raw/hr_leave_policy_internal_copy_a.md` and `data/raw/hr_leave_policy_internal_copy_b.md` with identical leave-policy text.
2. Rebuild indices.

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'hr leave policy internal'"'"', mục '"'"'Leave Policy'"'"' quy định gì?","top_k":5,"access_level":"restricted"}'
```
Expected:
- `status == "ANSWERED"`
- Citation signatures are deduplicated (no repeated identical evidence text in `citations`)

## Scenario 16: Zero-result retrieval edge case

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"zzzzzzzzzzzzzzzz","top_k":5,"access_level":"internal"}'
```
Expected:
- `hits == []`

## Scenario 17: Very high `top_k` request

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"Theo tài liệu '"'"'engineering onboarding public'"'"', mục '"'"'Code Review'"'"' quy định gì?","top_k":50,"access_level":"restricted"}'
```
Expected:
- HTTP `200`
- `hits` length `>= 5`
- `hits` contains `engineering_onboarding_public-1-699e11c3`

## Scenario 18: Malformed API payload

Request:
```bash
curl -s -o /tmp/malformed.json -w '%{http_code}' -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"test","top_k":0}'
```
Expected:
- HTTP status code `422`
- Error body in `/tmp/malformed.json` contains validation detail for `top_k`

## Scenario 19: LLM output format-violation recovery

Setup (scenario-only):
1. Create temp config with:
   - `models.llm_backend: "transformers"`
   - invalid/unavailable `models.llm_model_name`
2. Start API with that config.

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'engineering onboarding public'"'"', mục '"'"'Code Review'"'"' quy định gì?","top_k":5,"access_level":"public"}'
```
Expected:
- Service falls back to heuristic behavior.
- `status == "ANSWERED"`
- `citations` contains `engineering_onboarding_public-1-699e11c3`

## Scenario 20: Repeated query consistency check

Request (run twice):
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Theo tài liệu '"'"'engineering onboarding public'"'"', mục '"'"'Code Review'"'"' quy định gì?","top_k":5,"access_level":"public"}'
```
Expected:
- Response 1 and Response 2 have identical:
  - `status`
  - `confidence`
  - first citation `chunk_id`
  - `answer`

## Cleanup for Scenario-specific Setup

- Remove temporary scenario docs/configs after testing.
- Rebuild indices to return to baseline:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```
