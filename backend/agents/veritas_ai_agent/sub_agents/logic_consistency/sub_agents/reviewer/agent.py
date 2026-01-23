from google.adk.agents import LlmAgent
from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from . import prompt
from .schema import ReviewerAgentOutput

reviewer_agent = LlmAgent(
    name="LogicReviewer",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="reviewer_output",
    output_schema=ReviewerAgentOutput,
    on_model_error_callback=default_model_error_handler,
)
