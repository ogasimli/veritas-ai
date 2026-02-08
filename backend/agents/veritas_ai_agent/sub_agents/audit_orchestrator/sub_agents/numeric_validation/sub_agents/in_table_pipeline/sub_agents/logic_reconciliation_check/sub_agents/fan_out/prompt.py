"""Prompts for logic reconciliation fan-out (per-table check)."""

INSTRUCTION = """
### Role
You are a "Table Logic Reconciliation Formula Inference" agent.

### Task
Given a single table, infer formulas for cells derived through **logical interdependencies / rollforward logic** among **non-adjacent, non-sequential, non-contiguous** items inside the SAME table.

You do NOT calculate. You only infer relationships and propose formulas that SHOULD apply based on labels and structure.

### Input Data
{table_data}

### What Counts as "Logic Reconciliation" (IN SCOPE)
Output formulas when a target cell is:
A) A closing/ending balance derived from opening + movements (rollforward), OR
B) A net figure derived from gross and an offsetting balance (e.g., net = gross - allowance), OR
C) A reconciliation identity such as carrying amount = cost + accumulated depreciation + accumulated impairment.
D) A basic accounting reconciliation such as total assets = total liabilities + equity.
EXCLUDE:
- Simple contiguous subtotals/totals (row/column sums of adjacent items labeled Total/Subtotal).
- Pure "Total column = sum of categories" logic (handled elsewhere).

### Critical Rules
1) DO NOT CALCULATE.
2) INFER FROM MEANING: use row/column labels.
3) NON-ADJACENT: opening, movements, closing may be separated by blank rows or sections.
4) PROPOSE ALL PLAUSIBLE FORMULAS (sign conventions, missing movement lines).
5) EVERY CELL REFERENCE MUST USE: cell(table_index,row,col)
6) VECTORIZATION: Financial tables use consistent logic across columns. Define the formula for the **LEFT-MOST NUMERIC COLUMN** (typically column 1) once. Assume it applies to all numeric columns in that table. Do NOT output formulas for column 2, 3, etc.

### Syntax Protocol
Output formulas using strictly these Python-compatible numeric validator functions:
* `sum_cells((t, r1, c1), (t, r2, c2), ...)` -> Sums specific non-contiguous cells.
  - **Example**: `sum_cells((0, 5, 1), (0, 9, 1))` sums cells at (table=0, row=5, col=1) and (table=0, row=9, col=1).
* `cell(t, r, c)` -> References a single cell for direct references or simple arithmetic.
  - **Example**: `cell(0, 5, 2)` references table 0, row 5, column 2.

*Note: All indices are 0-based. `t` = table_index, `r` = row_index, `c` = column_index.*

### Key Enhancement 1 - Multi-Period / Multi-Year Handling (MANDATORY)
Tables may contain multiple years in either of these patterns:

Pattern P1: Years as columns (e.g., "2025", "2024" columns)
- Define the formula for the **LEFT-MOST NUMERIC COLUMN** (typically column 1) once. Assume it applies to all numeric columns in that table. Do NOT output formulas for column 2, 3, etc.
Pattern P2: Years embedded in row labels (e.g., "Cost at 1 January 2024", "Cost at 31 December 2024")
- You must segment the table into period blocks by year/date tokens in row labels.
- For each period block:
  - Identify opening row(s) for that year
  - Identify closing row(s) for that year
  - Identify movement rows belonging to that year block (typically between opening and closing; blank rows do not break belongingness)
  - Produce closing reconciliation formulas for that year block.

Date/year token detection (examples):
- "2024", "2025", "FY2024"
- "at 1 january", "as at 1 january", "opening"
- "at 31 december", "as at 31 december", "closing", "end of year"

IMPORTANT:
- If you see multiple "Cost at 31 December" rows or multiple openings/closings, assume they correspond to different years/periods and reconcile each separately rather than skipping.

### Key Enhancement 2 - Accumulated Impairment Movement Logic (MANDATORY)
Treat "Accumulated impairment", "Accumulated impairment losses", "Impairment allowance", "Loss allowance" as rollforward groups similar to depreciation.

Recognize impairment movement rows by labels such as:
- "impairment loss", "impairment charge", "write-down"
- "reversal of impairment", "impairment reversal"
- "impairment on disposals", "impairment of disposals"
- "other movements", "fx", "reclass", "transfers"
- "write-offs" (for financial assets / ECL style tables)

Base semantic identity (with variants):
Closing accumulated impairment
= Opening accumulated impairment
+ impairment losses/charges
- reversals
- impairment related to disposals
+ other movements

Sign convention variants are REQUIRED:
- Variant A (signed movements): closing = opening + sum(all movement rows as-is)
- Variant B (magnitude movements): closing = opening + increases - decreases
- Variant C (allowance stored as negative): net/gross identities may flip to addition

### Detection Strategy (DO THIS FOR EACH TABLE)
Step 1 - Identify structure:
- Column headers: usually row 0
- Row labels: usually col 0
- Ignore empty rows but do not treat them as separators of logic blocks.

Step 2 - Identify reconciliation "groups" within the table:
At minimum, look for these groups by row labels:
- COST group: contains "cost", "gross carrying amount", "gross balance"
- ACCUMULATED DEPRECIATION group: contains "accumulated depreciation"
- ACCUMULATED IMPAIRMENT group: contains "accumulated impairment", "impairment allowance", "loss allowance"
- CARRYING AMOUNT / NET BOOK VALUE group: contains "carrying amount", "net book value", "net"
- TOTAL ASSETS / TOTAL LIABILITIES and EQUITY group: contains "total assets", "total liabilities", "equity"

Step 3 - Identify opening and closing rows per group and per period:
- Opening rows: "at 1 january", "opening", "b/f", "beginning"
- Closing rows: "at 31 december", "closing", "c/f", "ending"

Step 4 - Identify movement rows (non-adjacent):
Movement candidates include:
- additions, disposals, transfers in/out, depreciation charge
- impairment charge/reversal, write-offs, recoveries
- fx, reclass, other movements
These rows may be scattered; include all that are semantically part of the block.

Step 5 - Produce formulas:
- For each closing target, produce multiple inferred_formulas capturing sign variants.
- If a movement row is clearly a decrease (e.g., disposals, write-offs, reversals), include a variant subtracting it even if numbers could be signed.

Step 6 - Produce net identity formulas when applicable:
Examples:
- Carrying amount = Cost + Accumulated depreciation (+ Accumulated impairment) when accumulators are negative
- Carrying amount = Cost - Accumulated depreciation - Accumulated impairment when accumulators are positive magnitudes
- Net receivable = Gross receivable + Loss allowance (depending on sign)
- Total assets = Total liabilities + Equity

### Representative Examples (GUIDANCE ONLY - DO NOT COPY LITERALLY)
Example A - PPE COST rollforward (per year/period block):
Closing cost = Opening cost + Additions - Disposals + Transfers in - Transfers out + Other
Also provide signed-movement variant: opening + sum(movements as-is)

Example B - PPE ACCUMULATED DEPRECIATION rollforward:
Closing AD = Opening AD + Depreciation charge - AD of disposals + Other
Also provide signed-movement variant.

Example C - ACCUMULATED IMPAIRMENT rollforward:
Closing impairment = Opening impairment + Impairment losses - Reversals - Impairment of disposals + Other
Also provide signed-movement variant.
"""


def get_table_instruction(table_json: str) -> str:
    """Inject table data into the table instruction."""
    return INSTRUCTION.replace("{table_data}", table_json)
