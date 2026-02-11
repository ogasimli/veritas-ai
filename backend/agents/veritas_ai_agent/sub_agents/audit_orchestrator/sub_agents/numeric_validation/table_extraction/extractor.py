"""
Programmatic markdown table extraction.

Uses the markdown_table_extractor library so that cell values are copied
verbatim from the source — no LLM involved, no hallucination risk.
Number parsing (locale detection, accounting negatives, etc.) is handled
by number_parser.process_dataframe before the grid is returned.
"""

import logging

import pandas as pd
from markdown_table_extractor import TableMergeStrategy, extract_markdown_tables

from .number_parser import detect_locale, process_dataframe

logger = logging.getLogger(__name__)


def extract_tables_from_markdown(markdown_content: str) -> list[dict]:
    """
    Extract all markdown tables and return them as parsed grids.

    Each entry contains:
        table_index  - 0-based position in document order
        grid         - 2-D list; numbers are floats, labels are strings

    Table *names* are intentionally NOT assigned here; that is the job of
    the TableNamer LLM agent in the next pipeline stage.
    """
    result = extract_markdown_tables(
        markdown_content,
        merge_strategy=TableMergeStrategy.NONE,
        skip_sub_headers=False,
    )

    dfs = list(result.get_dataframes())

    # 1. Collect all numeric-looking samples from the entire document
    all_samples = []
    for df in dfs:
        for i in range(len(df.columns)):
            series = df.iloc[:, i]
            # Fast collection of non-na strings with digits
            col_samples = [
                str(x)
                for x in series
                if pd.notna(x) and any(c.isdigit() for c in str(x))
            ]
            all_samples.extend(col_samples)

    # 2. Detect global locale once
    global_locale = "en_US"
    if all_samples:
        global_locale = detect_locale(all_samples)
        logger.info("Detected document-wide locale: %s", global_locale)

    tables: list[dict] = []
    for idx, df in enumerate(dfs):
        # 3. Pass global locale to parser
        tables.append(
            {
                "table_index": idx,
                "grid": process_dataframe(df, locale=global_locale),
            }
        )

    logger.info("Extracted %d tables programmatically", len(tables))
    return tables


def tables_to_json(tables: list[dict]) -> dict:
    """Wrap the tables list in the envelope expected by downstream state."""
    return {"tables": tables}
