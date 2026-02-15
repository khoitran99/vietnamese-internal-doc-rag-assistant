# Project Proposal: Vietnamese Company Docs QA Assistant (Generative RAG)

## 1. Project Title

**Enterprise-Safe Vietnamese RAG Assistant for Internal Company Documentation**  
(Answer + Citations + Confidence + No-Answer Guardrails)

## 2. Motivation and Problem Statement

Internal company knowledge is fragmented across HR policies, onboarding guides, engineering SOPs, and security procedures. Searching manually is slow and error-prone, while generic chatbots risk hallucination and privacy leakage.

This project builds a Retrieval-Augmented Generation (RAG) system that answers Vietnamese questions using only company documents, always returning verifiable citations, a confidence level, and a safe no-answer fallback when evidence is insufficient.

## 3. Goals and Success Criteria

### 3.1 Goals

1. Accurate answers grounded in company docs.
2. Traceable outputs: show which documents/sections support the answer.
3. Robustness: handle ambiguous questions and `NOT_FOUND` cases.
4. Production-minded design: modular pipeline, logging, access-control metadata, reproducible runs.
5. Strong evaluation: retrieval metrics + answer quality metrics + error analysis.

### 3.2 Success Criteria (Measurable)

- Evidence Hit Rate@k >= target (for example, >= 85% for gold doc in top-5 on the test set).
- Human Answer Correctness average >= 4.0/5.
- Citation Correctness >= 90% (citations truly support claims).
- No-Answer Precision is high (system rarely fabricates unsupported answers).

## 4. Scope (What Is In / Out)

### 4.1 In Scope

- Ingest internal docs (`PDF`, `DOCX`, `MD`, `HTML` exports).
- Chunking + metadata extraction (doc title, section, updated date, department).
- Hybrid retrieval (`BM25` + dense embeddings + `FAISS`).
- Generative answering with citations + confidence + safe fallback.
- UI demo (`Streamlit`/`Gradio`) + API layer (`FastAPI`).
- Evaluation set creation + experiments + ablation study.
- Report + slides + live demo.

### 4.2 Out of Scope (to keep 8 weeks realistic)

- Full enterprise SSO integration (roles/permissions are mocked via metadata).
- Fine-tuning an LLM from scratch.
- Full multi-agent workflow/tool-calling beyond retrieval and response.

## 5. Alignment With Course Requirements

The final project guideline expects a complete NLP system with strong evaluation and demo, plus code, report, and presentation.

This proposal aligns with **Option D (QA System)** structure (retriever + reader/generator), including:

- Document retrieval + multi-document handling.
- Confidence scoring + no-answer behavior.
- Simple UI for demo.
- Proper evaluation metrics (retrieval + answer quality).

It also adds a modern layer: **Generative RAG plus grounded evidence tracing**, aligned with current transformer-based QA practice.

## 6. System Design

### 6.1 High-Level Architecture

#### Offline (Indexing)

1. Collect docs and parse text.
2. Clean and normalize.
3. Chunk text (overlap windows).
4. Build indexes:
   - BM25 index
   - Dense embedding index (`FAISS`)
5. Store metadata (`doc_id`, `title`, `section`, `updated_at`, `access_level`).

#### Online (Answering)

1. Receive user question.
2. Retrieve (`BM25` + dense), then merge top-k.
3. Rerank (optional) and select evidence.
4. Assemble prompt: question + evidence snippets + instruction format.
5. LLM generates:
   - Answer (short + actionable)
   - Citations (doc + section)
   - Confidence
   - No-answer fallback when needed

### 6.2 Core Components

#### A. Document Ingestion and Chunking

**Supported inputs**

- `PDF`, `DOCX`, Markdown, `HTML` (Confluence/Notion export).

**Chunking strategy**

- Chunk size: approximately 300-600 tokens.
- Overlap: 50-100 tokens.
- Preserve structure: headings mapped to `section_path` (example: `HR > Leave > Annual Leave`).

**Metadata fields**

- `doc_id`, `title`, `section_path`, `chunk_id`
- `department` (`HR` / `Engineering` / `Security` / `General`)
- `updated_at` (from doc metadata or manual config)
- `access_level` (`public` / `internal` / `restricted`)

#### B. Hybrid Retrieval (Modern and Practical)

- `BM25`: exact-match, acronyms, policy codes.
- Dense retrieval: semantic matching via embeddings.
- `FAISS`: fast vector search.

**Fusion strategy (simple and effective)**

- Take top-k from BM25 and top-k from dense retrieval.
- Normalize scores.
- Weighted merge (for example, `0.5 lexical + 0.5 dense`) or Reciprocal Rank Fusion.
- Return final top-k evidence chunks.

#### C. Generative Answering (RAG Prompt Contract)

The model must follow a strict schema:

**Output format**

- Answer: concise steps/bullets.
- Citations: evidence chunks used (`title + section + chunk_id`).
- Confidence: `High` / `Medium` / `Low`.
- If confidence is low: ask a clarifying question or state `NOT_FOUND`.

**No-hallucination rule**

- If the answer is not explicitly supported by provided context, respond with `NOT_FOUND`.

#### D. Guardrails and No-Answer Handling

**Heuristics for no-answer decision**

- Top retrieval scores are below threshold.
- Evidence chunks have low semantic similarity.
- Model cannot cite at least one chunk for each major claim.

**Fallback response**

- "I couldn’t find this in the current documents" + top related sections + one clarifying question.

#### E. UI Demo and API

**FastAPI endpoints**

- `/ask`: question -> answer JSON
- `/search`: return top evidence chunks
- `/health`: status

**Streamlit/Gradio UI**

- Question input
- Answer panel
- Evidence panel (top chunks, highlighted sentences)
- Confidence badge
- Debug toggle (show retrieval scores)

## 7. Tech Stack (Engineer-Friendly)

### 7.1 Core

- Python
- Hugging Face Transformers (tokenization + model inference)
- `FAISS` (dense index)
- BM25 library
- `FastAPI` (service)
- `Streamlit`/`Gradio` (demo)

### 7.2 Ops and Reproducibility

- `requirements.txt` + environment instructions
- Config files (`config.yaml`)
- Logs + experiment tracking (optional: W&B / MLflow)

### 7.3 Hardware Note (Mac M1 Max)

- Use PyTorch `MPS` acceleration when possible, with modest batch sizes.

## 8. Data Plan (Company Docs)

### 8.1 Document Categories (Recommended)

- HR: leave policy, benefits, working hours, OT/comp-off
- Engineering: onboarding, dev workflow, code review, release process
- Security: access policy, credential rotation, incident reporting
- Operations: IT requests, procurement, facilities guidelines

### 8.2 Access and Privacy

Because these are company documents, privacy is explicit in the design:

- All indexing runs locally.
- Store embeddings and chunk text locally.
- Optional access filtering: hide restricted chunks unless role permits.

## 9. Evaluation and Experiments

Evaluation is done at two levels.

### 9.1 Retrieval Metrics

- Recall@k: gold evidence doc appears in top-k.
- MRR: rank quality for correct evidence.
- Evidence Hit Rate: percentage of queries where at least one gold chunk is retrieved.

### 9.2 Answer Quality Metrics

Because internal-doc QA often involves paraphrasing:

- Human evaluation (3 raters if possible, or rotating among teammates):
  - Correctness (1-5)
  - Helpfulness (1-5)
  - Citation correctness (Yes/No)
  - Hallucination (Yes/No)
- Optional automatic checks:
  - Citation coverage ratio (claims supported by citations)

### 9.3 Ablation Study (High Impact)

Run controlled comparisons:

1. BM25 only
2. Dense only
3. Hybrid (BM25 + Dense)
4. Hybrid + rerank (optional)

Report:

- Retrieval metric changes
- Answer correctness changes
- Failure cases

### 9.4 Error Analysis (Required in Report)

At least 15-20 representative failures, categorized by:

- Retrieval miss (wrong doc)
- Chunking issue (answer split across chunks)
- Policy ambiguity
- Outdated-document conflict
- Model overgeneralization (to be reduced by guardrails)

## 10. Work Plan (8 Weeks)

### Week 1: Scope and Setup

- Confirm doc sources + export format
- Define metadata schema + folder structure
- Draft evaluation rubric + test set format

### Week 2: Ingestion and BM25 Baseline

- Parse docs and clean text
- Implement chunking + metadata
- Build BM25 index + `/search` endpoint

### Week 3: Dense Retrieval + FAISS

- Select embedding model
- Build `FAISS` index
- Add hybrid retrieval + retrieval metrics script

### Week 4: End-to-End RAG

- Prompt template + output schema
- Implement `/ask`
- Deliver first working UI demo

### Week 5: Guardrails, No-Answer, Citations

- Add confidence logic
- Implement no-answer fallback
- Add evidence highlighting

### Week 6: Evaluation Set + Experiments

Create approximately 120 QA items:

- question
- gold evidence doc/section
- reference answer

Then run ablations and log results.

### Week 7: Polish and Performance

- Cache embeddings
- Improve chunking and overlap
- Add debug mode + logs

### Week 8: Report, Slides, Demo

- Draft 8-10 page report per course guideline
- Prepare 10-12 slide deck + live demo script

## 11. Team Roles (3 Members)

### Member 1: Data and Retrieval Lead

- Parsing + chunking + metadata
- BM25 + dense + `FAISS`
- Retrieval evaluation (`Recall@k`, `MRR`)

### Member 2: RAG and Guardrails Lead

- Prompt engineering + citation format contract
- Confidence + no-answer policies
- Failure analysis + mitigations

### Member 3: Platform and Demo Lead

- `FastAPI` service + UI
- Integration + logging + reproducibility
- Demo polish + engineer narrative

## 12. Final Deliverables (Submission Package)

1. GitHub repository + runnable instructions.
2. Trained assets (`FAISS` index, BM25 index, configs, prompts).
3. Report (8-10 pages), including:
   - Motivation and related work
   - Methodology (retrieval + RAG + guardrails)
   - Experiments + ablation
   - Results tables + error analysis
   - Conclusion + future work
4. Slides (10-12) + optional live demo video.

## 13. Demo Plan (10 Minutes)

1. Introduce pain point: searching internal docs is slow.
2. Ask 3-4 realistic company questions.
3. Show:
   - Answer + citations
   - Evidence panel
   - Confidence changes when question is vague
4. Ask a tricky question not present in docs and show `NOT_FOUND` behavior.
5. Present ablation slide (`BM25` vs dense vs hybrid).
6. Conclude with privacy and enterprise-safe design.
