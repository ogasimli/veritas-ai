"""ReviewerAgent - filters, re-verifies, and outputs final findings."""
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from agents.common.error_handler import default_model_error_handler

from . import prompt
from .schema import ReviewerAgentOutput

reviewer_agent = LlmAgent(
    name="ReviewerAgent",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="reviewer_output",
    output_schema=ReviewerAgentOutput,
    code_executor=BuiltInCodeExecutor(),  # For re-verification
    on_model_error_callback=default_model_error_handler,
)
