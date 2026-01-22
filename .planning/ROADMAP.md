# Roadmap: Veritas AI

## Overview

Build a multi-agent AI co-auditor that processes financial statements (.docx) to detect numeric errors, logical inconsistencies, disclosure compliance gaps, and external risk signals. Start with foundation and document ingestion, then build the agent pipelines (numeric validation as the core), and finish with the frontend dashboard for findings presentation.

## Domain Expertise

None

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Project setup, backend/frontend scaffolding, database schema
- [x] **Phase 2: Document Ingestion** - Upload API, .docx parsing, structured extraction
- [x] **Phase 3: Numeric Validation** (Completed) - Planner + Validator + Manager agents with code_executor
- [x] **Phase 3.1: Root Orchestrator Agent** (Completed) - Coordinate all validation agents in parallel
- [x] **Phase 4: Logic Consistency** (Completed) - Reasoning agent for semantic inconsistencies
- [x] **Phase 4.1: Logic Reviewer** (Completed) - False-positive filtering + business-impact severity for logic findings
- [x] **Phase 5: Disclosure Compliance** (Completed) - Scanner, YAML checklists, parallel validator agents
- [x] **Phase 5.1: Disclosure Reviewer** (Completed) - False-positive filtering for semantic mismatches, combined disclosures, cross-references
- [x] **Phase 6: External Signal** (Completed) - News/litigation search via google_search tool
- [x] **Phase 6.1: Bidirectional Verification + Deep Research** (INSERTED, Completed) - ParallelAgent with 2 sub-agents for report→internet + internet→report verification using Deep Research
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
- [x] 01-03: Database schema and GCS setup

### Phase 2: Document Ingestion
**Goal**: Upload .docx files, parse with python-docx, extract structured content (tables as markdown)
**Depends on**: Phase 1
**Research**: Likely (document parsing library)
**Research topics**: python-docx table/structure extraction, markdown conversion patterns
**Plans**: TBD

Plans:
- [x] 02-01: Upload API endpoint with GCS storage
- [x] 02-02: Extractor agent (.docx → structured markdown)

### Phase 3: Numeric Validation
**Goal**: Core validation pipeline — Planner identifies FSLIs, Validators check math via code_executor, Manager aggregates
**Depends on**: Phase 2
**Research**: Likely (new agent framework)
**Research topics**: Google ADK agent patterns, code_executor tool integration, SequentialAgent/ParallelAgent usage
**Plans**: TBD

Plans:
- [x] 03-01: Planner agent (identify FSLIs from document)
- [x] 03-02: Validator agent with code_executor integration
- [x] 03-03: Manager agent (aggregate, QC, deduplicate)

### Phase 3.1: Root Orchestrator Agent (INSERTED)
**Goal**: Root orchestrator agent to coordinate all validation agents (Numeric, Logic, Disclosure, External) in parallel
**Depends on**: Phase 3
**Research**: Unlikely (reuses ADK ParallelAgent patterns)
**Plans**: 1/1 complete

Plans:
- [x] 3.1-01: Create root orchestrator agent with ParallelAgent pattern

### Phase 4: Logic Consistency
**Goal**: Agent that detects semantically unreasonable claims even if numerically correct
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Unlikely (reuses ADK patterns, prompt engineering)
**Plans**: 1/1 complete

Plans:
- [x] 04-01: Logic consistency agent with reasoning chains

### Phase 4.1: Logic Reviewer (INSERTED)
**Goal**: Refactor logic_consistency to 2-stage SequentialAgent (Detector→Reviewer) for false-positive filtering and business-impact severity
**Depends on**: Phase 4 (existing logic agent), Phase 3 (SequentialAgent patterns)
**Research**: Unlikely (reuses ADK patterns)
**Plans**: 1/1 complete

Plans:
- [x] 4.1-01: Refactor to Detector + Reviewer sub-agents with filtering + severity logic

### Phase 5: Disclosure Compliance
**Goal**: Dynamic IFRS checklist validation — Scanner identifies applicable standards, parallel Validators check each
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Completed (IFRS checklist extracted from Excel)
**Plans**: 1/1 complete

Plans:
- [x] 05-01: Scanner agent + YAML checklist structure + FanOutVerifier integration

### Phase 5.1: Disclosure Reviewer (INSERTED)
**Goal**: Refactor disclosure_compliance to 3-stage SequentialAgent (Scanner→FanOutVerifier→Reviewer) for false-positive filtering
**Depends on**: Phase 5 (existing disclosure agent), Phase 3 (Reviewer patterns from numeric_validation)
**Research**: Unlikely (reuses Reviewer pattern)
**Plans**: 1/1 complete

Plans:
- [x] 5.1-01: Create Reviewer sub-agent with false-positive filtering for semantic equivalence, combined disclosures, cross-references

### Phase 6: External Signal
**Goal**: Agent that searches news/litigation for risk signals using Gemini's google_search tool
**Depends on**: Phase 3 (reuses ADK patterns)
**Research**: Completed (google_search tool API, grounding patterns)
**Plans**: 1/1 complete

Plans:
- [x] 06-01: External signal agent with google_search

### Phase 6.1: Bidirectional Verification + Deep Research (INSERTED)
**Goal**: Enhance external signal agent with bidirectional verification (internet→report AND report→internet) using ParallelAgent with 2 sub-agents and Deep Research integration
**Depends on**: Phase 6 (existing external signal agent)
**Research**: Completed (Deep Research API patterns, long-running task handling)
**Research topics**: Gemini Deep Research Agent API, async task management, ParallelAgent with Deep Research sub-agents
**Plans**: 2/2 complete

Plans:
- [x] 6.1-01: Deep Research infrastructure (DeepResearchClient + bidirectional sub-agents)
- [x] 6.1-02: Integration and backend updates (ParallelAgent orchestrator + processor + root agent)

**Details:**
Current limitation: Phase 6 only checks internet→report (external info contradicting report statements).

Enhancement needed:
1. **Report→Internet verification**: Extract publicly verifiable claims from report (dates, locations, partnerships, regulatory filings, awards, certifications) and verify via internet search
2. **Bidirectional architecture**: ParallelAgent with 2 sub-agents:
   - Sub-agent 1: Internet→Report (existing pattern)
   - Sub-agent 2: Report→Internet (new pattern)
3. **Deep Research integration**: Replace gemini-2.0-flash-exp with Deep Research for both sub-agents to handle complex verification queries
4. **Long-running task handling**: Implement async task management per Deep Research documentation

Reference: https://ai.google.dev/gemini-api/docs/deep-research#long-running-tasks

### Phase 7: Frontend Dashboard
**Goal**: Real-time dashboard with WebSocket integration, file upload, and findings display
**Depends on**: Phase 1 (frontend), Phases 3-6 (agent outputs)
**Research**: Unlikely (standard Next.js + Shadcn patterns)
**Plans**: 4/4 complete

Plans:
- [x] 07-01: Dark mode + Layout shell + Audit list
- [x] 07-02: File upload with validation
- [x] 07-03: WebSocket integration + Live agent cards
- [x] 07-04: Export functionality + Final polish

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Completed | 2026-01-09 |
| 2. Document Ingestion | 2/2 | Completed | 2026-01-10 |
| 3. Numeric Validation | 3/3 | Completed | 2026-01-13 |
| 3.1. Root Orchestrator Agent | 1/1 | Completed | 2026-01-18 |
| 4. Logic Consistency | 1/1 | Completed | 2026-01-18 |
| 4.1. Logic Reviewer | 1/1 | Completed | 2026-01-19 |
| 5. Disclosure Compliance | 1/1 | Completed | 2026-01-19 |
| 5.1. Disclosure Reviewer | 1/1 | Completed | 2026-01-19 |
| 6. External Signal | 1/1 | Completed | 2026-01-19 |
| 6.1. Bidirectional Verification + Deep Research | 2/2 | Completed | 2026-01-21 |
| 7. Frontend Dashboard | 4/4 | Completed | 2026-01-21 |
