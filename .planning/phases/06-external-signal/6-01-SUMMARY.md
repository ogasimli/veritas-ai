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
    - backend/agents/orchestrator/sub_agents/external_signal/agent.py
    - backend/agents/orchestrator/sub_agents/external_signal/prompt.py
    - backend/agents/orchestrator/sub_agents/external_signal/schema.py
    - backend/agents/orchestrator/sub_agents/external_signal/__init__.py
  modified:
    - backend/agents/orchestrator/agent.py
    - backend/agents/orchestrator/sub_agents/__init__.py
    - backend/app/services/processor.py
    - backend/agents/orchestrator/sub_agents/logic_consistency/agent.py (bugfix)

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
duration: 18 minutes
completed: 2026-01-19T15:45:00Z
---

# Phase 6 Plan 01: External Signal Integration

Created external signal agent that searches for news, litigation, and financial distress signals using Gemini's google_search tool, integrated into orchestrator as fourth parallel validation pipeline.

## Accomplishments

- Created standalone LlmAgent with google_search tool for external signal detection
- Configured gemini-2.5-flash model with temperature=1.0 for optimal grounding
- Designed schema for three signal types: news, litigation, financial_distress
- Integrated agent into ParallelAgent orchestrator for parallel execution
- Updated processor to extract and store external signal findings with category='external'
- Fixed logic_consistency agent bug (invalid SequentialAgent parameters)

## Files Created/Modified

**Created:**
- `backend/agents/orchestrator/sub_agents/external_signal/agent.py` - LlmAgent with google_search tool only, gemini-2.5-flash model, temperature 1.0
- `backend/agents/orchestrator/sub_agents/external_signal/prompt.py` - Instructions for extracting company name/year and searching for risk signals
- `backend/agents/orchestrator/sub_agents/external_signal/schema.py` - ExternalFinding and ExternalSignalOutput Pydantic models
- `backend/agents/orchestrator/sub_agents/external_signal/__init__.py` - Package exports

**Modified:**
- `backend/agents/orchestrator/agent.py` - Added external_signal_agent to ParallelAgent sub_agents list
- `backend/agents/orchestrator/sub_agents/__init__.py` - Exported external_signal_agent
- `backend/app/services/processor.py` - Added external signal findings extraction (section 3d) and storage (section 4d)
- `backend/agents/orchestrator/sub_agents/logic_consistency/agent.py` - Removed invalid output_key/output_schema parameters (bugfix)

## Decisions Made

1. **Model Selection**: Used gemini-2.5-flash instead of gemini-3-pro-preview for cost optimization - search tasks are lighter than analysis, and 2.5-flash is sufficient for google_search tool usage.

2. **Tool Configuration**: google_search as ONLY tool in agent following ADK one-tool restriction. Cannot combine with code_executor or other tools per RESEARCH.md findings.

3. **Temperature Setting**: Set temperature=1.0 via GenerateContentConfig, following official recommendation for optimal grounding quality.

4. **Query Generation**: Model-generated queries - provide context (company name, year) in prompt and let model optimize query construction rather than hardcoding query strings.

5. **Severity Hardcoding**: All external signal findings have severity='medium' (not risk-assessed) because external signals require human auditor review before making risk determinations.

6. **Import Path**: Used `from google.adk.tools import google_search` (not `google.adk.tools.gemini_api`) based on actual ADK structure.

## Issues Encountered

**Issue 1: Logic Consistency Agent Import Error**
- Problem: Existing logic_consistency agent had invalid parameters (output_key, output_schema) for SequentialAgent, causing import failures
- Resolution: Removed invalid parameters following deviation rule 1 (auto-fix bugs)
- Commit: fix(6-01): remove invalid output_key and output_schema from SequentialAgent (76beca3)

**Issue 2: Temperature Parameter Location**
- Problem: LlmAgent doesn't accept temperature as direct parameter
- Resolution: Used GenerateContentConfig wrapper with temperature=1.0 field
- No deviation - corrected during implementation

## Next Phase Readiness

Phase 6 complete. External signal agent now searches for news, litigation, and financial distress signals in parallel with other validation agents.

**Current architecture:**
```
ParallelAgent orchestrator
├── numeric_validation - Math verification with code execution
├── logic_consistency - Semantic contradiction detection
├── disclosure_compliance - IFRS checklist validation
└── external_signal - News/litigation/distress search (NEW)
```

**Validation suite complete:**
- Numeric validation (Phase 3) - Math verification
- Logic consistency (Phase 4) - Contradiction detection
- Disclosure compliance (Phase 5) - IFRS checklist
- External signals (Phase 6) - Web search for risk signals

Ready to proceed with Phase 7 (Frontend Dashboard).
