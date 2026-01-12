# UAT Issues: Phase 03 Plan 01

**Tested:** 2026-01-10
**Source:** .planning/phases/03-numeric-validation/03-01-SUMMARY.md
**Tester:** User via /gsd:verify-work

## Open Issues

(None)

---

## Resolved Issues

### REFACTOR-001: Rename Planner agent to Extractor and simplify output

**Discovered:** 2026-01-12
**Resolved:** 2026-01-12
**Phase/Plan:** 03-01
**Severity:** Required (architecture alignment)
**Feature:** Agent naming and output schema

**Description:** Based on architecture review, the "Planner" agent needs to be renamed to "Extractor" to better reflect its purpose (extracting/identifying FSLIs). Additionally, the output schema needs to be simplified to return only FSLI names instead of full FSLI objects with values.

**Current State:**
- Agent name: `PlannerAgent`
- Folder: `backend/agents/numeric_validation/sub_agents/planner/`
- Output key: `planner_agent_output`
- Schema: Complex nested structure with `FSLI` containing `FSLIValue` objects

**Required Changes:**

#### 1. Folder Rename
```
backend/agents/numeric_validation/sub_agents/planner/
    ↓
backend/agents/numeric_validation/sub_agents/extractor/
```

#### 2. Agent Definition (`agent.py`)
```python
# Before
planner_agent = LlmAgent(
    name="PlannerAgent",
    output_key="planner_agent_output",
    output_schema=PlannerAgentAgentOutput,
    ...
)

# After
extractor_agent = LlmAgent(
    name="ExtractorAgent",
    output_key="extractor_output",
    output_schema=ExtractorAgentOutput,
    ...
)
```

#### 3. Schema Simplification (`schema.py`)
```python
# Before (complex)
class FSLIValue(BaseModel):
    label: str
    amount: float
    unit: str

class FSLI(BaseModel):
    name: str
    values: List[FSLIValue]
    source_ref: str

class PlannerAgentAgentOutput(BaseModel):
    fslis: List[FSLI]

# After (simplified)
class ExtractorAgentOutput(BaseModel):
    fsli_names: List[str]  # ["Revenue", "Cost of Sales", "Net Income", ...]
```

#### 4. Prompt Update (`prompt.py`)
```python
# Before - asks for names + values + source refs
INSTRUCTION = """
...extract all FSLIs...
For each identified FSLI, extract:
1. The name of the line item.
2. The associated numeric values...
3. A source reference...
"""

# After - asks only for names
INSTRUCTION = """
You are a financial document analyst specialized in identifying Financial Statement Line Items (FSLIs).

Given extracted document text, identify ALL Financial Statement Line Items (FSLIs) present in the document.

An FSLI is a named row or category in financial tables representing a balance or transaction type.
Examples: "Revenue", "Cost of Sales", "Net Income", "Total Assets", "Trade Receivables", "Goodwill".

Your task:
1. Scan ALL tables in the document (income statement, balance sheet, cash flow, notes)
2. Identify every unique FSLI name
3. Return ONLY the names - do NOT extract values or amounts

Output a list of FSLI names found in the document.
"""
```

#### 5. Root Agent Import Update (`agent.py`)
```python
# Before
from .sub_agents.planner import planner_agent
root_agent = SequentialAgent(
    ...
    sub_agents=[planner_agent],
)

# After
from .sub_agents.extractor import extractor_agent
root_agent = SequentialAgent(
    ...
    sub_agents=[extractor_agent],
)
```

#### 6. Sub-agents `__init__.py` Updates
```python
# Before (sub_agents/planner/__init__.py)
from .agent import planner_agent

# After (sub_agents/extractor/__init__.py)
from .agent import extractor_agent
```

#### 7. Test Updates (`tests/test_agent.py`)
```python
# Before
assert root_agent.sub_agents[0].name == "PlannerAgent"

# After
assert root_agent.sub_agents[0].name == "ExtractorAgent"
```

**Rationale:**
- "Extractor" better describes the agent's purpose (extracting/identifying FSLIs)
- Simplified output (names only) improves extraction accuracy
- The Verifier agent will analyze each FSLI in context of the full document
- Aligns with new architecture: Extractor → FanOutVerifier → Reviewer

**Impact on Future Phases:**
- 03-02 (FanOutVerifierAgent) will read `extractor_output.fsli_names` from session state
- 03-03 (ReviewerAgent) unchanged - reads from Verifier outputs

**Files to Modify:**
1. `backend/agents/numeric_validation/sub_agents/planner/` → rename to `extractor/`
2. `backend/agents/numeric_validation/sub_agents/extractor/agent.py` - rename agent
3. `backend/agents/numeric_validation/sub_agents/extractor/schema.py` - simplify schema
4. `backend/agents/numeric_validation/sub_agents/extractor/prompt.py` - update instruction
5. `backend/agents/numeric_validation/sub_agents/extractor/__init__.py` - update export
6. `backend/agents/numeric_validation/agent.py` - update import
7. `backend/agents/numeric_validation/tests/test_agent.py` - update assertions

**Resolution:**
- ✅ Renamed `sub_agents/planner/` to `sub_agents/extractor/`
- ✅ Simplified `ExtractorAgentOutput` schema to `fsli_names: List[str]`
- ✅ Updated `extractor/prompt.py` to focus only on FSLI names
- ✅ Renamed `PlannerAgent` to `ExtractorAgent` in `extractor/agent.py`
- ✅ Updated `extractor/agent.py` output key to `extractor_output`
- ✅ Updated all imports in `numeric_validation/agent.py` and `numeric_validation/sub_agents/__init__.py`
- ✅ Updated test assertions in `numeric_validation/tests/test_agent.py`
- ✅ All tests pass

**Final State:**
- Agent name: `ExtractorAgent`
- Folder: `backend/agents/numeric_validation/sub_agents/extractor/`
- Output key: `extractor_output`
- Schema: Simplified list of strings

### UAT-002: Gemini 3 models require billing enabled (quota limit 0 on free tier)

**Discovered:** 2026-01-10
**Resolved:** 2026-01-11
**Phase/Plan:** 03-01
**Severity:** Major (was blocking)
**Feature:** Agent execution via runner
**Description:** The `gemini-3-pro-preview` model requires billing to be enabled. The free tier quota for Gemini 3 models is set to 0, resulting in RESOURCE_EXHAUSTED errors.
**Expected:** Agent should execute and return FSLIs from test document
**Actual:** Agent now successfully extracts FSLIs with correct structure

**Resolution:**
- ✅ User enabled billing on Google Cloud project
- ✅ Switched back to `gemini-3-pro-preview` model
- ✅ Test passes: Agent successfully extracts FSLIs (Revenue, Cost of sales, Gross profit, Trade receivables)
- ✅ Removed temporary workaround code
- ✅ All agent infrastructure working correctly

**Test Results (2026-01-11):**
```json
{
  "fslis": [
    {"name": "Revenue", "values": [{"label": "2023", "amount": 1500000, "unit": "USD"}, ...]},
    {"name": "Cost of sales", "values": [...]},
    {"name": "Gross profit", "values": [...]},
    {"name": "Trade receivables", "values": [...]}
  ]
}
```

> **Note:** Output format will change after REFACTOR-001 to simplified `fsli_names` list.

**Final Status:**
- ✅ Agent creation works
- ✅ InMemoryRunner API works (`run_debug()` method)
- ✅ Using `gemini-3-pro-preview` as intended
- ✅ Billing enabled and working
- ✅ FSLI extraction working correctly

### UAT-001: LlmAgent created with invalid parameters

**Discovered:** 2026-01-10
**Phase/Plan:** 03-01
**Severity:** Blocker
**Feature:** Planner Agent instantiation
**Description:** The `create_planner_agent()` function uses parameters that don't exist on google-adk's `LlmAgent` class.
**Expected:** Agent should instantiate without errors
**Actual:** ValidationError - `response_schema` and `config` are "extra inputs not permitted"
**Repro:**
1. `cd backend && source .venv/bin/activate`
2. `python3 -c "from app.services.agents import create_planner_agent; create_planner_agent()"`

**Root cause:** The implementation assumed `LlmAgent` accepts `response_schema` and `config` with `thinking_config`, but google-adk 1.22.0 does not support these parameters.

**Fix needed:** Remove invalid parameters and use only supported LlmAgent parameters: `name`, `model`, `instruction`, `output_key`, and possibly `tools` or `code_executor`.

**Resolved:** 2026-01-10
**Fix:**
- Changed `response_schema` → `output_schema`
- Changed `config` with thinking_config → `planner=BuiltInPlanner(thinking_config=...)`
- Used `types.ThinkingConfig(thinking_level="high")` for thinking mode

---

*Phase: 03-numeric-validation*
*Plan: 01*
*Last Updated: 2026-01-12*
