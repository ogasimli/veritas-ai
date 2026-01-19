"""External signal agent - searches news/litigation via google_search."""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai.types import GenerateContentConfig
from . import prompt
from .schema import ExternalSignalOutput

external_signal_agent = LlmAgent(
    name="external_signal",
    model="gemini-2.5-flash",  # Compatible with google_search (Gemini 2+ required)
    instruction=prompt.INSTRUCTION,
    tools=[google_search],  # CRITICAL: ONLY google_search, cannot add other tools
    output_key="external_signal_output",
    output_schema=ExternalSignalOutput,
    generate_content_config=GenerateContentConfig(
        temperature=1.0,  # Recommended for grounding per RESEARCH.md
    ),
)
