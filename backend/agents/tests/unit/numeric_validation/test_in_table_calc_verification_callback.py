from unittest.mock import MagicMock

import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_verification.sub_agents.table_extractor.callbacks import (
    resolve_and_verify_formulas,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_verification.sub_agents.table_extractor.schema import (
    CellData,
    ExtractedTable,
    ExtractionOutput,
    VerificationOutput,
)


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_success():
    # Setup mock context
    grid = [
        [CellData(value="100", formulas=[]), CellData(value="200", formulas=[])],
        [
            CellData(value="300", formulas=["cell(0,0) + cell(0,1)"]),
            CellData(value="400", formulas=["cell(1,0) + 100"]),
        ],
    ]
    extraction_output = ExtractionOutput(
        tables=[ExtractedTable(table_name="Test Table", table=grid)]
    )

    callback_context = MagicMock()
    # Use a real dict for state to test mutations
    state = {"extraction_output": extraction_output}
    callback_context.state = state

    # Execute
    await resolve_and_verify_formulas(callback_context)

    # Verify
    assert "in_table_calc_verification_output" in state
    assert "in_table_calc_issues" in state

    # 1. Check full output
    full_val = VerificationOutput.model_validate(
        state["in_table_calc_verification_output"]
    )
    issues_val = VerificationOutput.model_validate(state["in_table_calc_issues"])

    assert len(full_val.tables) == 1
    table_ver = full_val.tables[0]
    assert table_ver.table_name == "Test Table"
    assert len(table_ver.verifications) == 2

    # Cell (1, 0)
    ver1 = next(v for v in table_ver.verifications if v.cell_ref == "(1, 0)")
    assert ver1.actual_value == 300.0
    assert ver1.formula_tests[0].calculated_value == 300.0
    assert ver1.formula_tests[0].difference == 0.0

    # Cell (1, 1)
    ver2 = next(v for v in table_ver.verifications if v.cell_ref == "(1, 1)")
    assert ver2.actual_value == 400.0
    assert ver2.formula_tests[0].calculated_value == 400.0
    assert ver2.formula_tests[0].difference == 0.0

    # 2. Check issues output (should be empty because all match)
    assert len(issues_val.tables) == 0


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_with_issues():
    # One cell matches, one doesn't
    grid = [
        [CellData(value="100", formulas=[]), CellData(value="200", formulas=[])],
        [
            CellData(value="300", formulas=["cell(0,0) + cell(0,1)"]),
            CellData(value="500", formulas=["cell(1,0) + 100"]),
        ],
    ]
    extraction_output = ExtractionOutput(
        tables=[ExtractedTable(table_name="Issue Table", table=grid)]
    )

    callback_context = MagicMock()
    state = {"extraction_output": extraction_output}
    callback_context.state = state

    await resolve_and_verify_formulas(callback_context)

    issues_val = VerificationOutput.model_validate(state["in_table_calc_issues"])
    assert len(issues_val.tables) == 1
    table_issue = issues_val.tables[0]
    assert len(table_issue.verifications) == 1  # Only the 500 one
    assert table_issue.verifications[0].cell_ref == "(1, 1)"
    # Expected 300+100=400, Actual 500. Diff = -100
    assert table_issue.verifications[0].formula_tests[0].difference == -100.0


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_rounding_and_formatting():
    # Test parentheses as negative and currency
    grid = [
        [
            CellData(value="$ (500.00)", formulas=[]),
            CellData(value="1,000.50", formulas=[]),
        ],
        [CellData(value="500.50", formulas=["cell(0,0) + cell(0,1)"])],
    ]
    extraction_output = ExtractionOutput(
        tables=[ExtractedTable(table_name="Format Table", table=grid)]
    )

    callback_context = MagicMock()
    state = {"extraction_output": extraction_output}
    callback_context.state = state

    await resolve_and_verify_formulas(callback_context)

    full_val = VerificationOutput.model_validate(
        state["in_table_calc_verification_output"]
    )
    ver = full_val.tables[0].verifications[0]

    # ( -500.00 + 1000.50 ) = 500.50
    assert ver.actual_value == 500.50
    assert ver.formula_tests[0].calculated_value == 500.50


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_invalid_formula():
    grid = [[CellData(value="100", formulas=["invalid_func(1)"])]]
    extraction_output = ExtractionOutput(
        tables=[ExtractedTable(table_name="Error Table", table=grid)]
    )

    callback_context = MagicMock()
    state = {"extraction_output": extraction_output}
    callback_context.state = state

    await resolve_and_verify_formulas(callback_context)

    issues_val = VerificationOutput.model_validate(state["in_table_calc_issues"])
    ver = issues_val.tables[0].verifications[0]

    # invalid_func(1) -> 0.0. Actual 100. Diff = -100. Thus it is an issue.
    assert ver.formula_tests[0].calculated_value == 0.0
    assert abs(ver.formula_tests[0].difference) >= 1.0


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_empty_logic():
    # No extraction data
    callback_context = MagicMock()
    state = {}
    callback_context.state = state
    await resolve_and_verify_formulas(callback_context)
    assert "in_table_calc_verification_output" not in state

    # Empty tables list
    state = {"extraction_output": ExtractionOutput(tables=[])}
    callback_context.state = state
    await resolve_and_verify_formulas(callback_context)
    full_val = VerificationOutput.model_validate(
        state["in_table_calc_verification_output"]
    )
    issues_val = VerificationOutput.model_validate(state["in_table_calc_issues"])
    assert full_val.tables == []
    assert issues_val.tables == []


@pytest.mark.asyncio
async def test_resolve_and_verify_formulas_sorting():
    # Setup multiple tables with multiple issues of varying severity
    # Table A has max diff 50
    # Table B has max diff 100
    grid_a = [
        [CellData(value="100", formulas=[])],
        [CellData(value="150", formulas=["cell(0,0)"])],  # Diff 50
        [CellData(value="110", formulas=["cell(0,0)"])],  # Diff 10
    ]
    grid_b = [
        [CellData(value="200", formulas=[])],
        [CellData(value="300", formulas=["cell(0,0)"])],  # Diff 100
        [CellData(value="205", formulas=["cell(0,0)"])],  # Diff 5
    ]

    extraction_output = ExtractionOutput(
        tables=[
            ExtractedTable(table_name="Table A", table=grid_a),
            ExtractedTable(table_name="Table B", table=grid_b),
        ]
    )

    callback_context = MagicMock()
    state = {"extraction_output": extraction_output}
    callback_context.state = state

    await resolve_and_verify_formulas(callback_context)

    issues_val = VerificationOutput.model_validate(state["in_table_calc_issues"])

    # Table B should be first because it has the max diff (100)
    assert issues_val.tables[0].table_name == "Table B"
    assert issues_val.tables[1].table_name == "Table A"

    # Within Table B, the 100 diff verification should be first
    b_verifs = issues_val.tables[0].verifications
    assert abs(b_verifs[0].formula_tests[0].difference) == 100.0
    assert abs(b_verifs[1].formula_tests[0].difference) == 5.0

    # Within Table A, the 50 diff verification should be first
    a_verifs = issues_val.tables[1].verifications
    assert abs(a_verifs[0].formula_tests[0].difference) == 50.0
    assert abs(a_verifs[1].formula_tests[0].difference) == 10.0
