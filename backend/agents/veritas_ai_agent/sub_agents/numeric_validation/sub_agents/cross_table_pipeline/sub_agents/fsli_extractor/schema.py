"""Pydantic schema for the FSLI extractor agent output."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class FsliCategorization(BaseModel):
    """Lists of FSLIs grouped by their hierarchical role."""

    primary_fsli: list[str] = Field(
        default_factory=list,
        description="Main balance-sheet, income-statement, or cash-flow line items that appear in more than one table (e.g., 'Total assets').",
    )
    sub_fsli: list[str] = Field(
        default_factory=list,
        description="Note-level or breakdown items that roll up into a primary FSLI and appear in multiple tables (e.g., 'Trade receivables').",
    )


class FsliExtractorOutput(BaseAgentOutput, FsliCategorization):
    """The structured output of the FSLI Extractor agent."""
