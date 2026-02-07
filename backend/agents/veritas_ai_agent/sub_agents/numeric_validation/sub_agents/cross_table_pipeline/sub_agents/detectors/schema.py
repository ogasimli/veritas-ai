"""Schemas for cross-table detectors."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class CrossTableFinding(BaseModel):
    """A cross-table discrepancy between financial statements."""

    fsli_name: str = Field(
        description="Name of the Financial Statement Line Item involved"
    )
    statement_type: str = Field(
        description="Which statement the item appears in (e.g., 'Balance Sheet', 'Income Statement', 'Cash Flow')"
    )
    discrepancy: str = Field(
        description="Description of the cross-table discrepancy found"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning showing how the discrepancy was identified"
    )
    source_refs: list[str] = Field(
        description="References to locations in the document (e.g., 'Table 4', 'Note 12')"
    )


class CrossTableDetectorOutput(BaseAgentOutput):
    """Output from a cross-table detector — list of discrepancies found."""

    findings: list[CrossTableFinding] = Field(
        default_factory=list,
        description="List of cross-table discrepancies found",
    )
