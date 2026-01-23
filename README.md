<div align="center">
  <img src="frontend/public/logo-readme.png" alt="Veritas AI Logo">
</div>

<h1 align="center">Veritas AI</h1>

<p align="center">
  <strong>Multi-Agent AI Co-Auditor for Financial Statement Validation</strong>
</p>

<p align="center">
  Automatically detects cross-document inconsistencies in financial statements, eliminating human error in high-stakes financial reporting.
</p>

---

## 🎯 Overview

Veritas AI is a multi-agent artificial intelligence co-auditor that performs automated validation of financial statements. It addresses the critical pain points faced by auditors:

- **Manual cross-referencing** across 100+ page financial documents
- **Reconciling footnotes** to primary statements
- **Checking logical consistency** across periods, disclosures, and discussions
- **IFRS/IAS compliance verification** for minimum disclosure requirements

> **Design Principle**: Deterministic tools own the **numbers**, LLM owns the **meaning**.

## 🏗️ Architecture

The system uses a **multi-agent orchestration pattern** built on Google's Agent Development Kit (ADK):

```
                         ┌──────────────────────────────────┐
                         │      Audit Orchestrator          │
                         │       (ParallelAgent)            │
                         └───────────────┬──────────────────┘
                                         │
         ┌───────────────┬───────────────┬───────────────┬───────────────┐
         ▼               ▼               ▼               ▼               
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Numeric       │ │     Logic       │ │   Disclosure    │ │    External     │
│   Validation    │ │   Consistency   │ │   Compliance    │ │     Signal      │
│   Agent         │ │   Agent         │ │   Agent         │ │     Agent       │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Agent Responsibilities

| Agent | Purpose | Implementation |
|-------|---------|----------------|
| **Numeric Validation** | Verifies mathematical accuracy (footings, cross-ties) | Deterministic Python + adaptive batching |
| **Logic Consistency** | Detects logical inconsistencies across statements | Gemini Pro reasoning |
| **Disclosure Compliance** | Checks IFRS/IAS minimum disclosure requirements | Rule-based + LLM verification |
| **External Signal** | Cross-references with external public information | Deep Research integration |

## 🛠️ Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| **Agent Framework** | [Google ADK](https://github.com/google/adk-python) (Agent Development Kit) |
| **LLM** | Gemini 2.0 Flash |
| **API Framework** | FastAPI |
| **Package Manager** | [uv](https://astral.sh/uv) |
| **Database** | PostgreSQL (SQLAlchemy + asyncpg) |
| **Migrations** | Alembic |
| **Language** | Python 3.10+ |

### Frontend
| Component | Technology |
|-----------|------------|
| **Framework** | Next.js 16 (App Router) |
| **Styling** | Tailwind CSS 4 |
| **State Management** | TanStack Query |
| **UI Components** | Radix UI + shadcn/ui |
| **Language** | TypeScript 5 |

## 📁 Directory Structure

```
veritas-ai/
├── .agent/             # AI assistant rules and workflows
├── .docs/              # Product documentation (PRD, etc.)
├── backend/            # Python backend
│   ├── agents/         # ADK agent definitions
│   │   ├── veritas_ai_agent/   # Main production agent
│   │   │   ├── agent.py        # Root orchestrator (ParallelAgent)
│   │   │   ├── sub_agents/     # Specialized validation agents
│   │   │   │   ├── numeric_validation/
│   │   │   │   ├── logic_consistency/
│   │   │   │   ├── disclosure_compliance/
│   │   │   │   └── external_signal/
│   │   │   ├── app_utils/      # Shared utilities
│   │   │   └── data/           # IFRS/IAS checklists
│   ├── app/            # FastAPI application
│   │   ├── api/        # REST API endpoints
│   │   ├── models/     # SQLAlchemy models
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic
│   ├── alembic/        # Database migrations
│   ├── scripts/        # Utility scripts
│   └── tests/          # pytest test suite
├── frontend/           # Next.js frontend
│   ├── app/            # App Router pages
│   ├── components/     # React components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions
│   └── public/         # Static assets
└── Makefile            # Root project commands
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** 
- **uv** (Python package manager) — auto-installed by Makefile
- **Google Cloud credentials** (for Gemini API access)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/veritas-ai.git
cd veritas-ai

# Install all dependencies (backend + frontend)
make install
```

### Environment Setup

1. **Backend environment** — Copy and configure:
   ```bash
   cp backend/.env.example backend/.env
   cp backend/agents/.env.example backend/agents/.env
   ```

2. **Required environment variables**:
   ```env
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_API_KEY=your-gemini-api-key
   DATABASE_URL=postgresql://user:pass@localhost:5432/veritas
   ```

## 💻 Development

### Run Both Servers (Recommended)

```bash
# Starts backend (port 8000) and frontend (port 3000) concurrently
make dev
```

### Run Individually

```bash
# Backend only
cd backend && make dev

# Frontend only
cd frontend && npm run dev
```

### ADK Agent Playground

The ADK web playground provides an interactive UI for testing agents:

```bash
cd backend/agents
make playground
# Opens at http://localhost:8501
```

## 🧪 Testing

```bash
# Run all tests
make test

# Backend tests only
cd backend && make test

# Agent-specific tests
cd backend/agents && make test
```

## 🔍 Code Quality

```bash
# Lint everything
make lint

# Backend linting (ruff + codespell)
cd backend && make lint

# Frontend linting (ESLint)
cd frontend && npm run lint
```

## 🚢 Deployment

### Deploy Agent to Cloud Run

```bash
# Deploy the ADK agent to Google Cloud Run
cd backend/agents
make deploy
```

This deploys the `veritas_ai_agent` with:
- Google Cloud Run hosting
- Built-in ADK web UI
- Auto-scaling based on demand

## 📚 Key Commands Reference

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run backend + frontend dev servers |
| `make test` | Run all tests |
| `make lint` | Lint backend + frontend |
| `make deploy` | Deploy backend to Cloud Run |
| `cd backend/agents && make playground` | Launch ADK agent playground |

## 📄 Documentation

- [Product Requirements Document](.docs/veritas_ai_prd.md) — Full PRD with feature scope
- [Backend README](backend/README.md) — Backend-specific documentation
- [Frontend README](frontend/README.md) — Frontend-specific documentation

---

<p align="center">
  <sub>Built with ❤️ using Google ADK, Gemini, Next.js, and FastAPI</sub>
</p>
