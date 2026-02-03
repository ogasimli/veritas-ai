"""
Programmatic markdown table extraction.

Uses the markdown_table_extractor library so that cell values are copied
verbatim from the source — no LLM involved, no hallucination risk.
Number parsing (locale detection, accounting negatives, etc.) is handled
by number_parser.process_dataframe before the grid is returned.
"""

import logging

from markdown_table_extractor import TableMergeStrategy, extract_markdown_tables

from .number_parser import process_dataframe

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

    tables: list[dict] = []
    for idx, df in enumerate(result.get_dataframes()):
        tables.append(
            {
                "table_index": idx,
                "grid": process_dataframe(df),
            }
        )

    logger.info("Extracted %d tables programmatically", len(tables))
    return tables


def tables_to_json(tables: list[dict]) -> dict:
    """Wrap the tables list in the envelope expected by downstream state."""
    return {"tables": tables}
