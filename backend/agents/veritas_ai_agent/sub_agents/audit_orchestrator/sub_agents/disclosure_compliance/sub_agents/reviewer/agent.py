"""ReviewerAgent - filters false positives from disclosure findings."""

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_PRO

from . import prompt
from .schema import DisclosureReviewerOutput

reviewer_agent = LlmAgent(
    name="DisclosureReviewer",
    model=GEMINI_PRO,
    instruction=prompt.INSTRUCTION,
    output_key="disclosure_reviewer_output",
    output_schema=DisclosureReviewerOutput,
    on_model_error_callback=default_model_error_handler,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level="high"
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
