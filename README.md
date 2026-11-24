# GitLab Support Automation & Documentation Triage Platform

An enterprise event-driven platform and high-density operational cockpit for automated platform support triage, semantic duplicate detection, and grounded runbook assistance on GitLab issues.

Built with **FastAPI**, **PostgreSQL (`pgvector`)**, **ARQ + Redis**, **React + Vite**, and **Tailwind CSS**.

---

## 🏗️ Architecture Overview

The platform monitors incoming GitLab issues in real time, classifies category/priority/component, performs semantic duplicate matching, and retrieves grounded answers and diagnostic runbooks from internal documentation and academy guides with strict anti-hallucination guardrails.

```mermaid
flowchart TD
    GL[GitLab Issues & Notes] -->|Webhook / Poller| API[FastAPI Ingestion Engine]
    API -->|HMAC Verification & Idempotency| REDIS[(Redis Queue)]
    REDIS -->|Task Dispatch| WORKER[ARQ Background Workers]
    
    subgraph AI & RAG Engine
        WORKER -->|Sanitize & Redact PII| REDACT[PII / Secret Masker]
        REDACT -->|Embed Text| EMB[OpenAI / Gemini Embeddings]
        EMB -->|Hybrid Search| PG[(PostgreSQL + pgvector)]
        PG -->|Top Chunks + Runbooks| RAG[Hybrid RAG & BM25 Retriever]
        RAG -->|Grounded Context| LLM[LLM Triage & Diagnostic Classifier]
    end

    LLM --> DUP[Semantic Duplicate Detector]
    LLM --> RUNBOOK[Safe Diagnostic Generator]
    LLM --> DRIFT[Docs Drift Radar < 0.65 Conf]
    LLM --> DRAFT[AI Draft Response & Proposed Actions]

    subgraph State Machine & Guardrails
        DRAFT --> AE[ActionExecutor State Machine]
        AE -->|Auto-Pilot or Co-Pilot| UI[React + Vite Cockpit :3000]
        UI -->|Approve / Override Diff| AUDIT[(Audit Log & RLHF Golden Store)]
        AUDIT -->|Execute Mutation| GL_API[python-gitlab API Client]
    end

    GL_API -->|Post Note / Apply Labels / Clone Issue| GL
```

---

## ✨ Key Features

### 1. Real-Time GitLab Watcher & Ingestion
- **Secure Webhook Receiver:** Constant-time `X-Gitlab-Token` HMAC verification with replay protection via Redis idempotency keys.
- **Dual Ingestion Mode:** Instant webhook ingestion (`Issue Hook`, `Note Hook`) paired with a periodic reconciliation poller via `python-gitlab`.

### 2. Grounded Hybrid RAG & Knowledge Engine
- **Hybrid Retrieval:** Dense vector embeddings (`pgvector` cosine similarity) combined with sparse keyword search (BM25) against indexed Runbooks, Documentation, and Academy guides.
- **Zero-Hallucination Strict Grounding:** Every claim in draft replies is grounded in an indexed document with exact source links and section headers.
- **Auto-Runbook & Diagnostic Snippet Generator:** Matches incoming error symptoms against known platform runbooks (e.g. Istio 502, Vault PKI expiry, database connection timeouts) and generates safe, read-only diagnostic checklists (`kubectl`, `curl`, config validation).

### 3. Intelligent Triage & Duplicate Detection
- **Multi-Factor Classification:** Determines **Category** (Bug, Feature Request, Configuration/Usage, Access/IAM, Outage), **Severity** (P1 Critical through P4 Low), and **Component/Team**.
- **Cross-Issue Semantic Deduplication:** Vector similarity comparisons across open and closed tickets to flag duplicate threads and prevent redundant engineering triage.
- **SLA Breach Predictor:** Real-time countdown timers tracking issue age against priority targets (P1: 1h, P2: 4h, P3: 24h, P4: 72h) with escalation warnings.

### 4. Human-in-the-Loop & State Machine ActionExecutor
- **Two Execution Modes:**
  - **Co-Pilot (Default):** Generates proposed labels, triage assessments, diagnostic runbooks, and draft replies awaiting support engineer approval in the cockpit.
  - **Auto-Pilot:** Threshold-gated automatic labeling and responses for high-confidence classifications (`confidence >= 0.85`).
- **Action State Machine:** Explicit transitions (`DRAFT` → `APPROVED` → `EXECUTED` / `FAILED`) protecting mutating operations (issue cloning, escalation ticket creation, public comment posting).
- **Interactive Feedback Loop (RLHF Golden Store):** Human edits to draft replies or classification overrides are diffed and saved as golden few-shot examples to continuously refine future prompts.
- **"Docs Drift" Radar:** Clusters low-confidence triage queries (`< 0.65`) into a "Missing Docs" queue with a one-click draft generator to create new documentation or Academy tutorials.

### 5. High-Density Operational Cockpit (UI/UX)
- Dark-mode-first aesthetic inspired by Linear, Sentry, and Datadog.
- **Keyboard-first navigation:**
  - <kbd>J</kbd> / <kbd>K</kbd>: Navigate through issue queue
  - <kbd>A</kbd>: Approve proposed actions & draft response
  - <kbd>C</kbd>: Open Ticket Cloning / Escalation modal
  - <kbd>E</kbd>: Edit draft response
  - <kbd>Esc</kbd>: Close drawers and modals

---

## 🚀 Quickstart with Docker Compose

### Prerequisites
- [Docker Engine](https://docs.docker.com/engine/install/) (>= 24.0) & [Docker Compose](https://docs.docker.com/compose/) (>= 2.20)
- GitLab Personal Access Token (`read_api`, `write_repository`)

### 1. Clone & Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# GitLab Integration
GITLAB_URL=https://gitlab.com
GITLAB_PRIVATE_TOKEN=glpat-your-personal-access-token
GITLAB_WEBHOOK_SECRET=your-secret-webhook-token
GITLAB_BOT_USERNAME=platform-support-bot

# LLM Provider (Google Gemini or OpenAI-compatible endpoint)
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash

# Automation Policies
AUTO_PILOT_CONFIDENCE_THRESHOLD=0.85
DUPLICATE_SIMILARITY_THRESHOLD=0.82
ENABLE_AUTO_EXECUTION=false
```

### 2. Build & Launch Services

```bash
docker compose up --build
```

The stack starts 5 coordinated services:
- **`frontend`** (Nginx + React/Vite SPA): [http://localhost:3000](http://localhost:3000)
- **`backend`** (FastAPI Core & Webhook API): [http://localhost:8000](http://localhost:8000) (Interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs))
- **`worker`** (ARQ Async Task Worker): Asynchronous RAG ingestion, LLM pipelines, and reconciliation polling
- **`postgres`** (PostgreSQL 16 with `pgvector`): `localhost:5432`
- **`redis`** (Redis 7 In-Memory Cache & Queue): `localhost:6379`

---

## 🛠️ Local Development Setup

If running locally without Docker:

### 1. Start Infrastructure (Postgres & Redis)

```bash
docker compose up -d postgres redis
```

### 2. Backend Setup (Python 3.12+)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations / startup tables
export DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/app_db
export REDIS_URL=redis://localhost:6379/0

# Start API server
uvicorn app.main:app --reload --port 8000

# Start background worker (in separate terminal)
arq app.tasks.worker.WorkerSettings
```

### 3. Frontend Setup (React + Vite + pnpm)

```bash
cd frontend
pnpm install
pnpm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Testing & Verification

### Run Backend Unit & Integration Tests

```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

Tests cover:
- Triage assessment creation & schema validation
- Duplicate detection similarity thresholding
- Action state-machine transitions
- Webhook signature HMAC verification

### Run Frontend Build & Type Check

```bash
cd frontend
pnpm run build
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Connection URI for PostgreSQL with `pgvector` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue and cache connection |
| `GITLAB_URL` | `https://gitlab.com` | Base URL of target GitLab instance |
| `GITLAB_PRIVATE_TOKEN` | *None* | Scoped personal/project access token for API calls |
| `GITLAB_WEBHOOK_SECRET` | *None* | Secret token matching `X-Gitlab-Token` header |
| `GITLAB_BOT_USERNAME` | `platform-bot` | Username used to filter bot's own notes |
| `LLM_API_KEY` | *None* | API key for Gemini / OpenAI / vLLM / Ollama |
| `LLM_BASE_URL` | `https://generativelanguage...` | OpenAI-compatible endpoint URL |
| `LLM_MODEL` | `gemini-2.5-flash` | Target model for triage & drafting |
| `AUTO_PILOT_CONFIDENCE_THRESHOLD` | `0.85` | Confidence required for automatic execution |
| `DUPLICATE_SIMILARITY_THRESHOLD` | `0.82` | Cosine similarity threshold for duplicate flagging |
| `ENABLE_AUTO_EXECUTION` | `false` | Global safety switch for automated GitLab mutations |

---

## 🔒 Security & Supply-Chain Hardening

- **Prompt Injection Defense:** Strict separation between system instructions and untrusted GitLab issue bodies; Markdown and input sanitization before LLM context ingestion.
- **Secret & PII Redaction:** Automatic pre-filtering masks access tokens, private keys, JWTs, and passwords before embeddings or external API calls.
- **pnpm Supply-Chain Configuration:** Pinned `pnpm@9` and configured `frontend/pnpm-workspace.yaml` with `minimumReleaseAge: 0` and authorized build dependencies (`esbuild`) for reproducible, airtight container builds.

---

## 📄 License
Internal Production Platform. All rights reserved.
