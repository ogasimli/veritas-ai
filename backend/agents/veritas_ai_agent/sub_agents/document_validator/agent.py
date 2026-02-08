"""DocumentValidator sub-agent definition."""

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_FLASH

from . import prompt
from .schema import DocumentValidatorOutput

document_validator_agent = LlmAgent(
    name="DocumentValidator",
    model=GEMINI_FLASH,
    instruction=prompt.INSTRUCTION,
    output_key="document_validator_output",
    output_schema=DocumentValidatorOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
