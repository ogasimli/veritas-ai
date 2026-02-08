"""Pydantic schema for in-table check agents."""

from pydantic import BaseModel, Field


class TargetCell(BaseModel):
    """Identifies a specific cell in a specific table."""

    table_index: int = Field(description="Index of the table containing the cell")
    row_index: int = Field(description="Row index of the cell")
    col_index: int = Field(description="Column index of the cell")
