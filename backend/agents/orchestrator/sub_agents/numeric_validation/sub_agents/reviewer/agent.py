"""ReviewerAgent - filters, re-verifies, and outputs final findings."""
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor

from . import prompt
from .schema import ReviewerAgentOutput

reviewer_agent = LlmAgent(
    name="ReviewerAgent",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="reviewer_output",
    output_schema=ReviewerAgentOutput,
    code_executor=BuiltInCodeExecutor(),  # For re-verification
)
