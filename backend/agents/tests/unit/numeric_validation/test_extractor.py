"""Unit tests for table_extraction.extractor.

All tests exercise the real markdown_table_extractor library — nothing is
mocked.  That is the point of this module: the extraction path must be
deterministic and hallucination-free end-to-end.
"""

from veritas_ai_agent.sub_agents.numeric_validation.table_extraction.extractor import (
    extract_tables_from_markdown,
    tables_to_json,
)

# ---------------------------------------------------------------------------
# Single-table basics
# ---------------------------------------------------------------------------


class TestSingleTable:
    MD = (
        "| Item | 2024 | 2023 |\n"
        "|------|------|------|\n"
        "| Cash | 1,000 | 800 |\n"
        "| Debt | (500) | (400) |\n"
        "| **Total** | 500 | 400 |\n"
    )

    def test_returns_one_table(self):
        assert len(extract_tables_from_markdown(self.MD)) == 1

    def test_table_index_is_zero(self):
        assert extract_tables_from_markdown(self.MD)[0]["table_index"] == 0

    def test_header_row_preserved(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        assert grid[0] == ["Item", "2024", "2023"]

    def test_numbers_parsed_to_float(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        assert grid[1] == ["Cash", 1000.0, 800.0]

    def test_accounting_negatives_parsed(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        assert grid[2] == ["Debt", -500.0, -400.0]

    def test_bold_label_preserved(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        # Bold markers survive; the label column has no digits so no parse attempt
        assert grid[3][0] == "**Total**"

    def test_output_keys(self):
        table = extract_tables_from_markdown(self.MD)[0]
        assert set(table.keys()) == {"table_index", "grid"}


# ---------------------------------------------------------------------------
# Multiple tables
# ---------------------------------------------------------------------------


class TestMultipleTables:
    MD = (
        "# Balance Sheet\n\n"
        "| Asset | Amount |\n"
        "|-------|--------|\n"
        "| Cash | 500 |\n"
        "\n"
        "Some narrative text between tables.\n\n"
        "# Note 3\n\n"
        "| Component | Value |\n"
        "|-----------|-------|\n"
        "| Bank A | 300 |\n"
        "| Bank B | 200 |\n"
    )

    def test_two_tables_extracted(self):
        assert len(extract_tables_from_markdown(self.MD)) == 2

    def test_indices_are_sequential(self):
        tables = extract_tables_from_markdown(self.MD)
        assert tables[0]["table_index"] == 0
        assert tables[1]["table_index"] == 1

    def test_first_table_content(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        assert grid[0] == ["Asset", "Amount"]
        assert grid[1] == ["Cash", 500.0]

    def test_second_table_content(self):
        grid = extract_tables_from_markdown(self.MD)[1]["grid"]
        assert grid[0] == ["Component", "Value"]
        assert grid[1] == ["Bank A", 300.0]
        assert grid[2] == ["Bank B", 200.0]


class TestBackToBackTables:
    """Two tables with only a blank line between them — no headers or text."""

    MD = "| A | B |\n|---|---|\n| 1 | 2 |\n\n| C | D |\n|---|---|\n| 3 | 4 |\n"

    def test_both_tables_extracted(self):
        tables = extract_tables_from_markdown(self.MD)
        assert len(tables) == 2

    def test_grids_are_independent(self):
        tables = extract_tables_from_markdown(self.MD)
        assert tables[0]["grid"][1] == [1.0, 2.0]
        assert tables[1]["grid"][1] == [3.0, 4.0]


# ---------------------------------------------------------------------------
# Number-format edge cases (end-to-end through number_parser)
# ---------------------------------------------------------------------------


class TestNumberFormats:
    def _single_grid(self, md: str) -> list[list]:
        return extract_tables_from_markdown(md)[0]["grid"]

    def test_currency_dollar(self):
        md = "| X |\n|---|\n| $1,250.50 |\n"
        assert self._single_grid(md)[1][0] == 1250.5

    def test_currency_euro(self):
        md = "| X |\n|---|\n| €800 |\n"
        assert self._single_grid(md)[1][0] == 800.0

    def test_percentage(self):
        md = "| X |\n|---|\n| 12.5% |\n"
        assert self._single_grid(md)[1][0] == 0.125

    def test_accounting_negative_with_currency(self):
        md = "| X |\n|---|\n| $(2,000) |\n"
        assert self._single_grid(md)[1][0] == -2000.0

    def test_eu_locale_detected_per_column(self):
        # Column has 1.234,56 and 2.000,00 → strong EU signal
        md = (
            "| Label | Amount |\n"
            "|-------|--------|\n"
            "| A | 1.234,56 |\n"
            "| B | 2.000,00 |\n"
        )
        grid = self._single_grid(md)
        assert grid[1][1] == 1234.56
        assert grid[2][1] == 2000.0

    def test_zero_value(self):
        md = "| X |\n|---|\n| 0 |\n"
        assert self._single_grid(md)[1][0] == 0.0

    def test_large_number(self):
        md = "| X |\n|---|\n| 1,234,567,890 |\n"
        assert self._single_grid(md)[1][0] == 1234567890.0


# ---------------------------------------------------------------------------
# Empty / missing cells
# ---------------------------------------------------------------------------


class TestEmptyCells:
    MD = "| A | B |\n|---|---|\n| 100 |   |\n|     | 200 |\n"

    def test_empty_cells_become_empty_string(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        # row 1: A=100, B=empty
        assert grid[1][0] == 100.0
        assert grid[1][1] == ""
        # row 2: A=empty, B=200
        assert grid[2][0] == ""
        assert grid[2][1] == 200.0


# ---------------------------------------------------------------------------
# Single-column table
# ---------------------------------------------------------------------------


class TestSingleColumnTable:
    MD = "| Values |\n|--------|\n| 10 |\n| 20 |\n| 30 |\n"

    def test_single_column_extracted(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        assert grid[0] == ["Values"]
        assert grid[1] == [10.0]
        assert grid[2] == [20.0]
        assert grid[3] == [30.0]


# ---------------------------------------------------------------------------
# No tables / empty input
# ---------------------------------------------------------------------------


class TestNoTables:
    def test_empty_string(self):
        assert extract_tables_from_markdown("") == []

    def test_plain_text_only(self):
        md = "# Heading\n\nJust a paragraph.\n\nAnother one.\n"
        assert extract_tables_from_markdown(md) == []

    def test_header_only_table_not_returned(self):
        # Library requires at least one data row
        md = "| A | B |\n|---|---|\n"
        assert extract_tables_from_markdown(md) == []


# ---------------------------------------------------------------------------
# tables_to_json envelope
# ---------------------------------------------------------------------------


class TestTablesToJson:
    def test_wraps_in_tables_key(self):
        raw = [{"table_index": 0, "grid": [["A"], [1.0]]}]
        assert tables_to_json(raw) == {"tables": raw}

    def test_empty_list(self):
        assert tables_to_json([]) == {"tables": []}

    def test_multiple_tables_preserved_in_order(self):
        raw = [
            {"table_index": 0, "grid": [["X"]]},
            {"table_index": 1, "grid": [["Y"]]},
        ]
        result = tables_to_json(raw)
        assert len(result["tables"]) == 2
        assert result["tables"][0]["table_index"] == 0
        assert result["tables"][1]["table_index"] == 1


# ---------------------------------------------------------------------------
# Realistic financial-statement snippet
# ---------------------------------------------------------------------------


class TestRealisticFinancialStatement:
    MD = (
        "# Statement of Financial Position\n"
        "*(in thousands USD)*\n\n"
        "| | 31 Dec 2024 | 31 Dec 2023 |\n"
        "|---|---|---|\n"
        "| **Current Assets** | | |\n"
        "| Cash and cash equivalents | 4,520 | 3,810 |\n"
        "| Trade receivables | 12,300 | 11,450 |\n"
        "| **Total current assets** | 16,820 | 15,260 |\n"
        "| **Non-current Assets** | | |\n"
        "| Property, plant & equipment | 28,100 | 27,500 |\n"
        "| **Total non-current assets** | 28,100 | 27,500 |\n"
        "| **TOTAL ASSETS** | 44,920 | 42,760 |\n"
    )

    def test_single_table_extracted(self):
        assert len(extract_tables_from_markdown(self.MD)) == 1

    def test_section_headers_are_labels(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        # "**Current Assets**" row — numeric columns are empty strings
        current_assets_row = grid[1]
        assert "Current Assets" in current_assets_row[0]
        assert current_assets_row[1] == ""
        assert current_assets_row[2] == ""

    def test_cash_row_parsed(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        cash_row = grid[2]  # Cash and cash equivalents
        assert cash_row[1] == 4520.0
        assert cash_row[2] == 3810.0

    def test_total_assets_parsed(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        total_row = grid[-1]  # TOTAL ASSETS
        assert total_row[1] == 44920.0
        assert total_row[2] == 42760.0

    def test_grid_dimensions(self):
        grid = extract_tables_from_markdown(self.MD)[0]["grid"]
        # 1 header + 8 data rows = 9 rows; 3 columns
        assert len(grid) == 9
        assert all(len(row) == 3 for row in grid)
