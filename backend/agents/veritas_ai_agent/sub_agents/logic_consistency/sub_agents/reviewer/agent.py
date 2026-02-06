from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from . import prompt
from .schema import LogicConsistencyReviewerOutput

reviewer_agent = LlmAgent(
    name="LogicConsistencyReviewer",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="logic_consistency_reviewer_output",
    output_schema=LogicConsistencyReviewerOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
