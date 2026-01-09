# Veritas AI

## What This Is

Multi-agent AI co-auditor that analyzes financial statements (.docx) to detect numeric errors, logical inconsistencies, disclosure compliance gaps, and external risk signals. Built as a product for auditors and accountants who need automated first-pass review of financial reports.

## Core Value

Numeric validation accuracy — if the system can't reliably catch math errors and inconsistencies in financial tables, nothing else matters.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Upload .docx financial statements via drag-and-drop UI
- [ ] Extract and structure document content (tables preserved as markdown)
- [ ] Numeric validation pipeline: Extractor → Planner → Validator → Manager (map-reduce by FSLI)
- [ ] Logic consistency agent: detect semantically unreasonable claims even if numerically correct
- [ ] Disclosure compliance agent: dynamic IFRS checklist validation (scan → filter → validate)
- [ ] External signal agent: news/litigation search via Gemini's google_search tool
- [ ] Coordinator agent: orchestrate pipelines, aggregate findings, deduplicate
- [ ] Findings dashboard: severity filtering, category grouping, source citations
- [ ] Real-time processing status via WebSocket
- [ ] Drill-down view with document references for each finding

### Out of Scope

- User authentication / multi-tenancy — v1 is single-user, auth comes later
- PDF support — requires different parsing strategy, defer to v2
- Excel support — defer to v2
- Mobile-responsive UI — desktop-first for v1
- Full IFRS standard coverage — start with core standards (IAS 1, 7, 24, IFRS 7, 15, 16)

## Context

**Tech Stack (decided)**:
- Frontend: Next.js 14 (App Router) + Shadcn/UI + TanStack Query
- Backend: FastAPI + async SQLAlchemy + asyncpg
- Agents: Google ADK (SequentialAgent, ParallelAgent patterns)
- LLM: Gemini 3 Pro with built-in tools (code_executor, google_search)
- Cloud: GCP (Cloud Run, Cloud Storage, PostgreSQL via Cloud SQL)
- Document parsing: python-docx

**Architecture**:
- Coordinator orchestrates 4 parallel agent pipelines
- Numeric Validation: sequential (Extractor → Planner → Validator → Manager)
- Logic Consistency: single agent with reasoning chain
- Disclosure Compliance: dynamic (Scanner → Filter → parallel Validators per standard)
- External Signal: single agent with google_search tool
- WebSocket for real-time status updates from agents to frontend

**Key patterns**:
- Map-reduce for numeric validation (parallelize by Financial Statement Line Item)
- YAML-based IFRS checklists loaded dynamically based on document scan
- code_executor for deterministic math verification
- Reasoning trails on all findings for audit traceability

## Constraints

- **Cloud**: GCP only — all infrastructure must be Google Cloud services
- **Timeline**: 1-2 weeks for working prototype — aggressive, scope accordingly
- **Input format**: .docx only — no PDF/Excel parsing in v1
- **LLM**: Gemini 3 Pro — use built-in tools, no external API integrations

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Shadcn/UI for frontend | Accessible (Radix), own the code, rapid dashboard building | — Pending |
| Google ADK for orchestration | Native Gemini integration, built-in agent patterns | — Pending |
| Map-reduce for numeric validation | Reduces context noise, isolates hallucinations, enables parallelism | — Pending |
| Dynamic IFRS checklist loading | Avoids 50+ irrelevant standard checks per document | — Pending |
| WebSocket for status updates | Real-time progress feedback essential for long-running agent pipelines | — Pending |

---
*Last updated: 2026-01-09 after initialization*
