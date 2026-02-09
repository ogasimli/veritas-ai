# Veritas AI Backend

**FastAPI-based backend for the Veritas AI co-auditor platform** — A multi-agent system that automates financial statement validation and audit workflows using Google ADK and Gemini models.

---

## 📖 Overview

The Veritas AI backend provides a robust REST API for uploading, processing, and validating financial reports through an intelligent multi-agent pipeline. The system combines:

- **Document Management**: Upload and storage of financial reports (DOCX supported, PDF coming soon)
- **Multi-Agent Validation**: Orchestrated validation across numeric, logic, compliance, and external signal domains
- **Real-Time Progress Tracking**: WebSocket-based live updates during long-running audit jobs
- **Persistent Storage**: PostgreSQL database for audit history and Google Cloud Storage for documents

---

## 🏗️ Architecture

```mermaid
graph TD
    Client[Client Application] -->|REST API| FastAPI[FastAPI Backend]
    Client -->|WebSocket| FastAPI

    FastAPI --> API[API Layer]
    API --> Services[Service Layer]

    Services --> Storage[GCS Storage Service]
    Services --> Processor[Agent Processor]
    Services --> Extractor[DOCX Extractor]
    Services --> WS[WebSocket Manager]

    Processor --> Validator[Document Validator]
    
    subgraph "Multi-Agent System"
        Validator --> Orchestrator[Audit Orchestrator]
        Orchestrator -->|Parallel| Numeric[Numeric Validation]
        Orchestrator -->|Parallel| Logic[Logic Consistency]
        Orchestrator -->|Parallel| Compliance[Disclosure Compliance]
        Orchestrator -->|Parallel| External[External Signals]
    end

    Services --> DB[(PostgreSQL)]
    Storage --> GCS[(Google Cloud Storage)]

    DB --> Models[SQLAlchemy Models]
    Models --> Documents[Documents]
    Models --> Jobs[Jobs]
    Models --> Findings[Findings]
```

### Key Components

| Component | Description |
|-----------|-------------|
| **API Layer** | FastAPI routes for documents, jobs, health checks, and WebSockets |
| **Service Layer** | Business logic for document processing, storage, and agent orchestration |
| **Multi-Agent System** | Autonomous validation pipeline with parallel expert agents (see [agents/README.md](./agents/README.md)) |
| **Database** | PostgreSQL with async SQLAlchemy for storing audit results and metadata |
| **Storage** | Google Cloud Storage for document persistence |
| **WebSocket Manager** | Real-time progress streaming during audit execution |

---

## 🛠️ Tech Stack

### Core Framework
- **[FastAPI](https://fastapi.tiangolo.com/)** — Modern async web framework with automatic OpenAPI docs
- **[Uvicorn](https://www.uvicorn.org/)** — ASGI server with hot-reload support

### Database & ORM
- **[PostgreSQL 15](https://www.postgresql.org/)** — Production-grade relational database
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** — Async ORM with type safety
- **[asyncpg](https://github.com/MagicStack/asyncpg)** — High-performance async PostgreSQL driver
- **[Alembic](https://alembic.sqlalchemy.org/)** — Database migration management

### AI & Agents
- **[Google ADK](https://github.com/google/adk)** — Agent Development Kit for building multi-agent systems
- **[Google Gemini](https://ai.google.dev/)** — Gemini 3 Pro/Flash and Deep Research models

### Cloud & Storage
- **[Google Cloud Storage](https://cloud.google.com/storage)** — Object storage for financial documents
- **[Docker](https://www.docker.com/)** — Containerization for consistent deployment

### Developer Tools
- **[uv](https://astral.sh/uv/)** — Ultra-fast Python package manager
- **[Ruff](https://github.com/astral-sh/ruff)** — Blazing-fast linter and formatter
- **[pytest](https://pytest.org/)** — Testing framework with async support
- **[pre-commit](https://pre-commit.com/)** — Git hooks for code quality

---

## 🤖 Multi-Agent Validation Pipeline

The core intelligence of Veritas AI lives in the **agents/** directory. The multi-agent system orchestrates four parallel validation pipelines:

1. **Numeric Validation** — Math-based verification of financial calculations
2. **Logic Consistency** — Semantic contradiction detection
3. **Disclosure Compliance** — IFRS/IAS standard adherence checks
4. **External Signals** — Web research for claim verification

**For detailed architecture, agent workflows, and implementation patterns, see:**

📖 **[agents/README.md](./agents/README.md)**

---

## 📥 Installation

### Prerequisites

- **Python 3.11+**
- **[uv](https://astral.sh/uv/)** — Fast Python package manager
- **Docker** — For local PostgreSQL database
- **Google Cloud credentials** (optional, for GCS integration)

### 1. Install Dependencies

```bash
cd backend
make install
```

This installs all Python dependencies using `uv`, including the local `agents` package in editable mode.

### 2. Environment Setup

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database connection (local Docker database by default)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/veritas

# Google Cloud Storage bucket name (leave empty for local storage)
GCS_BUCKET=

# Debug mode (true/false)
DEBUG=true

# Dummy agent mode for frontend testing without hitting MAS (true/false)
USE_DUMMY_AGENTS=false

# Agent configuration
GOOGLE_GENAI_USE_VERTEXAI=FALSE
VERITAS_AGENT_MODE=orchestrator
NUMERIC_VALIDATION_AGENT_MODE=all
GEMINI_PRO_MODEL=gemini-3-flash-preview
GEMINI_FLASH_MODEL=gemini-3-flash-preview
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Start Local Database

```bash
docker compose up -d db
```

This starts a PostgreSQL 15 database container on port 5432.

### 4. Run Database Migrations

```bash
uv run alembic upgrade head
```

Applies all pending migrations to set up the database schema.

---

## 💻 Development

### Start the Development Server

```bash
make dev
```

This will:
1. Start the PostgreSQL database (if not running)
2. Apply migrations
3. Launch the FastAPI server with hot-reload on `http://localhost:8000`

### API Documentation

Once running, access:
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc

### Stop the Database

```bash
make db-stop
```

---

## 🚀 API Endpoints

### Health & Status
- `GET /api/health` — Health check endpoint

### Documents
- `POST /api/v1/documents/upload` — Upload a financial report (DOCX) and start audit job

### Jobs
- `GET /api/v1/jobs/` — List all audit jobs
- `GET /api/v1/jobs/{job_id}` — Get job status and metadata
- `GET /api/v1/jobs/{job_id}/results` — Get all agent results for a job
- `GET /api/v1/jobs/{job_id}/results/agent/{agent_id}` — Get results for specific agent
- `GET /api/v1/jobs/{job_id}/debug` — Download ADK debug YAML file (for troubleshooting)
- `PATCH /api/v1/jobs/{job_id}` — Update job metadata
- `DELETE /api/v1/jobs/{job_id}` — Delete a job

### WebSockets
- `WS /ws/jobs/{job_id}` — Real-time progress updates during audit execution

---

## 🗄️ Database Management

### Create a New Migration

After modifying SQLAlchemy models, generate a migration:

```bash
make migrate msg="add new field to findings table"
```

### Manual Migration Commands

```bash
# View current migration status
uv run alembic current

# Upgrade to latest version
uv run alembic upgrade head

# Downgrade one version
uv run alembic downgrade -1
```

---

## 🧪 Testing

### Run All Tests

```bash
make test
```

This runs both backend API/service tests and agent pipeline tests.

### Run Only Backend Tests

```bash
uv run pytest tests/
```

### Run with Coverage

```bash
uv run pytest tests/ --cov=app --cov-report=html
```

---

## ✨ Code Quality

### Linting & Formatting

```bash
make lint
```

This runs:
- **codespell** — Spell checking
- **ruff check** — Linting with auto-fix
- **ruff format** — Code formatting

### Pre-Commit Hooks

Install pre-commit hooks to run checks automatically:

```bash
uv run pre-commit install
```

---

## 🚢 Deployment

### Deploy to Google Cloud Run

```bash
make deploy
```

This executes `scripts/deploy_infra.sh`, which:
1. Enables required GCP APIs (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Storage)
2. Creates a GCS bucket for document storage
3. Provisions a Cloud SQL PostgreSQL 15 instance (or reuses existing)
4. Creates the database and application user
5. Stores secrets (DB password, DB URL, Gemini API key) in Secret Manager
6. Builds the Docker image via Cloud Build and pushes to Artifact Registry
7. Deploys to Cloud Run with secrets and environment variables injected

The deploy script reads agent configuration from `backend/.env` — including `GEMINI_API_KEY`, model names, and agent mode settings. Sensitive values are stored in Secret Manager; non-sensitive config is set as Cloud Run env vars.

### Environment Variables (Production)

These are automatically configured by `deploy_infra.sh`:

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | Secret Manager | Cloud SQL connection string |
| `GEMINI_API_KEY` | Secret Manager | Gemini API key for agent pipeline |
| `GCS_BUCKET` | Env var | GCS bucket for document storage |
| `DEBUG` | Env var | Set to `false` in production |
| `GOOGLE_GENAI_USE_VERTEXAI` | Env var | Vertex AI routing toggle |
| `VERITAS_AGENT_MODE` | Env var | Agent mode (orchestrator, numeric_validation, etc.) |
| `NUMERIC_VALIDATION_AGENT_MODE` | Env var | Numeric pipeline mode (all, in_table_pipeline, cross_table_pipeline) |
| `GEMINI_PRO_MODEL` | Env var | Gemini Pro model override (if set in .env) |
| `GEMINI_FLASH_MODEL` | Env var | Gemini Flash model override (if set in .env) |
| `ALLOWED_ORIGINS` | Env var | CORS allowed origins (update after frontend deploy) |

