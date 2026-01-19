from google.adk.agents import LlmAgent
from . import prompt
from .schema import ReviewerAgentOutput

reviewer_agent = LlmAgent(
    name="LogicReviewer",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="reviewer_output",
    output_schema=ReviewerAgentOutput,
)
