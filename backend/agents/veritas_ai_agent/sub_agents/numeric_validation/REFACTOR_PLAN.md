# Numeric Validation Pipeline Refactoring Plan

## Overview

This plan describes the complete refactoring of the numeric validation pipeline to:
1. Eliminate LLM hallucinations by extracting tables programmatically
2. Consolidate in-table and cross-table validation into a unified pipeline
3. Use fan-out parallelization for scalable formula reconstruction

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Input: Markdown Document                               │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Programmatic Table Extraction (Python - No LLM)                        │
│  ───────────────────────────────────────────────────────                        │
│  • Uses markdown_table_extractor library                                        │
│  • Parses numbers with locale detection (babel)                                 │
│  • Outputs: {tables: [{table_index, grid: 2D array}]}                           │
│  • Stored in state: "extracted_tables_raw"                                      │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Table Namer Agent (Lightweight LLM)                                    │
│  ──────────────────────────────────────────                                     │
│  • ONLY assigns table_name to each table                                        │
│  • Uses: header > caption > context inference                                   │
│  • Output: {table_names: ["Name1", "Name2", ...]}                               │
│  • after_agent_callback merges with extracted_tables_raw                        │
│  • Stored in state: "extracted_tables"                                          │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │         ParallelAgent            │
                    │   (in_table + cross_table)       │
                    └─────────────────┬─────────────────┘
                                      │
          ┌───────────────────────────┴───────────────────────────┐
          │                                                       │
          ▼                                                       ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────────┐
│  IN-TABLE PIPELINE              │         │  CROSS-TABLE PIPELINE               │
│  (InTableFormulaFanOut)         │         │  (SequentialAgent)                  │
│  ─────────────────────          │         │  ─────────────────────              │
│  • Reads extracted_tables       │         │  1. FsliExtractorAgent              │
│  • Intelligent batching:        │         │     • Extracts primary + sub FSLIs  │
│    - Complex tables: separate   │         │     • State: "fsli_extractor_output"│
│    - Simple tables: batched     │         │                                     │
│  • Each agent proposes formulas │         │  2. CrossTableFormulaFanOut         │
│  • after_agent_callback writes  │         │     • Batches FSLIs (FSLI_BATCH_SIZE│
│    to state with check_type=    │         │     • Each agent proposes cross-    │
│    "in_table"                   │         │       table relationships           │
│  • State: "reconstructed_       │         │     • after_agent_callback writes   │
│    formulas" (shared)           │         │       with check_type="cross_table" │
└─────────────────┬───────────────┘         └─────────────────┬───────────────────┘
                  │                                           │
                  └───────────────────────────┬───────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Formula Execution (before_agent_callback - Python)                     │
│  ─────────────────────────────────────────────────────────                      │
│  • Reads "reconstructed_formulas" from state                                    │
│  • Evaluates each formula using formula_engine.py                               │
│  • Filters formulas where |calculated - actual| >= 1.0                          │
│  • Ranks issues by absolute difference (descending)                             │
│  • Stores in state: "formula_execution_issues"                                  │
└─────────────────────────────────────────────┬───────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Aggregator Agent (LlmAgent)                                            │
│  ───────────────────────────────────                                            │
│  • Reads "formula_execution_issues" from state                                  │
│  • Deduplicates findings (same cell/FSLI flagged by both pipelines)             │
│  • Generates human-readable description for each issue                          │
│  • Output: {issues: [{issue_description, check_type, difference, ...}]}         │
│  • State: "numeric_validation_output"                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
backend/agents/veritas_ai_agent/sub_agents/numeric_validation/
├── agent.py                              # MODIFY: New pipeline orchestration
├── schemas.py                            # NEW: Shared schemas for formulas
├── table_extraction/                     # NEW: Programmatic extraction
│   ├── __init__.py
│   ├── extractor.py                      # Table extraction logic
│   └── number_parser.py                  # Number parsing with locale detection
├── sub_agents/
│   ├── table_namer/                      # NEW: Lightweight naming agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── prompt.py
│   │   ├── schema.py
│   │   └── callbacks.py                  # Merge names with extracted_tables_raw
│   ├── in_table_pipeline/         # NEW: In-table formula reconstruction
│   │   ├── __init__.py
│   │   ├── agent.py                      # CustomAgent with intelligent batching
│   │   ├── prompt.py
│   │   ├── schema.py
│   │   └── callbacks.py                  # Write to shared state
│   ├── cross_table_pipeline/             # NEW: Cross-table validation
│   │   ├── __init__.py
│   │   ├── agent.py                      # SequentialAgent wrapper
│   │   └── sub_agents/
│   │       ├── fsli_extractor/
│   │       │   ├── __init__.py
│   │       │   ├── agent.py
│   │       │   ├── prompt.py
│   │       │   └── schema.py
│   │       └── cross_table_fan_out/
│   │           ├── __init__.py
│   │           ├── agent.py
│   │           ├── prompt.py
│   │           ├── schema.py
│   │           └── callbacks.py          # Write to shared state
│   ├── formula_engine.py                 # MODIFY: Add multi-table support
│   └── aggregator/                       # NEW: Final aggregator
│       ├── __init__.py
│       ├── agent.py
│       ├── prompt.py
│       ├── schema.py
│       └── callbacks.py                  # Execute formulas before aggregation
└── DELETE:
    ├── sub_agents/in_table_verification/
    └── sub_agents/legacy_numeric_validation/
```

---

## Intelligent Batching Strategy for In-Table Fan-Out

### Complexity Scoring

Each table gets a complexity score based on multiple factors:

```python
def calculate_table_complexity(table: dict) -> int:
    """
    Calculate complexity score for a table.
    Higher score = more complex = should be processed alone.
    """
    grid = table["grid"]
    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    # Base complexity: grid size
    size_score = rows * cols

    # Bonus for many numeric cells (more potential formulas)
    numeric_cells = sum(
        1 for row in grid for cell in row
        if isinstance(cell, (int, float)) or _is_numeric_string(cell)
    )
    numeric_ratio = numeric_cells / max(size_score, 1)

    # Bonus for potential subtotal rows (keywords in first column)
    subtotal_keywords = ['total', 'subtotal', 'net', 'gross', 'balance', 'sum']
    subtotal_rows = sum(
        1 for row in grid
        if any(kw in str(row[0]).lower() for kw in subtotal_keywords)
    )

    # Final score
    complexity = size_score + (numeric_ratio * 20) + (subtotal_rows * 10)
    return int(complexity)
```

### Batching Thresholds

```python
# Environment configurable
SIMPLE_TABLE_THRESHOLD = int(os.getenv("SIMPLE_TABLE_THRESHOLD", "30"))  # complexity <= 30
COMPLEX_TABLE_THRESHOLD = int(os.getenv("COMPLEX_TABLE_THRESHOLD", "100"))  # complexity >= 100
MAX_BATCH_COMPLEXITY = int(os.getenv("MAX_BATCH_COMPLEXITY", "80"))  # max combined score per batch

def batch_tables_by_complexity(tables: list[dict]) -> list[list[dict]]:
    """
    Batch tables intelligently:
    - Complex tables (>= COMPLEX_TABLE_THRESHOLD): Always alone
    - Medium tables: Group up to MAX_BATCH_COMPLEXITY total
    - Simple tables (<= SIMPLE_TABLE_THRESHOLD): Batch aggressively
    """
    scored_tables = [(t, calculate_table_complexity(t)) for t in tables]
    scored_tables.sort(key=lambda x: x[1], reverse=True)  # Complex first

    batches = []
    current_batch = []
    current_batch_complexity = 0

    for table, complexity in scored_tables:
        # Complex tables go alone
        if complexity >= COMPLEX_TABLE_THRESHOLD:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_batch_complexity = 0
            batches.append([table])
            continue

        # Check if adding to current batch would exceed limit
        if current_batch_complexity + complexity > MAX_BATCH_COMPLEXITY:
            if current_batch:
                batches.append(current_batch)
            current_batch = [table]
            current_batch_complexity = complexity
        else:
            current_batch.append(table)
            current_batch_complexity += complexity

    if current_batch:
        batches.append(current_batch)

    return batches
```

### Example Batching

| Table | Rows×Cols | Subtotals | Complexity | Batch |
|-------|-----------|-----------|------------|-------|
| Balance Sheet | 25×4 | 8 | 180 | Alone |
| Income Statement | 15×3 | 5 | 95 | Alone |
| Note 5 (simple) | 3×2 | 1 | 16 | Batch A |
| Note 6 (simple) | 4×2 | 0 | 8 | Batch A |
| Note 7 (medium) | 8×3 | 2 | 44 | Batch A |
| Note 8 (simple) | 2×3 | 1 | 16 | Batch B |

---

## Shared State Schema

### Unified Formula State: `reconstructed_formulas`

Both in-table and cross-table pipelines write to the SAME state key:

```python
# State key: "reconstructed_formulas"
# Type: list[dict]

state["reconstructed_formulas"] = [
    # In-table formulas (check_type: "in_table")
    {
        "check_type": "in_table",
        "table_index": 0,
        "table_name": "Statement of Financial Position",
        "target_cell": {"table_index": 0, "row": 8, "col": 1},
        "actual_value": 800.0,
        "inferred_formulas": [
            {
                "formula": "sum_cells((0,4,1), (0,7,1))",
                "semantic_basis": "Grand total as sum of section subtotals",
                "description": "Sum of subtotals: Current + Non-Current"
            }
        ]
    },
    # Cross-table formulas (check_type: "cross_table")
    {
        "check_type": "cross_table",
        "fsli_id": "Trade receivables",
        "formula_type": "direct",
        "description": "Balance sheet receivables vs note breakdown",
        "formula": "TradeReceivables_BS = TradeReceivables_Note",
        "sources": [
            {"table": "Balance Sheet", "row": 5, "col": 1, "label": "Trade receivables"},
            {"table": "Note 7", "row": 12, "col": 2, "label": "Trade receivables"}
        ]
    },
    ...
]
```

### All State Keys

```python
# Step 1: Programmatic extraction
state["extracted_tables_raw"] = {
    "tables": [
        {"table_index": 0, "grid": [[...]]},
        ...
    ]
}

# Step 2: After table namer callback merges names
state["extracted_tables"] = {
    "tables": [
        {"table_index": 0, "table_name": "Balance Sheet", "grid": [[...]]},
        ...
    ]
}

# After FSLI extraction
state["fsli_extractor_output"] = {
    "primary_fsli": ["Property, plant and equipment", ...],
    "sub_fsli": ["Interest on lease liabilities", ...]
}

# Shared formula state (both pipelines write here)
state["reconstructed_formulas"] = [...]  # See above

# After formula execution (before aggregator)
state["formula_execution_issues"] = [...]  # Filtered & sorted by difference

# Final output
state["numeric_validation_output"] = {
    "issues": [{"issue_description": "...", "check_type": "...", ...}]
}
```

---

## Configuration

### Environment Variables

```bash
# .env
FSLI_BATCH_SIZE=5                    # FSLIs per cross-table agent
SIMPLE_TABLE_THRESHOLD=30            # Tables with complexity <= this are "simple"
COMPLEX_TABLE_THRESHOLD=100          # Tables with complexity >= this run alone
MAX_BATCH_COMPLEXITY=80              # Max combined complexity per batch
```

---

## Design Conventions

### Prompt templating
Every LLM agent's prompt is a static string constant (`INSTRUCTION`) in its
`prompt.py`.  ADK automatically substitutes `{key}` placeholders with the
value of `state["key"]` before sending the request — no builder function or
manual formatting needed.  Prefer referencing state keys directly rather than
constructing intermediate summaries.

### Callbacks live in `callbacks.py`
Each agent directory owns a `callbacks.py` that exports its `before_agent_callback`
and/or `after_agent_callback`.  `agent.py` imports them by name.  This keeps
the agent definition file minimal and makes callback logic independently
testable.

---

## Implementation Tasks

### Task 1: Table Extraction Module
**Goal**: Create programmatic table extraction with number parsing
**Testable**: Run on sample MD file, verify JSON output
**Files**:
- `table_extraction/__init__.py`
- `table_extraction/extractor.py`
- `table_extraction/number_parser.py`

**Test**:
```bash
python -c "from table_extraction import extract_tables_from_markdown; print(extract_tables_from_markdown(open('test.md').read()))"
```

---

### Task 2: Table Namer Agent
**Goal**: Create lightweight agent that only assigns table names
**Testable**: Run agent with mock state, verify names output
**Files**:
- `sub_agents/table_namer/__init__.py`
- `sub_agents/table_namer/agent.py`
- `sub_agents/table_namer/prompt.py`
- `sub_agents/table_namer/schema.py`
- `sub_agents/table_namer/callbacks.py`

**Callback flow** (`callbacks.py`):
- `before_agent_callback` — runs programmatic extraction, writes
  `state["extracted_tables_raw"]`.  No summary or preview is built; the
  full payload is injected into the prompt via `{extracted_tables_raw}`
  template substitution.
- `after_agent_callback` — reads `state["table_namer_output"]` (the
  `TableNamerOutput` written by ADK's `output_schema` machinery), builds
  a `{table_index -> table_name}` map, and merges it with the raw grids.
  Falls back to `"Table {idx}"` for any index the LLM did not name.
  Writes `state["extracted_tables"]`.

---

### Task 3: Shared Schemas
**Goal**: Create shared Pydantic schemas for formula state
**Testable**: Import and validate sample data
**Files**:
- `schemas.py`

**Contents**:
```python
from pydantic import BaseModel, Field
from typing import Literal

class TargetCell(BaseModel):
    table_index: int
    row: int
    col: int

class InferredFormula(BaseModel):
    formula: str
    semantic_basis: str
    description: str

class SourceReference(BaseModel):
    table: str
    row: int
    col: int
    label: str

class ReconstructedFormula(BaseModel):
    """Unified schema for both in-table and cross-table formulas."""
    check_type: Literal["in_table", "cross_table"]

    # In-table specific
    table_index: int | None = None
    table_name: str | None = None
    target_cell: TargetCell | None = None
    actual_value: float | None = None
    inferred_formulas: list[InferredFormula] | None = None

    # Cross-table specific
    fsli_id: str | None = None
    formula_type: str | None = None  # "direct" | "multi_step"
    description: str | None = None
    formula: str | None = None
    sources: list[SourceReference] | None = None
```

---

### Task 4: Update Formula Engine
**Goal**: Add multi-table support to formula evaluation
**Testable**: Unit tests for formula evaluation
**Files**:
- `sub_agents/formula_engine.py` (modify existing)

**Key Changes**:
- Add `evaluate_formula_with_tables(formula, table_grids: dict[int, list])`
- Keep backward-compatible `evaluate_single_formula`

---

### Task 5: In-Table Formula Fan-Out Agent
**Goal**: Create fan-out agent with intelligent batching
**Testable**: Run with mock tables, verify batching logic
**Files**:
- `sub_agents/in_table_pipeline/__init__.py`
- `sub_agents/in_table_pipeline/agent.py`
- `sub_agents/in_table_pipeline/prompt.py`
- `sub_agents/in_table_pipeline/schema.py`
- `sub_agents/in_table_pipeline/callbacks.py`

**Callback Logic** (writes to shared state):
```python
async def write_in_table_formulas_callback(callback_context: CallbackContext) -> None:
    """Write in-table formulas to shared reconstructed_formulas state."""
    state = callback_context.state

    # Initialize shared state if not exists
    if "reconstructed_formulas" not in state:
        state["reconstructed_formulas"] = []

    # Collect outputs from all batch agents
    for key in list(state.keys()):
        if key.startswith("in_table_batch_output_"):
            output = state[key]
            for formula_entry in output.get("formulas", []):
                # Add check_type and append to shared state
                formula_entry["check_type"] = "in_table"
                state["reconstructed_formulas"].append(formula_entry)
```

---

### Task 6: FSLI Extractor Agent
**Goal**: Create agent to extract primary and sub-FSLIs
**Testable**: Run on sample doc, verify FSLI extraction
**Files**:
- `sub_agents/cross_table_pipeline/sub_agents/fsli_extractor/__init__.py`
- `sub_agents/cross_table_pipeline/sub_agents/fsli_extractor/agent.py`
- `sub_agents/cross_table_pipeline/sub_agents/fsli_extractor/prompt.py`
- `sub_agents/cross_table_pipeline/sub_agents/fsli_extractor/schema.py`

---

### Task 7: Cross-Table Formula Fan-Out Agent
**Goal**: Create fan-out agent for FSLI-batched cross-table analysis
**Testable**: Run with mock FSLIs and tables
**Files**:
- `sub_agents/cross_table_pipeline/sub_agents/cross_table_fan_out/__init__.py`
- `sub_agents/cross_table_pipeline/sub_agents/cross_table_fan_out/agent.py`
- `sub_agents/cross_table_pipeline/sub_agents/cross_table_fan_out/prompt.py`
- `sub_agents/cross_table_pipeline/sub_agents/cross_table_fan_out/schema.py`
- `sub_agents/cross_table_pipeline/sub_agents/cross_table_fan_out/callbacks.py`

**Callback Logic** (writes to shared state):
```python
async def write_cross_table_formulas_callback(callback_context: CallbackContext) -> None:
    """Write cross-table formulas to shared reconstructed_formulas state."""
    state = callback_context.state

    if "reconstructed_formulas" not in state:
        state["reconstructed_formulas"] = []

    for key in list(state.keys()):
        if key.startswith("cross_table_batch_output_"):
            output = state[key]
            for rel in output.get("cross_table_relationships", []):
                rel["check_type"] = "cross_table"
                state["reconstructed_formulas"].append(rel)
```

---

### Task 8: Cross-Table Pipeline Wrapper
**Goal**: Create SequentialAgent wrapping FSLI extractor + cross-table fan-out
**Testable**: Integration test with both agents
**Files**:
- `sub_agents/cross_table_pipeline/__init__.py`
- `sub_agents/cross_table_pipeline/agent.py`

---

### Task 9: Aggregator Agent
**Goal**: Create aggregator with formula execution callback
**Testable**: Run with mock formula_execution_issues
**Files**:
- `sub_agents/aggregator/__init__.py`
- `sub_agents/aggregator/agent.py`
- `sub_agents/aggregator/prompt.py`
- `sub_agents/aggregator/schema.py`
- `sub_agents/aggregator/callbacks.py`

**Callback Logic** (formula execution):
```python
async def execute_formulas_callback(callback_context: CallbackContext) -> None:
    """Execute all formulas and filter to issues with diff >= 1.0."""
    state = callback_context.state
    formulas = state.get("reconstructed_formulas", [])
    tables = state.get("extracted_tables", {}).get("tables", [])

    # Build table grids lookup
    table_grids = {t["table_index"]: t["grid"] for t in tables}
    table_names = {t["table_index"]: t["table_name"] for t in tables}

    issues = []
    for entry in formulas:
        if entry["check_type"] == "in_table":
            issues.extend(_evaluate_in_table(entry, table_grids, table_names))
        else:
            issues.extend(_evaluate_cross_table(entry, table_grids, table_names))

    # Sort by |difference| descending
    issues.sort(key=lambda x: abs(x.get("difference", 0)), reverse=True)
    state["formula_execution_issues"] = issues
```

---

### Task 10: Pipeline Orchestration
**Goal**: Wire everything together in agent.py
**Testable**: Full integration test
**Files**:
- `agent.py` (complete rewrite)

**Structure**:
```python
numeric_validation_agent = SequentialAgent(
    name="NumericValidation",
    sub_agents=[
        table_namer_agent,  # Has before_callback for extraction
        ParallelAgent(
            name="FormulaReconstruction",
            sub_agents=[
                in_table_pipeline,
                cross_table_pipeline
            ]
        ),
        aggregator_agent  # Has before_callback for formula execution
    ]
)
```

---

### Task 11: Cleanup
**Goal**: Remove old pipeline code
**Files to Delete**:
- `sub_agents/in_table_verification/` (entire directory)
- `sub_agents/legacy_numeric_validation/` (entire directory)

---

## Task Execution Order

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1: Foundation (No dependencies)                       │
│  ─────────────────────────────────────                       │
│  • Task 1: Table Extraction Module                           │
│  • Task 3: Shared Schemas                                    │
│  • Task 4: Update Formula Engine                             │
│  Can be done in parallel, independently testable             │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 2: Table Namer (Depends on Task 1)                    │
│  ────────────────────────────────────────                    │
│  • Task 2: Table Namer Agent                                 │
│  Test: extraction → naming → merged output                   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 3: Formula Reconstruction (Depends on Tasks 2, 3, 4)  │
│  ──────────────────────────────────────────────────────────  │
│  • Task 5: In-Table Formula Fan-Out                          │
│  • Task 6: FSLI Extractor                                    │
│  • Task 7: Cross-Table Fan-Out                               │
│  • Task 8: Cross-Table Pipeline Wrapper                      │
│  Tasks 5, 6 can be done in parallel                          │
│  Task 7 depends on Task 6                                    │
│  Task 8 depends on Tasks 6, 7                                │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 4: Aggregation (Depends on Phase 3)                   │
│  ─────────────────────────────────────────                   │
│  • Task 9: Aggregator Agent                                  │
│  Test: mock formula state → execution → aggregated output    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 5: Integration (Depends on all above)                 │
│  ───────────────────────────────────────────                 │
│  • Task 10: Pipeline Orchestration                           │
│  • Task 11: Cleanup old code                                 │
│  Full end-to-end testing                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests (per task)

```python
# Task 1: Table Extraction
def test_extract_tables_from_markdown():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = extract_tables_from_markdown(md)
    assert len(result["tables"]) == 1
    assert result["tables"][0]["grid"] == [["A", "B"], ["1", "2"]]

# Task 3: Schemas
def test_reconstructed_formula_schema():
    in_table = ReconstructedFormula(
        check_type="in_table",
        table_index=0,
        target_cell=TargetCell(table_index=0, row=1, col=1),
        actual_value=100.0,
        inferred_formulas=[...]
    )
    assert in_table.check_type == "in_table"

# Task 4: Formula Engine
def test_evaluate_formula_with_tables():
    grids = {0: [["A", "B"], [10, 20], [30, 40]]}
    result = evaluate_formula_with_tables("sum_col(0, 1, 1, 2)", grids)
    assert result == 60.0  # 20 + 40

# Task 5: Intelligent Batching
def test_batch_tables_by_complexity():
    tables = [
        {"table_index": 0, "grid": [[1]*4]*25},  # Complex
        {"table_index": 1, "grid": [[1]*2]*3},   # Simple
        {"table_index": 2, "grid": [[1]*2]*4},   # Simple
    ]
    batches = batch_tables_by_complexity(tables)
    assert len(batches) == 2  # Complex alone, simples together
```

### Integration Tests (per phase)

```python
# Phase 2: Extraction → Naming
async def test_extraction_and_naming():
    state = {"document_content": sample_md}
    # Run extraction callback
    # Run table namer agent
    # Verify state["extracted_tables"] has names

# Phase 3: Formula Reconstruction
async def test_formula_reconstruction():
    state = {"extracted_tables": {...}}
    # Run in-table fan-out
    # Verify state["reconstructed_formulas"] has in_table entries

# Phase 5: Full Pipeline
async def test_full_pipeline():
    state = {"document_content": sample_financial_report}
    # Run numeric_validation_agent
    # Verify state["numeric_validation_output"]
```
