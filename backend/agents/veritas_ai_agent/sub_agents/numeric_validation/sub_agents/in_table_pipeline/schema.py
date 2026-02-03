"""Pydantic schema for a single in-table batch agent output."""

from pydantic import Field

from veritas_ai_agent.schemas import BaseAgentOutput


class InTableBatchOutput(BaseAgentOutput):
    formulas: list[dict] = Field(
        default_factory=list,
        description="List of detected in-table formulas for the currently processed batch of tables",
    )
