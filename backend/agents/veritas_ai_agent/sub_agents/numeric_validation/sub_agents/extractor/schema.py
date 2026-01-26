from pydantic import BaseModel, Field
from typing import List

class ExtractorAgentOutput(BaseModel):
    """Output schema for ExtractorAgent."""
    fsli_names: List[str] = Field(
        default_factory=list,
        description="List of Financial Statement Line Item names found in the document"
    )
