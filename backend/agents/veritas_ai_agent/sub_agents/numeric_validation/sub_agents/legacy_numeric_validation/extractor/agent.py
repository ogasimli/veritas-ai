"""Extractor sub-agent definition."""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import prompt
from .schema import ExtractorAgentOutput

extractor_agent = LlmAgent(
    name="ExtractorAgent",
    model="gemini-3-flash-preview",
    instruction=prompt.INSTRUCTION,
    output_key="extractor_output",
    output_schema=ExtractorAgentOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
