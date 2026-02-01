from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class CellData(BaseModel):
    value: str = Field(description="The value shown in the original report")
    formulas: list[str] = Field(
        default_factory=list,
        description="Array of formula candidates (empty if not a calculable cell)",
    )


class ExtractedTable(BaseModel):
    table_name: str = Field(description="Explicit or inferred name of the table")
    table: list[list[CellData]] = Field(
        description="2D array representation of the table. Row 0 = headers, Row 1+ = data. Column 0 often contains row labels."
    )


class ExtractionOutput(BaseAgentOutput):
    """Output schema for TableExtractorAgent."""

    tables: list[ExtractedTable] = Field(
        default_factory=list,
        description="List of financial tables extracted from the document",
    )


class FormulaTest(BaseModel):
    formula: str
    calculated_value: float
    difference: float


class CellVerification(BaseModel):
    cell_ref: str
    actual_value: float
    formula_tests: list[FormulaTest]


class TableVerification(BaseModel):
    table_name: str
    table: list[list[CellData]]
    verifications: list[CellVerification]


class VerificationOutput(BaseModel):
    """Internal verification results."""

    tables: list[TableVerification] = Field(default_factory=list)
