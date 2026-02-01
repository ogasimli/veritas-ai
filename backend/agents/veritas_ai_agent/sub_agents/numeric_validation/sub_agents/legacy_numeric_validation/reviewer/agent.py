"""ReviewerAgent - filters, re-verifies, and outputs final findings."""

from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import prompt
from .schema import LegacyNumericReviewerOutput

reviewer_agent = LlmAgent(
    name="LegacyNumericIssueReviewer",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="legacy_numeric_issue_reviewer_output",
    output_schema=LegacyNumericReviewerOutput,
    code_executor=BuiltInCodeExecutor(),  # For re-verification
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
