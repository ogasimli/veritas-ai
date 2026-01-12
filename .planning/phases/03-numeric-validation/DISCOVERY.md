# Phase 3: Numeric Validation - Discovery

## Research Level: Standard (Level 2)

Research conducted 2026-01-10 on Google ADK agent patterns and code_executor integration.
Updated 2026-01-12 with refined architecture based on design review.

## Agent Architecture Overview

The numeric validation pipeline uses three specialized agents with a CustomAgent for dynamic parallel execution:

```
[ExtractorAgent]
       |
       v
  fsli_names: ["Revenue", "Cost of Sales", "Net Income", ...]
       |
       v
[FanOutVerifierAgent] (CustomAgent)
       |
       +---> ParallelAgent (dynamically created)
       |         |
       |         +---> VerifierAgent("verify_Revenue")
       |         +---> VerifierAgent("verify_Cost_of_Sales")
       |         +---> VerifierAgent("verify_Net_Income")
       |         +---> ...
       |
       v
  Aggregated checks: [VerificationCheck, VerificationCheck, ...]
       |
       v
[ReviewerAgent] (with code_executor for re-verification)
       |
       v
  findings: [Finding, Finding, ...]
```

## Agent Definitions

### 1. ExtractorAgent (LlmAgent)

**Purpose**: Identify Financial Statement Line Items (FSLIs) from extracted document text.

**Key characteristics**:
- Model: `gemini-3-pro-preview`
- Output: List of FSLI names only (not values/amounts)
- Uses extended thinking for complex document analysis

**Output schema**:
```python
class ExtractorAgentOutput(BaseModel):
    fsli_names: List[str]  # ["Revenue", "Cost of Sales", ...]
```

**Rationale**: Simplified output improves extraction accuracy. The Verifier will analyze each FSLI in context of the full document.

### 2. FanOutVerifierAgent (CustomAgent)

**Purpose**: Dynamically spawn parallel VerifierAgents, one per FSLI.

**Key characteristics**:
- Extends `BaseAgent` (CustomAgent pattern)
- Reads FSLI names from session state
- Creates `ParallelAgent` at runtime with fresh VerifierAgent instances
- Maintains ADK observability by yielding events from ParallelAgent

**Why CustomAgent**: ADK's `ParallelAgent` requires static sub-agents at init time. For dynamic parallelism (N agents based on runtime data), we use the CustomAgent pattern that creates ParallelAgent inside `_run_async_impl()`.

### 3. VerifierAgent (LlmAgent - created per FSLI)

**Purpose**: Run verification checks for a single FSLI.

**Key characteristics**:
- Model: `gemini-3-pro-preview`
- Tool: `BuiltInCodeExecutor` only (exclusive - cannot combine with other tools)
- Input: Single FSLI name + full document text
- Output: List of verification checks (pass/fail)

**Check types**:
1. **In-table sum verification**: Do component parts sum to totals?
2. **Cross-table consistency**: Does same FSLI match across different tables?

**Output schema**:
```python
class VerificationCheck(BaseModel):
    fsli_name: str
    check_type: str              # "in_table_sum" | "cross_table_consistency"
    description: str             # What was checked
    expected_value: float
    actual_value: float
    result: str                  # "pass" | "fail"
    source_refs: List[str]
    code_executed: str           # Python code used for verification

class VerifierAgentOutput(BaseModel):
    checks: List[VerificationCheck]
```

### 4. ReviewerAgent (LlmAgent)

**Purpose**: Filter, re-verify, and format final findings.

**Key characteristics**:
- Model: `gemini-3-pro-preview`
- Tool: `BuiltInCodeExecutor` (for re-verification of failures)
- Input: Aggregated checks from all Verifiers
- Output: Deduplicated findings with severity

**Responsibilities**:
1. Filter out passing checks
2. Re-verify each failure using code execution
3. Generate concise summary from check details
4. Assign severity based on discrepancy magnitude
5. Deduplicate similar findings

**Output schema**:
```python
class Finding(BaseModel):
    fsli_name: str
    summary: str                 # Short human-readable summary
    severity: str                # "high" | "medium" | "low"
    expected_value: float
    actual_value: float
    discrepancy: float
    source_refs: List[str]

class ReviewerAgentOutput(BaseModel):
    findings: List[Finding]
```

## State Sharing Pattern

Agents communicate via session state using `output_key`:

```
ExtractorAgent (output_key="extractor_output")
     |
     v
session.state['extractor_output'] = {fsli_names: [...]}
     |
     v
FanOutVerifierAgent reads fsli_names, creates ParallelAgent
     |
     +---> VerifierAgent writes to session.state[f"checks:{fsli_name}"]
     |
     v
session.state['checks:*'] = [VerificationCheck, ...]
     |
     v
ReviewerAgent reads all checks:* keys, outputs findings
     |
     v
session.state['reviewer_output'] = {findings: [...]}
```

## Code Executor Limitations

**Critical constraint**: `BuiltInCodeExecutor` can only be used **by itself** within an agent instance. Cannot combine with other tools.

**Implication**: Both VerifierAgent and ReviewerAgent use code_executor exclusively (no other tools).

**Available in sandbox**: numpy, pandas (useful for financial table operations)

## Sources

- [Google ADK Sequential Agents](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/)
- [Multi-Agent Systems in ADK](https://google.github.io/adk-docs/agents/multi-agents/)
- [Code Execution in ADK](https://google.github.io/adk-docs/tools/gemini-api/code-execution/)
- [Building Dynamic Parallel Workflows](https://dev.to/masahide/building-dynamic-parallel-workflows-in-google-adk-lmn)

## Don't Hand-Roll

- Agent orchestration (use SequentialAgent, ParallelAgent)
- Dynamic parallelism (use CustomAgent pattern, not asyncio.gather)
- Code execution sandbox (use BuiltInCodeExecutor)
- State management between agents (use output_key and session.state)

## Implementation Notes

1. Use `gemini-3-pro-preview` model for all agents (Gemini 3 Pro)
2. Store findings in database via Finding model (already exists)
3. Update Job status throughout pipeline execution
4. FSLI = Financial Statement Line Item (e.g., "Revenue", "Total Assets")
5. CustomAgent preserves ADK observability and session state management
