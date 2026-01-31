from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput

from ..table_extractor.schema import CellData


class FormulaTest(BaseModel):
    formula: str = Field(description="The formula being tested")
    calculated_value: float = Field(description="Result of evaluating the formula")
    difference: float = Field(
        description="Difference between calculated and actual value (calculated - actual)"
    )


class CellVerification(BaseModel):
    cell_ref: str = Field(description="Row, Col reference, e.g. '(2, 3)'")
    actual_value: float = Field(description="Value found in the report")
    formula_tests: list[FormulaTest] = Field(
        description="Results of testing each formula candidate"
    )


class TableVerification(BaseModel):
    table_name: str = Field(description="Name of the table")
    table: list[list[CellData]] = Field(
        description="2D array representation of the table. Populated by the prompt template using `{table}` from the extraction output."
    )
    verifications: list[CellVerification] = Field(
        description="List of verifications for calculable cells"
    )


class VerificationOutput(BaseAgentOutput):
    """Output schema for InTableCalcVerifierAgent."""

    tables: list[TableVerification] = Field(
        default_factory=list,
        description="Verification results for all processed tables",
    )
