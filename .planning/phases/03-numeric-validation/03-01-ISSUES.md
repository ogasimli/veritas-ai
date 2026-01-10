# UAT Issues: Phase 03 Plan 01

**Tested:** 2026-01-10
**Source:** .planning/phases/03-numeric-validation/03-01-SUMMARY.md
**Tester:** User via /gsd:verify-work

## Open Issues

None - all issues resolved!

## Resolved Issues

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
*Tested: 2026-01-10*
