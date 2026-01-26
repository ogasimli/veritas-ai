from pydantic import Field

from veritas_ai_agent.schemas import BaseAgentOutput


class ExtractorAgentOutput(BaseAgentOutput):
    """Output schema for ExtractorAgent."""

    fsli_names: list[str] = Field(
        default_factory=list,
        description="List of Financial Statement Line Item names found in the document",
    )
