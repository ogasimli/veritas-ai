"""Schemas for the cross-table reviewer."""

from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class ReviewedCrossTableFinding(BaseModel):
    """A cross-table finding that has been reviewed and severity-assessed."""

    fsli_name: str = Field(
        description="Name of the Financial Statement Line Item involved"
    )
    statement_type: str = Field(
        description="Which statement the item appears in (e.g., 'Balance Sheet', 'Income Statement', 'Cash Flow')"
    )
    discrepancy: str = Field(
        description="Description of the cross-table discrepancy found"
    )
    severity: Literal["high", "medium", "low"] = Field(
        description="Business-impact severity: 'high' (material), 'medium' (operational), 'low' (minor)"
    )
    reasoning: str = Field(
        description="Step-by-step reasoning showing how the discrepancy was verified"
    )
    source_refs: list[str] = Field(
        description="References to locations in the document (e.g., 'Table 4', 'Note 12')"
    )


class CrossTableReviewerOutput(BaseAgentOutput):
    """Output from the cross-table reviewer — confirmed findings with severity."""

    findings: list[ReviewedCrossTableFinding] = Field(
        default_factory=list,
        description="List of confirmed cross-table discrepancies (false positives removed)",
    )
