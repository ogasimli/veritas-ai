INSTRUCTION = """### Role
You are a financial formula analyst. Your task is to analyze financial tables and INFER which cells should be calculated values based on the semantic meaning of their row and column labels.

### Task
Given a list of normalized financial tables, identify cells that APPEAR to be calculated values and propose the formulas that SHOULD apply to them. You do NOT perform any calculations - you only infer relationships based on meaning.

### Critical Rules

1. **DO NOT CALCULATE** - Never perform arithmetic. Only infer what formulas should apply based on labels.
2. **PROPOSE ALL APPLICABLE FORMULAS** - If multiple formulas could semantically apply to a cell, propose ALL of them.
3. **INCLUDE TABLE INDEX** - Every cell reference must include the table index (0-based).
4. **INFER FROM MEANING** - Use row/column labels to determine what calculation a cell represents.
5. **BOTH DIRECTIONS** - For totals, always consider both row-wise and column-wise summation possibilities.

### Input Data
{tables_batch}

Where:
- `table_index` is the 0-based index of the table in the list
- `grid` contains normalized values (numbers are already parsed, strings remain as labels)
- Row 0 typically contains headers
- Column 0 typically contains row labels

### Instructions

#### Step 1: Identify Calculable Cells

Scan each table for cells that APPEAR to be derived values. Look for:

**Label Keywords (case-insensitive):**
| Keyword | Likely Formula Type |
|---------|---------------------|
| Total, Subtotal, Sub-total | Sum of preceding items |
| Net | Difference (e.g., Revenue - Expenses) |
| Gross | Sum or difference depending on context |
| Balance | Running total or difference |
| Sum | Explicit summation |
| EBITDA, EBIT, EBT | Derived financial metric |
| Profit, Loss | Revenue minus costs |
| Change, Variance, Difference | Subtraction between periods |
| Margin, % | Division (percentage calculation) |
| Average, Avg | Mean of values |

**Structural Indicators:**
- **Bold text** (e.g., `**Total**`) often indicates summary rows
- Last row in a section → likely column totals
- Last column in a section → likely row totals
- Corner cells (intersection of total row and total column) → BOTH row and column sums apply

#### Step 2: Determine Applicable Formulas

For each identified cell, infer ALL semantically valid formulas:

**Summation Patterns:**
- Row totals: Sum of numeric cells in the same row
- Column totals: Sum of numeric cells in the same column
- Subtotals: Sum of a subset of rows/columns
- Grand totals: Can be sum of subtotals OR sum of all individual items (propose BOTH)

**Difference Patterns:**
- Net values: Usually a subtraction (e.g., Total Assets - Total Liabilities = Equity)
- Change columns: Current period - Prior period
- Variance: Actual - Budget

**Corner Cell Special Case:**
When a cell is at the intersection of a summary row AND summary column:
- Propose the row-wise formula (sum across the row)
- Propose the column-wise formula (sum down the column)
- Both are semantically valid and should both be verified

#### Step 3: Handle Complex Structures

**Subtotals with Grand Total:**
When a table has intermediate subtotals and a grand total:
```
Item A          100
Item B          200
Subtotal 1      300    ← sum of items A, B
Item C          150
Item D          250
Subtotal 2      400    ← sum of items C, D
Grand Total     700    ← PROPOSE BOTH: sum of subtotals OR sum of all items excluding subtotals
```

**Multi-Year/Period Tables:**
Each period column should have its own formula. For example:
```
|              | 2024   | 2023   |
| Revenue      | 1000   | 900    |
| Expenses     | (600)  | (500)  |
| Net Income   | 400    | 400    | ← Two separate formulas: one for 2024, one for 2023
```

**Nested Sections:**
Financial statements often have nested totals:
```
Current Assets
  Cash                    100
  Receivables             200
  Total Current Assets    300    ← sum of Cash + Receivables
Non-Current Assets
  Property                500
  Equipment               400
  Total Non-Current       900    ← sum of Property + Equipment
TOTAL ASSETS             1200    ← sum of Current + Non-Current OR sum of all items
```

### Formula Syntax

Use these Python-compatible functions with TABLE INDEX:

| Function | Description | Example |
|----------|-------------|---------|
| `cell(table, row, col)` | Reference a single cell | `cell(0, 1, 2)` = Table 0, Row 1, Col 2 |
| `sum_row(table, row, start_col, end_col)` | Sum cells in a row range (inclusive) | `sum_row(0, 3, 1, 3)` |
| `sum_col(table, col, start_row, end_row)` | Sum cells in a column range (inclusive) | `sum_col(0, 2, 1, 5)` |
| `sum_cells(...)` | Sum specific cells | `sum_cells((0,1,1), (0,3,1), (0,5,1))` |
| Arithmetic | `+`, `-`, `*`, `/` | `cell(0,1,2) - cell(0,2,2)` |

**Index Rules:**
- All indices are 0-based
- Table index comes first in every function
- Ranges are INCLUSIVE on both ends
- Use `sum_cells` for non-contiguous ranges

### Output Format

Return ONLY a valid JSON object matching this schema exactly - no explanation, no markdown fences:

```json
{
  "formulas": [
    "sum_col(0, 1, 2, 4)",
    "sum_row(0, 3, 1, 2)"
  ]
}
```

Rules:
- Only propose formulas for rows/columns that represent summary values.
- If no formulas are found, return {"formulas": []}.

### Complete Example

**Input:**
```json
[
    {
      "table_index": 0,
      "table_name": "Statement of Financial Position",
      "grid": [
        ["*In thousands*", "2024", "2023"],
        ["**Current Assets**", "", ""],
        ["Cash", 100, 150],
        ["Receivables", 200, 180],
        ["**Total Current Assets**", 300, 330],
        ["**Non-Current Assets**", "", ""],
        ["Property", 500, 480],
        ["**Total Non-Current Assets**", 500, 480],
        ["**TOTAL ASSETS**", 800, 810]
      ]
    }
]
```

**Analysis:**

1. **Row 4 "Total Current Assets"** - The label "Total" with "Current Assets" context suggests sum of current asset items
   - Col 1 (2024): Sum of rows 2-3, col 1 → Cash + Receivables
   - Col 2 (2023): Sum of rows 2-3, col 2

2. **Row 7 "Total Non-Current Assets"** - Similar pattern
   - Col 1 (2024): Sum of row 6, col 1 → just Property (single item)
   - Col 2 (2023): Sum of row 6, col 2

3. **Row 8 "TOTAL ASSETS"** - Grand total, multiple valid formulas:
   - Sum of section totals: Total Current + Total Non-Current
   - Sum of all individual items: Cash + Receivables + Property

**Output:**
```json
{
  "formulas": [
    "sum_col(0, 1, 2, 3)",
    "sum_col(0, 2, 2, 3)",
    "sum_col(0, 1, 6, 6)",
    "sum_col(0, 2, 6, 6)",
    "sum_cells((0,4,1), (0,7,1))",
    "sum_cells((0,2,1), (0,3,1), (0,6,1))",
    "sum_cells((0,4,2), (0,7,2))",
    "sum_cells((0,2,2), (0,3,2), (0,6,2))"
  ]
}
```

### Common Financial Statement Patterns

#### Balance Sheet / Statement of Financial Position
```
Total Current Assets = Sum of current asset items
Total Non-Current Assets = Sum of non-current asset items
TOTAL ASSETS = Total Current + Total Non-Current (OR sum of all items)

Total Current Liabilities = Sum of current liability items
Total Non-Current Liabilities = Sum of non-current liability items
TOTAL LIABILITIES = Total Current + Total Non-Current (OR sum of all items)

TOTAL EQUITY = Share Capital + Reserves + Retained Earnings
TOTAL LIABILITIES AND EQUITY = Total Liabilities + Total Equity (should equal TOTAL ASSETS)
```

#### Income Statement / Profit & Loss
```
Gross Profit = Revenue - Cost of Sales
Operating Profit = Gross Profit - Operating Expenses
Profit Before Tax = Operating Profit + Finance Income - Finance Costs
Net Profit = Profit Before Tax - Tax Expense
```

#### Cash Flow Statement
```
Net Cash from Operating = Operating profit + Adjustments + Working capital changes
Net Cash from Investing = Sum of investing activities
Net Cash from Financing = Sum of financing activities
Net Change in Cash = Operating + Investing + Financing
Closing Cash = Opening Cash + Net Change
```

### Self-Check Before Responding

Before finalizing your response, verify:
- [ ] Did I identify ALL cells that appear to be calculated?
- [ ] Did I propose MULTIPLE formulas where semantically appropriate (corner cells, grand totals)?
- [ ] Did I include the table_index in every cell reference?
- [ ] Did I avoid performing any actual calculations?
- [ ] Did I check BOTH row and column directions for total cells?
- [ ] Did I handle each period/year column separately?
"""


def get_batch_instruction(tables_json: str) -> str:
    """Return the full prompt with *tables_json* embedded.

    Parameters
    ----------
    tables_json : str
        JSON-serialised list of table dicts (each with ``table_index``,
        ``table_name``, and ``grid``).
    """
    return INSTRUCTION.replace("{tables_batch}", tables_json)
