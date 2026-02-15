# Manual Test Checklist (20 Scenarios with Exact Expected Outputs)

This checklist is for the current implementation and default config in `config/default.yaml`.

## Baseline Setup

1. Rebuild data and indices:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```
2. Run API:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```
3. Base URL used below: `http://127.0.0.1:8000`

## Assertions Format

- Use exact JSON assertions for pass/fail.
- For `clarifying_question`, assert exact full string where specified.
- For citations, assert exact `chunk_id` values listed.

## Scenario 1: Exact keyword policy lookup

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhan vien duoc nghi phep bao nhieu ngay moi nam?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- `confidence == "High"`
- `citations == [{"title":"hr leave policy internal","section_path":"HR > Leave Policy","chunk_id":"hr_leave_policy_internal-0-c735e348"}]`
- `answer` contains `"12 ngay moi nam"`
- `clarifying_question == null`

## Scenario 2: Paraphrased policy lookup

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Quyen nghi phep hang nam cua nhan vien la bao nhieu?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- `confidence == "High"`
- First citation `chunk_id == "hr_leave_policy_internal-0-c735e348"`
- `answer` contains `"12 ngay"`

## Scenario 3: Acronym-heavy query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"PR can bao nhieu reviewer truoc merge?","top_k":5,"access_level":"public"}'
```
Expected output:
- `status == "ANSWERED"`
- `confidence == "High"`
- First citation `chunk_id == "engineering_onboarding_public-1-699e11c3"`
- `answer` contains `"1 reviewer"`

## Scenario 4: Multi-hop query across two sections

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nghi phep va code review la gi?","top_k":5,"access_level":"internal"}'
```
Expected output (current behavior):
- `status == "ANSWERED"`
- `citations` length is `1`
- First citation `chunk_id == "hr_leave_policy_internal-0-c735e348"`

## Scenario 5: Outdated policy ambiguity trap

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Chinh sach nghi phep nam 2020 la gi?","top_k":5,"access_level":"internal"}'
```
Expected output (known limitation for baseline corpus):
- `status == "ANSWERED"`
- First citation `chunk_id == "hr_leave_policy_internal-0-c735e348"`
- `answer` contains `"12 ngay"`

## Scenario 6: Unsupported question outside corpus

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Quy dinh an toan bay noi bo la gi?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "NOT_FOUND"`
- `confidence == "Low"`
- `citations == []`
- `answer == "I couldn't find this in the current documents."`
- `clarifying_question == "Ban co the lam ro them bo phan, chinh sach, hoac moc thoi gian lien quan cho cau hoi nay khong? (Cau hoi goc: Quy dinh an toan bay noi bo la gi?)"`

## Scenario 7: Vague question requiring clarification

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Chinh sach?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "NOT_FOUND"`
- `citations == []`
- `clarifying_question == "Ban co the lam ro them bo phan, chinh sach, hoac moc thoi gian lien quan cho cau hoi nay khong? (Cau hoi goc: Chinh sach?)"`

## Scenario 8: Contradictory phrasing

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nghi phep moi nam vua 12 ngay vua 20 ngay dung khong?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- First citation `chunk_id == "hr_leave_policy_internal-0-c735e348"`
- `answer` contains `"12 ngay"`

## Scenario 9: Long multi-part query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Cho toi biet quy dinh nghi phep, dang ky nghi truoc may ngay, va quy dinh reviewer truoc khi merge","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- `citations == [{\"title\":\"hr leave policy internal\",\"section_path\":\"HR > Leave Policy\",\"chunk_id\":\"hr_leave_policy_internal-0-c735e348\"},{\"title\":\"engineering onboarding public\",\"section_path\":\"Engineering > Code Review\",\"chunk_id\":\"engineering_onboarding_public-1-699e11c3\"}]`
- `answer` contains both `"12 ngay"` and `"1 reviewer"`

## Scenario 10: Restricted query with low access

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Thong tin dang nhap nhay cam can xoay vong bao lau?","top_k":5,"access_level":"public"}'
```
Expected output:
- `status == "NOT_FOUND"`
- `citations == []`

## Scenario 11: Restricted query with allowed access

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Thong tin dang nhap nhay cam can xoay vong bao lau?","top_k":5,"access_level":"restricted"}'
```
Expected output:
- `status == "ANSWERED"`
- `confidence == "High"`
- First citation `chunk_id == "security_access_restricted-0-1fa0a676"`
- `answer` contains `"90 ngay"`

## Scenario 12: Similar docs with different update times

Setup for this scenario only:
1. Add `data/raw/hr_leave_policy_internal_2020-01-01.md` with content `Nhan vien duoc nghi phep 10 ngay moi nam.`
2. Add `data/raw/hr_leave_policy_internal_2025-01-01.md` with content `Nhan vien duoc nghi phep 15 ngay moi nam.`
3. Re-run indexing command.

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhan vien duoc nghi phep bao nhieu ngay moi nam theo ban moi nhat?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- First citation `title == "hr leave policy internal 2025-01-01"`
- `answer` contains `"15 ngay"`

## Scenario 13: English-Vietnamese mixed query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Policy ve annual leave va code review requirement la gi?","top_k":5,"access_level":"internal"}'
```
Expected output (current strict-guardrail behavior):
- `status == "NOT_FOUND"`
- `citations == []`

## Scenario 14: Typo-containing Vietnamese query

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhaan vien duoc nghi phepp bao nhieu ngay?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- First citation `chunk_id == "hr_leave_policy_internal-0-c735e348"`
- `answer` contains `"12 ngay"`

## Scenario 15: Duplicate chunk collision case

Setup for this scenario only:
1. Add `data/raw/hr_leave_policy_internal_copy_a.md` and `data/raw/hr_leave_policy_internal_copy_b.md` with identical leave-policy content.
2. Re-run indexing command.

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"Nhan vien duoc nghi phep bao nhieu ngay moi nam?","top_k":5,"access_level":"internal"}'
```
Expected output:
- `status == "ANSWERED"`
- `citations` length is `1` (duplicate evidence deduped)
- `answer` has only one bullet line

## Scenario 16: Zero-result retrieval edge case

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"zzzzzzzzzzzzzzzz","top_k":5,"access_level":"internal"}'
```
Expected output:
- `hits == []`

## Scenario 17: Very high top_k request

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"nghi phep","top_k":50,"access_level":"internal"}'
```
Expected output:
- HTTP `200`
- `hits` length is `>= 1`
- First hit `chunk_id == "hr_leave_policy_internal-0-c735e348"`

## Scenario 18: Malformed API payload

Request:
```bash
curl -s -o /tmp/malformed.json -w '%{http_code}' -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":123}'
```
Expected output:
- HTTP status code `422`
- Error body contains validation detail for `question`

## Scenario 19: LLM format-violation recovery path

Setup for this scenario only:
1. Create a config with `models.llm_backend: "transformers"` and an invalid or unavailable model name.
2. Start API using that config.

Request:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"PR can bao nhieu reviewer truoc merge?","top_k":5,"access_level":"public"}'
```
Expected output:
- Service falls back to heuristic generation.
- `status == "ANSWERED"`
- First citation `chunk_id == "engineering_onboarding_public-1-699e11c3"`

## Scenario 20: Repeated query consistency check

Request:
Run the same request twice:
```bash
curl -s -X POST http://127.0.0.1:8000/ask -H 'content-type: application/json' -d '{"question":"PR can bao nhieu reviewer truoc merge?","top_k":5,"access_level":"public"}'
```
Expected output:
- Response 1 and Response 2 have identical:
  - `status`
  - `confidence`
  - `citations[0].chunk_id`
  - `answer`

## Cleanup Notes for Scenario-specific Setup

- Remove temporary scenario docs from `data/raw/` after each scenario.
- Re-run indexing command to return to baseline corpus.
