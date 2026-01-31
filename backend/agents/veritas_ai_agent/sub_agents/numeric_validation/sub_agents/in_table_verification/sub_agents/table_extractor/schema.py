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
    grid: list[list[CellData]] = Field(
        description="2D array representation of the table. Row 0 = headers, Row 1+ = data. Column 0 often contains row labels."
    )


class ExtractionOutput(BaseAgentOutput):
    """Output schema for TableExtractorAgent."""

    tables: list[ExtractedTable] = Field(
        default_factory=list,
        description="List of financial tables extracted from the document",
    )
