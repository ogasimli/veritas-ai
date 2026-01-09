# Veritas AI — Product Requirements Document (PRD)

## 1. Product Overview

### 1.1 One-Liner
**Veritas AI** is a multi-agent artificial intelligence (AI) co-auditor that automatically detects cross-document inconsistencies in financial statements, eliminating human error in high-stakes financial reporting.

---

## 2. Problem Statement

Auditors and controllers spend a disproportionate amount of time on:
- Manual cross-referencing across 100+ page financial statements
- Reconciling footnotes to primary statements
- Checking logical consistency across periods, disclosures, and discussions
- Translating meeting knowledge into formal disclosures

This work is:
- High risk (minor errors can trigger regulatory findings)
- Low creativity
- Poorly scalable
- Still largely manual despite advances in analytics

---

## 3. Target Users & Personas

### 3.1 Primary Users
- Audit Partners and Managers (Big 4 and Mid-tier firms)
- Internal Controllers and Heads of Financial Reporting
- Technical Accounting and IFRS Specialists

### 3.2 User Context
- Late-stage audit review and sign-off
- High pressure timelines
- Low tolerance for false positives
- Strong preference for explainability and traceability

---

## 4. Core Job-to-Be-Done

> “Before I sign off, I want to be absolutely certain that everything says the same thing everywhere — numerically and logically — without manually re-checking hundreds of pages.”

---

## 5. Inputs → Outputs

### 5.1 Inputs

> **MVP Input Strategy**: Word documents (.docx) are prioritized for highest accuracy in table extraction. PDF and Excel support planned for post-MVP.

| Document Type | MVP Format | Rationale |
|--------------|-----------|-----------|
| Financial statements (current year) | **.docx** (preferred) | Native table structure, 100% parsing accuracy |
| Financial statements (prior year) | **.docx** (preferred) | Same as above |
| Audit working papers | **.xlsx** (Phase 2) | Native spreadsheet format |
| Meeting minutes / internal notes | **.docx** or **.txt** | Semantic text extraction |

> **Why .docx over PDF?** Word documents contain explicit XML structure for tables, headings, and formatting. PDF tables must be inferred from text positioning, leading to potential extraction errors in complex financial tables.

### 5.2 Outputs
A structured **Reviewer Findings Report** containing:
- Flagged inconsistency
- Category (mathematical, logical, disclosure, external)
- Severity (high / medium / low)
- Exact document references (page, table, paragraph)
- Short reasoning trail explaining why the issue was flagged

---

## 6. Functional Scope

### 6.1 Must-Have Features (MVP)

#### A. Internal Consistency Checks

**A1. Low-Level (Deterministic Checks)**
- Table footings (rows and columns)
- Cross-statement ties:
  - Balance sheet to notes
  - Cash flow opening and closing balances to balance sheet
- Numerical equality with configurable tolerances

> Implemented using a Python-based numeric engine rather than probabilistic language models.

---

**A2. High-Level (Logical Consistency Checks)**
Examples include:
- Cash outflows inconsistent with reported asset additions
- Significant profit or margin volatility without narrative explanation
- Large related-party balances with insufficient disclosure depth

> Implemented using Gemini 3 Pro reasoning agents operating on structured summaries.

---

#### B. External Consistency Checks
- Scan external news and public information for:
  - Financial distress indicators
  - Litigation or regulatory actions
  - Restructuring or going-concern signals
- Flag absence of corresponding disclosures

> MVP scope limited to headline-level contradiction detection.

---

#### C. Internal Knowledge Consistency
- Compare meeting minutes and internal discussions to final disclosures
- Example:
  - Going-concern risks discussed internally but not disclosed in the financial statements

---

#### D. IFRS Minimum Disclosure Compliance
- Rule-based checklist validation for selected standards (MVP):
  - IAS 1 — Presentation of Financial Statements
  - IFRS 7 — Financial Instruments: Disclosures
  - IAS 24 — Related Party Disclosures

---

### 6.2 Nice-to-Have Features (Post-MVP)
- Prior-year inconsistency and drift detection
- Reconciliation of working paper conclusions to financial statements
- Suggested wording for missing or weak disclosures
- Confidence scores by section and by finding

---

## 7. System Architecture (Conceptual)

### 7.1 Agent Roles

1. **Document Parser Agent**
   - Extracts tables, sections, references, and semantic structure

2. **Numeric Validator Agent**
   - Performs deterministic arithmetic and cross-footing checks

3. **Logic Consistency Agent**
   - Evaluates logical coherence across statements and disclosures

4. **Disclosure Compliance Agent**
   - Checks IFRS minimum disclosure requirements

5. **External Signal Agent**
   - Identifies contradictions with external public information

6. **Coordinator Agent**
   - Aggregates findings
   - Deduplicates overlapping issues
   - Assigns severity and confidence

---

### 7.2 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14+ (App Router) | SSR, excellent file upload handling, TypeScript support |
| **Backend API** | Python + FastAPI | Python ecosystem for document parsing, async support |
| **LLM** | Gemini 3 Pro | Strong reasoning for logical consistency checks |
| **Agent Framework** | Google Agent Development Kit (ADK) | Native Gemini integration, multi-agent coordination |
| **Database** | PostgreSQL | Job tracking, findings storage (session-scoped for MVP) |
| **Object Storage** | Google Cloud Storage | Temporary document storage with TTL |
| **Task Queue** | Cloud Tasks / Celery + Redis | Async document processing |

---

### 7.3 Document Processing Architecture

```
Document Upload (.docx)
         │
         ▼
┌─────────────────────────────────┐
│    python-docx Extraction       │  ← Deterministic, fast
│  • Tables → pandas DataFrames   │
│  • Sections → Structured text   │
│  • Footnotes → References       │
│  • Page/paragraph locations     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│    Structured JSON Output       │  ← Clean data for agents
│  • Tables with cell references  │
│  • Section hierarchy            │
│  • Cross-reference mapping      │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│    Agent Layer (Google ADK)     │
│  • Numeric Validator (Python)   │  ← No LLM for math
│  • Logic Consistency (Gemini)   │  ← LLM for reasoning
│  • Disclosure Compliance (Rules)│  ← Rule engine
└─────────────────────────────────┘
```

> **Design Principle**: Deterministic tools own the **numbers**, LLM owns the **meaning**.

---

### 7.4 Gemini 3 Pro Usage Pattern
- Role-specific system prompts per agent
- Strict input-output schemas (JSON)
- Shared structured state across agents
- No free-form generation without grounding

---

## 8. User Experience (MVP)

### 8.1 Core Screens
1. Document upload and classification
2. Processing status by agent
3. Findings dashboard
4. Drill-down view with source citations

### 8.2 Interaction Model
- Read-only review mode for MVP
- No conversational interface initially (to reduce hallucination risk)

---

## 9. Privacy, Security & Compliance

- No training on client data
- Data processed only via private application programming interfaces (APIs)
- No persistent storage beyond session scope (MVP)
- Explicit disclaimer: AI-assisted review, not an audit opinion

---

## 10. Success Metrics

### Quantitative Metrics
- 100% detection of mathematical and casting errors
- ≥50% reduction in reviewer query cycles
- ≤10% false-positive rate on logical flags

### Qualitative Metrics
- User confidence sufficient to rely on output prior to sign-off

---

## 11. Strategic Note

Veritas AI targets non-automated, high-risk cognitive labor rather than generic text generation. Its value arises from multi-agent reasoning, deterministic validation, and audit-native explainability — not from model scale alone.
