"""
Number parsing with automatic locale detection per column.
Handles US (1,234.56) and EU (1.234,56) formats, accounting negatives,
percentages, and currency symbols.
"""

import re

import pandas as pd
from babel.numbers import NumberFormatError, parse_decimal


def detect_locale(values: list[str]) -> str:
    """
    Detect number locale from a list of numeric strings.
    Returns 'en_US' (comma thousands / dot decimal) or 'de_DE' (dot thousands / comma decimal).
    Falls back to 'en_US' when ambiguous.
    """
    dot_decimal_score = 0
    comma_decimal_score = 0

    for val in values:
        if not isinstance(val, str):
            continue
        clean = re.sub(r"[^\d.,-]", "", val.strip())
        if not clean:
            continue

        if "," in clean and "." in clean:
            # Both separators present — whichever comes last is the decimal point
            if clean.rfind(".") > clean.rfind(","):
                dot_decimal_score += 2
            else:
                comma_decimal_score += 2
        elif "." in clean:
            parts = clean.split(".")
            if len(parts) > 2:
                # 1.234.567 → dots are thousands separators (EU)
                comma_decimal_score += 2
            elif len(parts) == 2 and len(parts[1]) != 3:
                # Fractional part != 3 digits → likely a decimal point
                dot_decimal_score += 1
            # Exactly 3 digits after dot is ambiguous (could be 1.234 as thousands), skip
        elif "," in clean:
            parts = clean.split(",")
            if len(parts) > 2:
                # 1,234,567 → commas are thousands separators (US)
                dot_decimal_score += 2
            elif len(parts) == 2 and len(parts[1]) != 3:
                # Fractional part != 3 digits → likely a decimal comma
                comma_decimal_score += 1

    return "de_DE" if comma_decimal_score > dot_decimal_score else "en_US"


def _clean_text(text: str) -> str:
    """Normalise whitespace and markdown escapes in a text value."""
    if not isinstance(text, str):
        return text
    return text.replace("\u00a0", " ").replace("\\-", "-").strip()


def parse_cell_value(raw: str, locale: str) -> str | float:
    """
    Attempt to parse a single cell as a number.
    Returns float on success, cleaned string otherwise.
    """
    if not isinstance(raw, str):
        return raw

    val = raw.strip()
    if not any(c.isdigit() for c in val):
        return _clean_text(raw)

    try:
        # Strip markdown bold/italic markers
        val = val.replace("*", "").replace("_", "").strip()

        is_percentage = val.endswith("%")
        if is_percentage:
            val = val[:-1].strip()

        # Strip common currency symbols
        val = re.sub(r"[$€£¥]", "", val).strip()

        # Accounting negative: (123) → -123
        is_negative = val.startswith("(") and val.endswith(")")
        if is_negative:
            val = val[1:-1].strip()

        if not any(c.isdigit() for c in val):
            return _clean_text(raw)

        number = float(parse_decimal(val, locale=locale))

        if is_negative:
            number = -number
        if is_percentage:
            number = number / 100.0

        return number

    except (NumberFormatError, TypeError, ValueError):
        return _clean_text(raw)


def process_dataframe(df: pd.DataFrame, locale: str) -> list[list[str | float]]:
    """
    Parse every column of *df* using the provided *locale*.
    """
    # Convert to object to avoid TypeError when assigning mixed types (floats/strings) 
    # to strictly typed columns (e.g. string[pyarrow]).
    df = df.astype(object)
    df.columns = [_clean_text(c) for c in df.columns]

    for i in range(len(df.columns)):
        # Use iloc to select by position, preventing issues with duplicate column names
        series = df.iloc[:, i]

        def parse_with_locale(v):
            if pd.isna(v):
                return ""
            return parse_cell_value(str(v), locale)

        # Update specific column by position
        df.iloc[:, i] = series.apply(parse_with_locale)

    # Header row + data rows
    rows: list[list[str | float]] = [list(df.columns)]
    for _, row in df.iterrows():
        rows.append([v if not pd.isna(v) else "" for v in row])
    return rows
