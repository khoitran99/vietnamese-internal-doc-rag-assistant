# Beginner Project Diagrams

This guide explains how the project works end to end for a first-time contributor.

Project: `Vietnamese Internal Docs RAG Assistant`  
Core idea: the system answers only from indexed internal documents, with citations.

## 1) Big Picture

```mermaid
flowchart LR
    A[data/raw documents] --> B[Ingestion and chunking]
    B --> C[data/processed/chunks.jsonl]
    C --> D1[BM25 index]
    C --> D2[Dense index]
    D1 --> E[Hybrid retrieval]
    D2 --> E
    E --> F[RAG answer generation]
    F --> G[Guardrails]
    G --> H[FastAPI /ask and /search]
    H --> I[Client: Postman, curl, Streamlit]
```

What this means:
- Build-time path: `data/raw -> chunks -> indices`
- Runtime path: `question -> retrieve -> answer -> guardrails -> API response`

## 2) Repository Map (What Each Folder Does)

```mermaid
flowchart TD
    ROOT[final-project] --> CFG[config]
    ROOT --> RAW[data/raw]
    ROOT --> PROC[data/processed]
    ROOT --> IDX[data/indices]
    ROOT --> SRC[src]
    ROOT --> SCRIPTS[scripts]
    ROOT --> TESTS[tests]

    SRC --> ING[src/ingestion]
    SRC --> CHK[src/indexing]
    SRC --> RET[src/retrieval]
    SRC --> RAG[src/rag]
    SRC --> GR[src/guardrails]
    SRC --> API[src/api]
    SRC --> EVAL[src/eval]
    SRC --> UI[src/ui]
```

## 3) Build-Time Pipeline (How Knowledge Is Prepared)

### 3.1 Entry Script

```mermaid
flowchart LR
    A[scripts/ingest_and_index.py] --> B[load_settings]
    B --> C[ensure_directories]
    C --> D[ingest_and_chunk]
    D --> E[build_all_indices]
```

### 3.2 Ingestion and Chunking

```mermaid
flowchart TD
    A[data/raw/*] --> B[Parse by file type<br/>PDF DOCX MD TXT HTML]
    B --> C[normalize_text]
    C --> D[infer metadata<br/>department access_level updated_at]
    D --> E[extract section blocks from headings]
    E --> F[sliding token windows with overlap]
    F --> G[DocumentChunk list]
    G --> H[data/processed/chunks.jsonl]
```

Important outputs per chunk:
- `doc_id`
- `chunk_id`
- `text`
- `title`
- `section_path`
- `department`
- `updated_at`
- `access_level`

### 3.3 Index Building

```mermaid
flowchart LR
    A[chunks.jsonl] --> B[BM25 build]
    A --> C[Dense embedding build]
    B --> D[data/indices/bm25.pkl]
    C --> E[data/indices/dense/embeddings.npy]
    C --> F[data/indices/dense/chunks.jsonl]
    C --> G[data/indices/dense/meta.json]
```

## 4) Runtime Query Flow (`POST /ask`)

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI /ask
    participant RET as RetrievalService
    participant RAG as RAGAnswerer
    participant GR as Guardrails

    U->>API: question, top_k, access_level
    API->>RET: retrieve(question)
    RET-->>API: ranked evidence hits
    API->>RAG: question + evidence
    RAG->>GR: confidence and safety checks
    alt pass
        GR-->>API: ANSWERED + citations
    else fail
        GR-->>API: NOT_FOUND + clarifying_question
    end
    API-->>U: JSON response
```

## 5) Retrieval Internals

```mermaid
flowchart TD
    Q[Query] --> B[BM25 retrieval]
    Q --> D[Dense retrieval]
    B --> F[Fusion]
    D --> F
    F --> M[Metadata boost]
    M --> R[Recency boost]
    R --> T[Threshold filter]
    T --> K[Final top_k evidence]
```

Notes:
- BM25 is lexical (keyword-based).
- Dense is semantic (embedding similarity).
- Hybrid is usually stronger than either one alone.

## 6) Guardrail Decision Logic (Simplified)

```mermaid
flowchart TD
    A[Retrieved hits + citations] --> B{Any hits?}
    B -- No --> NF[NOT_FOUND]
    B -- Yes --> C[Check score and citation coverage]
    C --> D[Check relevance]
    D --> E[Check numbers and acronyms support]
    E --> F[Check token coverage consistency]
    F --> G{All checks pass?}
    G -- Yes --> ANS[ANSWERED]
    G -- No --> NF
```

## 7) Why `top_k` Matters

```mermaid
flowchart LR
    A[top_k from request] --> B[retrieval keeps up to top_k final hits]
    B --> C[answerer uses selected hits]
    C --> D[citations limited by max_citations]
```

Key distinction:
- `top_k`: number of final retrieval hits considered.
- `max_citations`: maximum citations shown in answer.

## 8) Evaluation and Tuning Loop

```mermaid
flowchart LR
    A[data/eval datasets] --> B[scripts/run_eval.py]
    A --> C[scripts/holdout_error_report.py]
    B --> D[Recall MRR HitRate]
    B --> E[No-answer metrics]
    C --> F[Failure buckets]
    D --> G[Tuning decisions]
    E --> G
    F --> G
    G --> H[Update config and logic]
    H --> A
```

## 9) First-Day Runbook (Beginner)

1. Install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Build chunks and indices:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/ingest_and_index.py --config config/default.yaml
```

3. Start API:
```bash
PYTHONPATH=. DISABLE_EXTERNAL_MODELS=1 python3 scripts/run_api.py --config config/default.yaml
```

4. Smoke check:
```bash
curl -s http://127.0.0.1:8000/health
```

5. Ask one question:
```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Cho tôi biết về đặt tên nhánh","top_k":5,"access_level":"public"}'
```

## 10) Debug Checklist for New Contributors

- If answer is `NOT_FOUND` unexpectedly:
  - Retry with `"debug": true`.
  - Check top retrieved `chunk_id` in debug output.
  - Check whether citation coverage or relevance thresholds rejected it.
- If retrieval is poor:
  - Rebuild corpus and indices.
  - Inspect chunk quality in `data/processed/chunks.jsonl`.
  - Compare BM25 vs dense top hits in `/search?debug=true`.
- If API fails:
  - Confirm indices exist in `data/indices/`.
  - Confirm config path and env vars are correct.

