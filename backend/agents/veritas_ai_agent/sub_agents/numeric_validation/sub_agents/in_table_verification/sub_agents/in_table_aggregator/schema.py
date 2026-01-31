from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput

from ..table_extractor import CellData


class CalculationIssue(BaseModel):
    table_name: str = Field(description="Name of the table containing the error")
    grid: list[list[CellData]] = Field(
        description="2D array representation of the table. Row 0 = headers, Row 1+ = data. Column 0 often contains row labels."
    )
    cell_ref: str = Field(description="The cell with the issue, e.g., '(2, 3)'")
    formula_checked: str = Field(description="The formula that failed verification")
    expected_value: float = Field(description="The value calculated by the formula")
    actual_value: float = Field(description="The value shown in the report")
    difference: float = Field(description="expected_value - actual_value")


class AggregatedResult(BaseAgentOutput):
    """Output schema for InTableAggregatorAgent."""

    issues: list[CalculationIssue] = Field(
        default_factory=list,
        description="List of genuine calculation issues, sorted by severity (abs(difference)) descending",
    )
    tables_checked: int = Field(
        description="Total number of tables where checks were performed"
    )
    formulas_verified: int = Field(
        description="Total number of formulas that were verified"
    )
    issues_found: int = Field(description="Total number of genuine issues found")
