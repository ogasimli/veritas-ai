# Roadmap: Veritas AI

## Overview

Build a multi-agent AI co-auditor that processes financial statements (.docx) to detect numeric errors, logical inconsistencies, disclosure compliance gaps, and external risk signals. Start with foundation and document ingestion, then build the agent pipelines (numeric validation as the core), and finish with the frontend dashboard for findings presentation.

## Domain Expertise

None

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Foundation** - Project setup, backend/frontend scaffolding, database schema
- [ ] **Phase 2: Document Ingestion** - Upload API, .docx parsing, structured extraction
- [ ] **Phase 3: Numeric Validation** - Planner + Validator + Manager agents with code_executor
- [ ] **Phase 4: Logic Consistency** - Reasoning agent for semantic inconsistencies
- [ ] **Phase 5: Disclosure Compliance** - Scanner, YAML checklists, parallel validator agents
- [ ] **Phase 6: External Signal** - News/litigation search via google_search tool
- [ ] **Phase 7: Frontend Dashboard** - Findings UI, WebSocket status, drill-down views

## Phase Details

### Phase 1: Foundation
**Goal**: Project scaffolding with Next.js frontend, FastAPI backend, PostgreSQL schema, and GCS integration
**Depends on**: Nothing (first phase)
**Research**: Unlikely (established patterns)
**Plans**: TBD

Plans:
- [x] 01-01: Backend scaffolding (FastAPI, SQLAlchemy, project structure)
- [x] 01-02: Frontend scaffolding (Next.js, Shadcn/UI, TanStack Query)
- [ ] 01-03: Database schema and GCS setup

### Phase 2: Document Ingestion
**Goal**: Upload .docx files, parse with python-docx, extract structured content (tables as markdown)
**Depends on**: Phase 1
**Research**: Likely (document parsing library)
**Research topics**: python-docx table/structure extraction, markdown conversion patterns
**Plans**: TBD

Plans:
- [ ] 02-01: Upload API endpoint with GCS storage
- [ ] 02-02: Extractor agent (.docx → structured markdown)

### Phase 3: Numeric Validation
**Goal**: Core validation pipeline — Planner identifies FSLIs, Validators check math via code_executor, Manager aggregates
**Depends on**: Phase 2
**Research**: Likely (new agent framework)
**Research topics**: Google ADK agent patterns, code_executor tool integration, SequentialAgent/ParallelAgent usage
**Plans**: TBD

Plans:
- [ ] 03-01: Planner agent (identify FSLIs from document)
- [ ] 03-02: Validator agent with code_executor integration
- [ ] 03-03: Manager agent (aggregate, QC, deduplicate)

### Phase 4: Logic Consistency
**Goal**: Agent that detects semantically unreasonable claims even if numerically correct
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Unlikely (reuses ADK patterns, prompt engineering)
**Plans**: TBD

Plans:
- [ ] 04-01: Logic consistency agent with reasoning chains

### Phase 5: Disclosure Compliance
**Goal**: Dynamic IFRS checklist validation — Scanner identifies applicable standards, parallel Validators check each
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Likely (domain knowledge)
**Research topics**: IFRS disclosure requirements for IAS 1, 7, 24, IFRS 7, 15, 16
**Plans**: TBD

Plans:
- [ ] 05-01: Scanner agent + YAML checklist structure
- [ ] 05-02: Compliance validator agents (parallel per standard)

### Phase 6: External Signal
**Goal**: Agent that searches news/litigation for risk signals using Gemini's google_search tool
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Likely (Gemini tool integration)
**Research topics**: Gemini google_search tool API, search grounding patterns
**Plans**: TBD

Plans:
- [ ] 06-01: External signal agent with google_search

### Phase 7: Frontend Dashboard
**Goal**: Findings UI with severity filtering, WebSocket status updates, and drill-down views
**Depends on**: Phase 1 (frontend), Phases 3-6 (agent outputs)
**Research**: Unlikely (standard Next.js + Shadcn patterns)
**Plans**: TBD

Plans:
- [ ] 07-01: Findings list with filtering and sorting
- [ ] 07-02: WebSocket integration for real-time status
- [ ] 07-03: Drill-down view with source citations

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/3 | In Progress | - |
| 2. Document Ingestion | 0/2 | Not started | - |
| 3. Numeric Validation | 0/3 | Not started | - |
| 4. Logic Consistency | 0/1 | Not started | - |
| 5. Disclosure Compliance | 0/2 | Not started | - |
| 6. External Signal | 0/1 | Not started | - |
| 7. Frontend Dashboard | 0/3 | Not started | - |
