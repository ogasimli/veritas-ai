"""Pydantic schemas for the Table Namer agent."""

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class TableNameAssignment(BaseModel):
    """A single table-name assignment returned by the LLM."""

    table_index: int = Field(description="0-based index of the table in document order")
    table_name: str = Field(description="Human-readable name inferred for the table")


class TableNamerOutput(BaseAgentOutput):
    """Structured output envelope written to state by the LLM agent."""

    table_names: list[TableNameAssignment] = Field(
        default_factory=list,
        description="Ordered list of name assignments, one per extracted table",
    )
