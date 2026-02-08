from pydantic import Field

from veritas_ai_agent.schemas import BaseAgentOutput


class DocumentValidatorOutput(BaseAgentOutput):
    """Output schema for DocumentValidator agent."""

    is_valid_financial_document: bool = Field(
        ...,
        description="True if the document is a financial statement, False otherwise",
    )
