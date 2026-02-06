"""Configuration for the MultiPassRefinementAgent pattern."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel


@dataclass
class MultiPassRefinementLlmAgentConfig:
    """Configuration for LLM agents using ADK's native config objects.

    This allows passing ADK's planner and generation configs directly,
    avoiding the need to maintain a parallel config structure.
    """

    # Required fields
    output_schema: type[BaseModel]
    get_instruction: Callable  # For chain: Callable[[int], str], For aggregator: Callable[[str], str]

    # Optional fields with defaults
    model: str = "gemini-3-pro-preview"
    planner: BuiltInPlanner | None = None
    generate_content_config: types.GenerateContentConfig | None = None

    # Callbacks
    before_agent_callback: Callable | None = None
    after_agent_callback: Callable | None = None
    on_model_error_callback: Callable | None = None
    before_model_callback: Callable | None = None
    after_model_callback: Callable | None = None
    before_tool_callback: Callable | None = None
    after_tool_callback: Callable | None = None

    # Tools and code execution
    tools: list[Any] | None = None
    code_executor: Any | None = None


@dataclass
class MultiPassRefinementConfig:
    """All-in-one configuration for multi-pass refinement.

    Combines runtime parameters and domain logic in a single config.
    """

    # === Required Fields ===
    chain_agent_config: (
        MultiPassRefinementLlmAgentConfig  # Config for chain pass agents
    )
    aggregator_config: MultiPassRefinementLlmAgentConfig  # Config for aggregator agent
    extract_findings: Callable[[dict], list[dict]]  # Extract findings from pass output

    # === Runtime Parameters ===
    n_parallel_chains: int = 3
    m_sequential_passes: int = 2
