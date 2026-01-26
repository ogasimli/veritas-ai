from typing import List, Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A confirmed numeric discrepancy that failed verification and was confirmed by re-verification."""
    fsli_name: str = Field(
        description="Name of the Financial Statement Line Item with the discrepancy"
    )
    summary: str = Field(
        description="Short human-readable summary of the discrepancy (e.g., 'Revenue components do not sum to reported Total Revenue')"
    )
    severity: Literal["high", "medium", "low"] = Field(
        description="Severity based on discrepancy percentage: 'high' (>5%), 'medium' (1-5%), 'low' (<1%)"
    )
    expected_value: float = Field(
        description="The value expected based on calculation (e.g., sum of components)"
    )
    actual_value: float = Field(
        description="The actual value found in the document for this FSLI"
    )
    discrepancy: float = Field(
        description="Absolute difference between expected and actual values"
    )
    source_refs: List[str] = Field(
        description="References to locations in the document (e.g., 'Table 4, Row 12', 'Note 5')"
    )


from veritas_ai_agent.schemas import BaseAgentOutput

class ReviewerAgentOutput(BaseAgentOutput):
    """Output from numeric reviewer agent - confirmed discrepancies that failed re-verification."""
    findings: List[Finding] = Field(
        default_factory=list,
        description="List of confirmed numeric discrepancies (duplicates removed, re-verification failed)"
    )
