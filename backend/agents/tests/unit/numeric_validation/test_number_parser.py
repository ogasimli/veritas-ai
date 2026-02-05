"""Unit tests for table_extraction.number_parser."""

import pandas as pd

from veritas_ai_agent.sub_agents.numeric_validation.table_extraction.number_parser import (
    detect_locale,
    parse_cell_value,
    process_dataframe,
)

# ---------------------------------------------------------------------------
# detect_locale
# ---------------------------------------------------------------------------


class TestDetectLocale:
    # --- unambiguous US signals -------------------------------------------
    def test_us_comma_thousands_dot_decimal(self):
        assert detect_locale(["1,234.56", "2,000.00"]) == "en_US"

    def test_us_multiple_commas(self):
        # 1,234,567 → commas are clearly thousands (US)
        assert detect_locale(["1,234,567"]) == "en_US"

    # --- unambiguous EU signals -------------------------------------------
    def test_eu_dot_thousands_comma_decimal(self):
        assert detect_locale(["1.234,56", "2.000,00"]) == "de_DE"

    def test_eu_multiple_dots(self):
        # 1.234.567 → dots are clearly thousands (EU)
        assert detect_locale(["1.234.567"]) == "de_DE"

    def test_eu_short_comma_decimal(self):
        # 1,5  →  fractional part != 3 digits  →  decimal comma
        assert detect_locale(["1,5", "2,75"]) == "de_DE"

    # --- fallback / ambiguous ----------------------------------------------
    def test_no_separators_falls_back_to_us(self):
        assert detect_locale(["100", "200", "3000"]) == "en_US"

    def test_empty_list_falls_back_to_us(self):
        assert detect_locale([]) == "en_US"

    def test_non_numeric_strings_ignored(self):
        # Only "1,234.56" is scoreable; the rest have no digits
        assert detect_locale(["hello", "world", "1,234.56"]) == "en_US"

    def test_ambiguous_1_234_no_strong_signal_falls_back_to_us(self):
        # "1,234" → 3 digits after comma → ambiguous, no score added
        assert detect_locale(["1,234"]) == "en_US"

    # --- mixed signals (majority wins) ------------------------------------
    def test_majority_us_wins(self):
        vals = ["1,234.56", "2,000.00", "1.234,56"]  # 2 US vs 1 EU
        assert detect_locale(vals) == "en_US"

    def test_majority_eu_wins(self):
        vals = ["1.234,56", "2.000,00", "1,234.56"]  # 2 EU vs 1 US
        assert detect_locale(vals) == "de_DE"


# ---------------------------------------------------------------------------
# parse_cell_value
# ---------------------------------------------------------------------------


class TestParseCellValue:
    # --- plain numbers -----------------------------------------------------
    def test_integer(self):
        assert parse_cell_value("42", "en_US") == 42.0

    def test_float(self):
        assert parse_cell_value("3.14", "en_US") == 3.14

    # --- thousands separators ----------------------------------------------
    def test_us_thousands(self):
        assert parse_cell_value("1,234,567", "en_US") == 1234567.0

    def test_eu_thousands(self):
        assert parse_cell_value("1.234.567", "de_DE") == 1234567.0

    # --- decimal separators ------------------------------------------------
    def test_us_decimal(self):
        assert parse_cell_value("1234.56", "en_US") == 1234.56

    def test_eu_decimal(self):
        assert parse_cell_value("1234,56", "de_DE") == 1234.56

    def test_eu_thousands_and_decimal(self):
        assert parse_cell_value("1.234,56", "de_DE") == 1234.56

    # --- accounting negative -----------------------------------------------
    def test_parentheses_negative_us(self):
        assert parse_cell_value("(1,500)", "en_US") == -1500.0

    def test_parentheses_negative_plain(self):
        assert parse_cell_value("(42)", "en_US") == -42.0

    def test_parentheses_negative_eu(self):
        assert parse_cell_value("(1.500,00)", "de_DE") == -1500.0

    # --- percentages -------------------------------------------------------
    def test_percentage_whole(self):
        assert parse_cell_value("50%", "en_US") == 0.5

    def test_percentage_fractional(self):
        assert parse_cell_value("12.5%", "en_US") == 0.125

    def test_percentage_zero(self):
        assert parse_cell_value("0%", "en_US") == 0.0

    # --- currency symbols --------------------------------------------------
    def test_dollar_sign(self):
        assert parse_cell_value("$2,400.50", "en_US") == 2400.5

    def test_euro_sign(self):
        assert parse_cell_value("€1.200,00", "de_DE") == 1200.0

    def test_pound_sign(self):
        assert parse_cell_value("£999", "en_US") == 999.0

    # --- combined edge cases -----------------------------------------------
    def test_percentage_inside_parens_not_parsed(self):
        # "%" must be the final character to trigger percentage logic;
        # "(50%)" ends with ")" so it falls back to a label string.
        # This combination does not appear in real financial statements.
        assert parse_cell_value("(50%)", "en_US") == "(50%)"

    def test_dollar_negative(self):
        assert parse_cell_value("$(1,000)", "en_US") == -1000.0

    # --- non-numeric / label strings ---------------------------------------
    def test_label_returned_as_string(self):
        assert (
            parse_cell_value("Cash and equivalents", "en_US") == "Cash and equivalents"
        )

    def test_empty_string(self):
        assert parse_cell_value("", "en_US") == ""

    def test_dash_only(self):
        # Common placeholder for zero / N/A
        assert parse_cell_value("-", "en_US") == "-"

    def test_markdown_bold_label(self):
        assert parse_cell_value("**Total**", "en_US") == "**Total**"

    # --- markdown bold around numbers --------------------------------------
    def test_bold_number(self):
        assert parse_cell_value("**1,500**", "en_US") == 1500.0

    # --- whitespace & nbsp -------------------------------------------------
    def test_nbsp_in_value(self):
        # \u00a0 (non-breaking space) should be normalised
        assert parse_cell_value("\u00a0500\u00a0", "en_US") == 500.0

    def test_leading_trailing_spaces(self):
        assert parse_cell_value("  1,234.56  ", "en_US") == 1234.56


# ---------------------------------------------------------------------------
# process_dataframe  (integration: locale detection → parsing → 2-D list)
# ---------------------------------------------------------------------------


class TestProcessDataframe:
    def _make_df(self, headers, rows):
        return pd.DataFrame(rows, columns=headers)

    def test_basic_us_table(self):
        df = self._make_df(
            ["Item", "2024", "2023"],
            [
                ["Cash", "1,000", "800"],
                ["Debt", "(500)", "(400)"],
                ["Total", "500", "400"],
            ],
        )
        result = process_dataframe(df, locale="en_US")

        # Header row preserved
        assert result[0] == ["Item", "2024", "2023"]
        # Numbers parsed
        assert result[1] == ["Cash", 1000.0, 800.0]
        assert result[2] == ["Debt", -500.0, -400.0]
        assert result[3] == ["Total", 500.0, 400.0]

    def test_eu_locale_table(self):
        df = self._make_df(
            ["Artikel", "Betrag"],
            [
                ["Umsatz", "1.234,56"],
                ["Kosten", "789,00"],
            ],
        )
        result = process_dataframe(df, locale="de_DE")
        assert result[1] == ["Umsatz", 1234.56]
        assert result[2] == ["Kosten", 789.0]

    def test_column_with_no_numbers_stays_text(self):
        df = self._make_df(
            ["Name", "Category"],
            [["Alice", "A"], ["Bob", "B"]],
        )
        result = process_dataframe(df, locale="en_US")
        assert result[1] == ["Alice", "A"]
        assert result[2] == ["Bob", "B"]

    def test_mixed_column_numeric_and_label(self):
        # Column 1 has numbers and one label ("N/A")
        df = self._make_df(
            ["Item", "Value"],
            [["A", "100"], ["B", "N/A"], ["C", "300"]],
        )
        result = process_dataframe(df, locale="en_US")
        assert result[1][1] == 100.0
        assert result[2][1] == "N/A"
        assert result[3][1] == 300.0

    def test_percentage_column(self):
        df = self._make_df(
            ["Metric", "Rate"],
            [["Growth", "12.5%"], ["Margin", "8.0%"]],
        )
        result = process_dataframe(df, locale="en_US")
        assert result[1][1] == 0.125
        assert result[2][1] == 0.08

    def test_empty_dataframe(self):
        df = self._make_df(["A", "B"], [])
        result = process_dataframe(df, locale="en_US")
        # Only the header row
        assert result == [["A", "B"]]

    def test_single_row(self):
        df = self._make_df(["X"], [["42"]])
        result = process_dataframe(df, locale="en_US")
        assert result == [["X"], [42.0]]

    def test_nbsp_in_header(self):
        df = self._make_df(["Col\u00a0A", "Col B"], [["1", "2"]])
        result = process_dataframe(df, locale="en_US")
        assert result[0] == ["Col A", "Col B"]

    def test_duplicate_headers_parsed_correctly(self):
        # Reproduces the original bug where duplicate empty logic caused columns to be skipped.
        # Headers: ["", "Unique", ""]
        df = self._make_df(
            ["", "Unique", ""],
            [
                ["1,000", "A", "2,000"],
                ["(500)", "B", "(400)"],
            ],
        )
        # Duplicate columns must be accessible and parsed
        result = process_dataframe(df, locale="en_US")

        # Header row
        assert result[0] == ["", "Unique", ""]
        # Data rows
        # Col 0: "1,000" -> 1000.0
        # Col 1: "A"     -> "A"
        # Col 2: "2,000" -> 2000.0
        assert result[1] == [1000.0, "A", 2000.0]
        assert result[2] == [-500.0, "B", -400.0]
