"""ReviewerAgent - filters false positives from disclosure findings."""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import prompt
from .schema import ReviewerAgentOutput

reviewer_agent = LlmAgent(
    name="DisclosureReviewer",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="reviewer_output",
    output_schema=ReviewerAgentOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
