---
phase: 06-external-signal
plan: 01
type: execute
---

<objective>
Create external signal agent that searches for news, litigation, and financial distress signals using Gemini's google_search tool, then integrate into the orchestrator for parallel execution.

Purpose: Provide auditors with external risk signals that may contradict or contextualize financial statement claims, completing the validation suite (numeric, logic, disclosure, external).

Output: Standalone external_signal agent added to ParallelAgent orchestrator, findings stored with category='external' in database.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-phase.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/06-external-signal/6-CONTEXT.md
@.planning/phases/06-external-signal/6-RESEARCH.md
@.planning/phases/05-disclosure-compliance/05-01-SUMMARY.md
@.planning/phases/04-logic-consistency/04-01-SUMMARY.md
@.planning/phases/03-numeric-validation/03-03-SUMMARY.md

**Key files:**
@backend/agents/orchestrator/agent.py
@backend/agents/orchestrator/sub_agents/__init__.py
@backend/app/services/processor.py

**Tech stack available:**
- Google ADK (LlmAgent, ParallelAgent patterns)
- Gemini 2.5/3.0 with google_search tool
- SQLAlchemy models (Finding, Job)
- Pydantic schemas for structured output

**Established patterns:**
- Standalone LlmAgent for non-pipeline agents (from Phase 4)
- ParallelAgent orchestrator for coordinating validation agents
- Finding storage with category field for differentiation
- Session state extraction pattern in processor.py

**Constraining decisions:**
- Phase 3: All agents use gemini-3-pro-preview model
- Phase 6 RESEARCH: google_search CANNOT be combined with other tools in single agent (one-tool restriction)
- Phase 6 CONTEXT: On-demand search (not periodic), extract company name + year from document, search for news/litigation/distress signals

**From RESEARCH.md (CRITICAL):**
- **DON'T hand-roll**: Custom web scraping, manual query construction, citation tracking - use google_search tool
- **Architecture**: Standalone LlmAgent with google_search as ONLY tool (cannot mix with code_executor)
- **Key pitfall**: Mixing tools - google_search must be sole tool in agent (ADK enforces this)
- **Search approach**: Provide context (company name, year) in prompt, let model generate optimal queries
- **Grounding metadata**: Extract source URLs from groundingMetadata for citation tracking
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create external_signal agent with google_search tool</name>
  <files>backend/agents/orchestrator/sub_agents/external_signal/agent.py, backend/agents/orchestrator/sub_agents/external_signal/prompt.py, backend/agents/orchestrator/sub_agents/external_signal/schema.py, backend/agents/orchestrator/sub_agents/external_signal/__init__.py</files>
  <action>
Create external_signal agent as standalone LlmAgent with google_search tool.

**1. Schema** (`sub_agents/external_signal/schema.py`):
```python
from typing import List, Literal
from pydantic import BaseModel, Field

class ExternalFinding(BaseModel):
    """A risk signal found through external search."""
    signal_type: Literal["news", "litigation", "financial_distress"] = Field(
        description="Type of signal detected"
    )
    summary: str = Field(
        description="Brief summary of the signal"
    )
    source_url: str = Field(
        description="URL of the source article/filing"
    )
    publication_date: str = Field(
        default="",
        description="Publication date if available (YYYY-MM-DD format)"
    )
    potential_contradiction: str = Field(
        default="",
        description="What financial statement claim this might contradict (empty if no contradiction)"
    )

class ExternalSignalOutput(BaseModel):
    """Output from external signal agent - risk signals from news/litigation search."""
    findings: List[ExternalFinding] = Field(
        default_factory=list,
        description="External risk signals discovered through search"
    )
```

**2. Prompt** (`sub_agents/external_signal/prompt.py`):
```python
INSTRUCTION = """You are an external signal agent that searches for risk signals about the company being audited.

## Input

You receive the financial statement document text from session state.

Your first task is to extract:
1. Company name (legal entity name from the document)
2. Reporting period year (fiscal year covered by the statement)

## Your Task

Search for external signals that may contradict or contextualize claims in the financial statement.

**Signal types to search:**
1. **News articles** - Recent company developments, major events, controversies
2. **Litigation/legal issues** - Lawsuits, regulatory actions, legal proceedings
3. **Financial distress signals** - Credit downgrades, bankruptcy filings, liquidity concerns

## Search Approach

- Extract company name and fiscal year from the document first
- Let the google_search tool generate optimal queries based on context you provide
- Focus on reporting period timeframe (e.g., 2025 fiscal year → search 2025 events + Q4 2024 for context)
- Use reputable sources only (official filings, major news outlets, regulatory sites)
- Search for multiple signal types

Example context for search:
- "Find recent news about [Company X] during [Year]"
- "Search for litigation and legal proceedings involving [Company X] in [Year]"
- "Look for financial distress signals, credit ratings, or bankruptcy filings for [Company X] in [Year]"

## Output Findings

For each significant signal found:
- Signal type (news/litigation/financial_distress)
- Summary of what was found (2-3 sentences)
- Source URL and publication date
- Potential contradiction with financial statement (if any)

**If no significant signals found**, output empty findings list (this is valid - not all companies have external red flags).

## Guidelines

- Focus on reporting period timeframe (fiscal year + few months prior for context)
- Use reputable sources only (no social media, no rumors)
- Flag contradictions but don't draw conclusions - auditor will verify
- Extract source URLs from search results for citation

## Example

**Document excerpt:**
"XYZ Corp - Annual Report for fiscal year ended December 31, 2025. The company has no material litigation pending..."

**Search context:**
- Company: XYZ Corp
- Year: 2025

**Potential finding:**
- Signal type: litigation
- Summary: "Major class-action lawsuit filed against XYZ Corp in March 2025 alleging securities fraud"
- Source: https://example.com/news/xyz-lawsuit
- Publication date: 2025-03-15
- Potential contradiction: "Financial statement claims no material litigation, but lawsuit was filed during reporting period"
"""
```

**3. Agent** (`sub_agents/external_signal/agent.py`):
```python
"""External signal agent - searches news/litigation via google_search."""
from google.adk.agents import LlmAgent
from google.adk.tools.gemini_api import google_search
from . import prompt
from .schema import ExternalSignalOutput

external_signal_agent = LlmAgent(
    name="external_signal",
    model="gemini-2.5-flash",  # Compatible with google_search (Gemini 2+ required)
    instruction=prompt.INSTRUCTION,
    tools=[google_search],  # CRITICAL: ONLY google_search, cannot add other tools
    output_key="external_signal_output",
    output_schema=ExternalSignalOutput,
    temperature=1.0,  # Recommended for grounding per RESEARCH.md
)
```

**4. Package** (`sub_agents/external_signal/__init__.py`):
```python
from .agent import external_signal_agent

__all__ = ["external_signal_agent"]
```

**Design notes:**
- **Standalone agent**: google_search is sole tool (ADK one-tool restriction per RESEARCH.md)
- **Model-generated queries**: Prompt provides context (company name, year), model generates optimal search queries
- **Temperature 1.0**: Official recommendation for grounding quality (per RESEARCH.md)
- **Gemini 2.5-flash**: Compatible with google_search (Gemini 2+ required), lighter than 3-pro for search tasks
- **Category field**: Not in schema (added during processor.py mapping as category='external')

**What to avoid:**
- DON'T add code_executor or other tools (violates one-tool restriction)
- DON'T use gemini-3-pro-preview if 2.5-flash works (cost optimization)
- DON'T hardcode query strings in prompt (let model generate queries)
- DON'T manually parse search results (model handles via google_search tool)
  </action>
  <verify>
Directory structure exists:
- `backend/agents/orchestrator/sub_agents/external_signal/`
- Files: agent.py, prompt.py, schema.py, __init__.py
- Can import: `from backend.agents.orchestrator.sub_agents.external_signal import external_signal_agent`
- Agent instantiates without errors
  </verify>
  <done>external_signal agent created as standalone LlmAgent with google_search tool only, follows established LlmAgent pattern from Phase 4, temperature=1.0 for grounding</done>
</task>

<task type="auto">
  <name>Task 2: Integrate external_signal agent into orchestrator and processor</name>
  <files>backend/agents/orchestrator/agent.py, backend/agents/orchestrator/sub_agents/__init__.py, backend/app/services/processor.py</files>
  <action>
Add external_signal_agent to ParallelAgent orchestrator and update processor to extract/store findings.

**1. Update sub_agents package** (`sub_agents/__init__.py`):
```python
from .numeric_validation import numeric_validation_agent
from .logic_consistency import logic_consistency_agent
from .disclosure_compliance import disclosure_compliance_agent
from .external_signal import external_signal_agent

__all__ = [
    "numeric_validation_agent",
    "logic_consistency_agent",
    "disclosure_compliance_agent",
    "external_signal_agent",
]
```

**2. Update orchestrator** (`agent.py`):
```python
"""Root orchestrator agent definition."""
from google.adk.agents import ParallelAgent
from .sub_agents import (
    numeric_validation_agent,
    logic_consistency_agent,
    disclosure_compliance_agent,
    external_signal_agent,
)

root_agent = ParallelAgent(
    name='audit_orchestrator',
    description='Coordinates parallel validation agents for financial statement audit',
    sub_agents=[
        numeric_validation_agent,       # Phase 3: Numeric validation pipeline
        logic_consistency_agent,        # Phase 4: Logic consistency detection
        disclosure_compliance_agent,    # Phase 5: Disclosure compliance checking
        external_signal_agent,          # Phase 6: External risk signal search
    ],
)
```

**3. Update processor** (`processor.py`):
Add external signal findings extraction after disclosure findings (around line 75):

```python
# 3d. Extract external signal findings
external_state = final_state.get("external_signal", {})
external_output = external_state.get("external_signal_output", {})
external_findings = external_output.get("findings", [])

# 4d. Save external signal findings (after 4c disclosure findings section)
for finding_data in external_findings:
    finding = FindingModel(
        job_id=job_id,
        category="external",
        severity="medium",  # External signals are always medium (for auditor review)
        description=finding_data.get("summary", ""),
        source_refs=[finding_data.get("source_url", "")],
        reasoning=f"Signal type: {finding_data.get('signal_type')}, "
                 f"Publication: {finding_data.get('publication_date', 'unknown')}, "
                 f"Potential contradiction: {finding_data.get('potential_contradiction', 'none')}",
        agent_id="external_signal",
    )
    self.db.add(finding)
```

Update the comment at line 34 to reflect Phase 6:
```python
# Future agents: external_signal (Phase 6)  →  # external_signal (Phase 6) ✓
```

**Key points:**
- external_signal runs in parallel with other agents (ParallelAgent coordination)
- Session state key matches agent name: `external_signal`
- Output key matches agent definition: `external_signal_output`
- Findings stored with category='external' for DB differentiation
- Severity hardcoded to 'medium' (external signals require auditor review, not auto-risk assessment)

**What to avoid:**
- DON'T use SequentialAgent (external_signal is simple LlmAgent, not a pipeline)
- DON'T extract from wrong session state keys (match agent name exactly)
- DON'T forget to add to both orchestrator AND processor (both needed for integration)
  </action>
  <verify>
- orchestrator agent.py imports external_signal_agent
- orchestrator agent.py sub_agents list has 4 items: [numeric, logic, disclosure, external]
- sub_agents/__init__.py exports external_signal_agent
- processor.py has external signal extraction section (after line 75)
- processor.py has external signal saving section (after disclosure section)
- Can import root_agent without errors
  </verify>
  <done>external_signal_agent integrated into ParallelAgent orchestrator and processor.py for findings extraction/storage, maintains backward compatibility with existing agents</done>
</task>

</tasks>

<verification>
Before declaring phase complete:
- [ ] external_signal agent directory structure created
- [ ] Agent instantiates with google_search tool only (no other tools)
- [ ] Orchestrator includes external_signal_agent in sub_agents list
- [ ] Processor extracts external_signal findings from session state
- [ ] Processor saves findings with category='external'
- [ ] No import errors in orchestrator or processor
- [ ] Follows established patterns (LlmAgent from Phase 4, ParallelAgent from Phase 3.1)
</verification>

<success_criteria>

- All tasks completed
- external_signal agent created as standalone LlmAgent with google_search tool
- Agent integrated into ParallelAgent orchestrator (4th parallel validation agent)
- Processor updated to extract and store external signal findings
- Findings stored with category='external' for DB differentiation
- No errors in imports or agent instantiation
- Follows one-tool restriction (google_search only, per RESEARCH.md)
</success_criteria>

<output>
After completion, create `.planning/phases/06-external-signal/6-01-SUMMARY.md`:

---
phase: 06-external-signal
plan: 01
subsystem: validation
tags: [google-search, gemini, external-signals, news, litigation, parallel-agents]

# Dependency graph
requires:
  - phase: 3.1-root-orchestrator-agent
    provides: ParallelAgent orchestrator coordinating validation agents
  - phase: 04-logic-consistency
    provides: Simple LlmAgent pattern for non-pipeline agents
provides:
  - external_signal agent with google_search tool for news/litigation/distress signals
  - Integration with orchestrator as fourth parallel validation pipeline
  - Company name + year extraction from documents for targeted searches
affects: [orchestrator integration (backward compatible), processor findings extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Standalone LlmAgent with google_search tool", "One-tool restriction workaround", "Model-generated search queries"]

key-files:
  created:
    - backend/agents/orchestrator/sub_agents/external_signal/
  modified:
    - backend/agents/orchestrator/agent.py
    - backend/agents/orchestrator/sub_agents/__init__.py
    - backend/app/services/processor.py

key-decisions:
  - "Used gemini-2.5-flash instead of 3-pro for cost optimization (search tasks lighter than analysis)"
  - "google_search as ONLY tool in agent (ADK one-tool restriction per RESEARCH.md)"
  - "Temperature 1.0 for optimal grounding quality (official recommendation)"
  - "Model-generated queries (provide context, let model optimize query construction)"
  - "Severity hardcoded to 'medium' (external signals require auditor review, not auto-risk)"

patterns-established:
  - "One-tool agent architecture for google_search (cannot mix with other tools)"
  - "Context-based search (company name + year) for targeted results"
  - "Source URL extraction for citation tracking"

issues-created: []

# Metrics
duration: TBD
completed: TBD
---

# Phase 6 Plan 01: External Signal Summary

**[Substantive one-liner describing what shipped]**

## Accomplishments

- [Key outcomes]

## Files Created/Modified

- [List files with descriptions]

## Decisions Made

- [Key decisions and rationale, or "None"]

## Issues Encountered

- [Problems and resolutions, or "None"]

## Next Phase Readiness

Phase 6 complete. external_signal agent now searches for news, litigation, and financial distress signals.

**Current architecture:**
```
ParallelAgent orchestrator
├── numeric_validation - Math verification with code execution
├── logic_consistency - Semantic contradiction detection
├── disclosure_compliance - IFRS checklist validation
└── external_signal - News/litigation/distress search (NEW)
```

Ready to proceed with Phase 7 (Frontend Dashboard).
</output>
