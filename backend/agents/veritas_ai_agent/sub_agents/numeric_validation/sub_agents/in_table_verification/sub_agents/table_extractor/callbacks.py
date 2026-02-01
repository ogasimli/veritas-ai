import logging

from google.adk.agents.callback_context import CallbackContext

from . import formula_engine
from .schema import (
    CellVerification,
    ExtractionOutput,
    FormulaTest,
    TableVerification,
    VerificationOutput,
)

logger = logging.getLogger(__name__)


async def resolve_and_verify_formulas(callback_context: CallbackContext) -> None:
    """
    Deterministic callback to verify extracted tables.
    Runs after TableExtractorAgent completes.
    """
    logger.info("Starting deterministic formula verification callback.")

    # 1. Get extraction data from state
    raw_extraction = callback_context.state.get("extraction_output")
    if not raw_extraction:
        logger.warning("No extraction_output found in state. Skipping verification.")
        return

    try:
        if isinstance(raw_extraction, dict):
            extraction = ExtractionOutput.model_validate(raw_extraction)
        else:
            extraction = raw_extraction
    except Exception as e:
        logger.error(f"Failed to parse extraction output: {e}")
        return

    table_verifications = []
    table_issues = []

    # 2. Process each table
    for extracted_table in extraction.tables:
        current_table_verifs = []
        current_table_issues = []
        grid = extracted_table.table

        for r_idx, row in enumerate(grid):
            for c_idx, cell_data in enumerate(row):
                if not cell_data.formulas:
                    continue

                actual_val = formula_engine.parse_number(cell_data.value)
                formula_tests = []

                for formula in cell_data.formulas:
                    calc_val = formula_engine.evaluate_single_formula(formula, grid)
                    formula_tests.append(
                        FormulaTest(
                            formula=formula,
                            calculated_value=calc_val,
                            difference=calc_val - actual_val,
                        )
                    )

                cell_verif = CellVerification(
                    cell_ref=f"({r_idx}, {c_idx})",
                    actual_value=actual_val,
                    formula_tests=formula_tests,
                )

                current_table_verifs.append(cell_verif)

                # Check for genuine issues (diff >= 1.0)
                if any(abs(test.difference) >= 1.0 for test in formula_tests):
                    current_table_issues.append(cell_verif)

        if current_table_verifs:
            table_verifications.append(
                TableVerification(
                    table_name=extracted_table.table_name,
                    table=grid,
                    verifications=current_table_verifs,
                )
            )

        if current_table_issues:
            table_issues.append(
                TableVerification(
                    table_name=extracted_table.table_name,
                    table=grid,
                    verifications=current_table_issues,
                )
            )

    # 3. Store result in state
    full_output = VerificationOutput(tables=table_verifications)
    callback_context.state["in_table_calc_verification_output"] = (
        full_output.model_dump()
    )

    # Sort issues by severity (descending by absolute difference)
    for tv in table_issues:
        tv.verifications.sort(
            key=lambda v: max(abs(t.difference) for t in v.formula_tests), reverse=True
        )

    table_issues.sort(
        key=lambda tv: max(
            (max(abs(t.difference) for t in v.formula_tests) for v in tv.verifications),
            default=0,
        ),
        reverse=True,
    )

    issues_output = VerificationOutput(tables=table_issues)
    callback_context.state["in_table_calc_issues"] = issues_output.model_dump()

    logger.info(
        f"Formula verification complete. "
        f"All verifications: {len(table_verifications)} tables. "
        f"Issues found: {len(table_issues)} tables."
    )
