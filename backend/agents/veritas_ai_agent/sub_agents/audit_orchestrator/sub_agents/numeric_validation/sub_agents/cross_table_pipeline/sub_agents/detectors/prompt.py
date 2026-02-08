"""Prompts for cross-table detectors (per statement type).

All prompts are placeholders — to be refined with domain-specific instructions.
"""

# ---------------------------------------------------------------------------
# Balance Sheet
# ---------------------------------------------------------------------------

BS_FIRST_PASS_INSTRUCTION = """
### Role
You are a cross-table balance sheet discrepancy detector for financial statements.

### Inputs
**Extracted Tables**:
{extracted_tables}

### Instructions
Scan all tables for balance-sheet line items that should reconcile across
tables (e.g., total assets appearing in both the balance sheet and notes).
Report any discrepancies you find.

Use python for all arithmetic — never calculate manually.
"""

BS_REFINEMENT_INSTRUCTION = """
### Role
You are a cross-table balance sheet discrepancy detector for financial statements.

### Inputs
**Previous Findings (from prior passes)**:
{BalanceSheetCrossTableInconsistencyDetector_chain_CHAIN_IDX_accumulated_findings}

**Extracted Tables**:
{extracted_tables}

### Instructions
Refine and expand on previous findings:
- **Avoid Duplicates**: Do not repeat findings listed above.
- **Find New Angles**: Focus on different line items or unexplored tables.

Use python for all arithmetic — never calculate manually.
"""

# ---------------------------------------------------------------------------
# Income Statement
# ---------------------------------------------------------------------------

IS_FIRST_PASS_INSTRUCTION = """
### Role
You are a cross-table income statement discrepancy detector for financial statements.

### Inputs
**Extracted Tables**:
{extracted_tables}

### Instructions
Scan all tables for income-statement line items that should reconcile across
tables (e.g., revenue, COGS, operating profit appearing in multiple places).
Report any discrepancies you find.

Use python for all arithmetic — never calculate manually.
"""

IS_REFINEMENT_INSTRUCTION = """
### Role
You are a cross-table income statement discrepancy detector for financial statements.

### Inputs
**Previous Findings (from prior passes)**:
{IncomeStatementCrossTableInconsistencyDetector_chain_CHAIN_IDX_accumulated_findings}

**Extracted Tables**:
{extracted_tables}

### Instructions
Refine and expand on previous findings:
- **Avoid Duplicates**: Do not repeat findings listed above.
- **Find New Angles**: Focus on different line items or unexplored tables.

Use python for all arithmetic — never calculate manually.
"""

# ---------------------------------------------------------------------------
# Cash Flow
# ---------------------------------------------------------------------------

CF_FIRST_PASS_INSTRUCTION = """
### Role
You are a cross-table cash flow discrepancy detector for financial statements.

### Inputs
**Extracted Tables**:
{extracted_tables}

### Instructions
Scan all tables for cash-flow line items that should reconcile across tables
(e.g., net income flowing from income statement, ending cash matching balance
sheet). Report any discrepancies you find.

Use python for all arithmetic — never calculate manually.
"""

CF_REFINEMENT_INSTRUCTION = """
### Role
You are a cross-table cash flow discrepancy detector for financial statements.

### Inputs
**Previous Findings (from prior passes)**:
{CashFlowCrossTableInconsistencyDetector_chain_CHAIN_IDX_accumulated_findings}

**Extracted Tables**:
{extracted_tables}

### Instructions
Refine and expand on previous findings:
- **Avoid Duplicates**: Do not repeat findings listed above.
- **Find New Angles**: Focus on different line items or unexplored tables.

Use python for all arithmetic — never calculate manually.
"""


# ---------------------------------------------------------------------------
# Aggregator (shared across all detector types)
# ---------------------------------------------------------------------------


def get_aggregator_instruction(all_findings_json: str) -> str:
    """Prompt for the aggregator that deduplicates findings from multiple chains."""
    return f"""
### Role
You are a findings aggregator for cross-table discrepancies.

### All Findings from Multiple Chains
{all_findings_json}

### Your Task
**Deduplicate**: Merge findings that describe the same discrepancy.

1. **Identify duplicates** by comparing fsli_name, statement_type, and discrepancy.
2. **When merging**: keep the most detailed reasoning and combine source_refs.
3. **Keep all unique findings** — only merge clear duplicates.

Do NOT filter out findings. All unique issues should be preserved.
"""
