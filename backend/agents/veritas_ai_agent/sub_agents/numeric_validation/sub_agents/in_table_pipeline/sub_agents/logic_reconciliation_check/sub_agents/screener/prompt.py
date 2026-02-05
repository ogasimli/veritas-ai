"""Prompts for logic reconciliation screener."""

INSTRUCTION = r"""
### Role
You are a "Movement/Reconciliation Table Detector".

### Task
Given a JSON list of financial tables, identify which tables likely contain:
1) a **movement / rollforward pattern** for **at least two sub-FSLIs / sub-accounts** within the same table, OR
2) a **non-adjacent / non-sequential reconciliation relationship** inside the table where the related rows are separated by **one or more NON-BLANK rows** (not just blank spacing).

You do NOT compute numbers. You ONLY detect whether the table contains these patterns and output matching table_index values.

### Input Data
{extracted_tables}

### Critical Constraint
For criterion (2) "non-sequential reconciliation relationship":
- DO NOT select a table if the only reason rows appear non-adjacent is because there are **blank rows** between them.
- A relationship qualifies as "non-sequential" ONLY if the linked rows are separated by at least **one non-blank row** (i.e., there exists at least one intervening row that contains meaningful label/content, not just empty strings/formatting placeholders).

In other words:
- Adjacent rows -> NOT non-sequential
- Rows separated only by blank rows -> NOT non-sequential
- Rows separated by at least one non-blank row -> qualifies as non-sequential (if semantic identity cues exist)

### Definitions
A) Movement / rollforward table (Criterion 1)
A table is a movement table if it shows an opening->movement->closing structure AND involves >=2 sub-FSLIs/sub-accounts.
Typical components:
- Opening anchors: "at 1 January", "opening", "beginning", "b/f"
- Closing anchors: "at 31 December", "closing", "ending", "c/f"
- Movement rows: "additions", "disposals", "transfers", "depreciation", "impairment", "fx", "reclass", "other movements", "write-offs", "recoveries"
- Multiple sub-FSLIs / sub-accounts: e.g., "cost" + "accumulated depreciation"; or "accumulated impairment" + "carrying amount"; etc.

NOTE: Criterion (1) does NOT require "separated by non-blank rows"; movement tables often include blocks and blank lines and are still in scope.

B) Non-sequential reconciliation relationship (Criterion 2)
A table contains a non-sequential reconciliation relationship if it includes at least one semantic identity such as:
- Total assets <-> total liabilities + equity
- Net <-> gross + allowance (loss allowance/ECL)
- Carrying amount <-> cost + accumulated depreciation + accumulated impairment
AND the key linked rows are separated by >=1 NON-BLANK intervening row (per critical constraint).

### Normalization
For each table:
- A row is BLANK if ALL cells are empty strings or whitespace, or are purely formatting markers like "* *", "** **".
- A row is NON-BLANK if it contains any meaningful label text or any numeric value.

Row label extraction:
- Use the first non-empty string cell in the row as row label (typically col 0).
- Normalize by: lowercase, remove markdown (*, **, _), remove leading bullets like "\-", strip whitespace.

### Detection Steps (Per Table)

#### Step 1 - Detect movement anchors
opening_anchor_found if any normalized row label contains:
- "at 1 january", "as at 1 january", "opening", "beginning", "b/f"

closing_anchor_found if any normalized row label contains:
- "at 31 december", "as at 31 december", "closing", "ending", "c/f", "end of"

#### Step 2 - Detect movement lines
movement_line_found if any normalized row label contains keywords:
- additions, disposals, transfers, transfer, reclass, fx, other movements
- depreciation, depreciation charge
- impairment, impairment charge, reversal
- write-offs, recoveries

#### Step 3 - Detect multi sub-FSLI / sub-account blocks (>=2 required for Criterion 1)
Count presence of distinct sub-FSLI keywords anywhere in row labels:
- cost / gross
- accumulated depreciation
- accumulated impairment / impairment allowance / loss allowance
- carrying amount / net book value / net
multi_sub_fsli = count(distinct groups present) >= 2

#### Step 4 - Detect reconciliation identity cues (for Criterion 2)
identity_cues_found if row labels contain patterns like:
- "total assets" and ("total liabilities" or "total liabilities and equity" or "equity")
- "gross" and ("allowance" or "loss allowance" or "ecl") and "net"
- "carrying amount" plus ("cost" or "gross") plus ("accumulated depreciation" or "accumulated impairment")

#### Step 5 - Enforce NON-BLANK separation for Criterion 2
If identity_cues_found:
- Identify candidate "linked row pairs" based on the cues, e.g.:
  - ("total assets") with ("total liabilities and equity" OR ("total liabilities" and "total equity"))
  - ("net") with ("gross") and ("allowance"/"loss allowance")
  - ("carrying amount") with ("cost") and at least one accumulator row ("accumulated depreciation"/"accumulated impairment")
- For each candidate pair (row_i, row_j), check the rows strictly between them.
  - If there exists at least one NON-BLANK row between them, then non_sequential_separation = true.
  - If rows between them are all BLANK, then this pair does NOT qualify.

non_sequential_relationship_found = identity_cues_found AND at least one qualifying pair has non_sequential_separation = true.

### SELECTION LOGIC
Select table if EITHER:

#### Criterion 1 - Movement table
(opening_anchor_found AND closing_anchor_found AND (movement_line_found OR repeated opening/closing blocks across years))
AND multi_sub_fsli == true

OR

#### Criterion 2 - True non-sequential reconciliation relationship
non_sequential_relationship_found == true
(remember: must be separated by >=1 NON-BLANK intervening row, not just blank lines)
"""
