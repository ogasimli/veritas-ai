"""Configuration for the MultiPassRefinementAgent pattern."""



from dataclasses import dataclass


from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types


@dataclass
class LlmAgentConfig:
    """Configuration for LLM agents using ADK's native config objects.

    This allows passing ADK's planner and generation configs directly,
    avoiding the need to maintain a parallel config structure.
    """

    model: str | None = None
    planner: BuiltInPlanner | None = None
    generate_content_config: types.GenerateContentConfig | None = None


@dataclass
class MultiPassRefinementConfig:
    """Runtime configuration for multi-pass refinement.

    Protocol implementations provide defaults; this config can override them.
    """

    n_parallel_chains: int | None = None  # Override protocol default if set
    m_sequential_passes: int | None = None  # Override protocol default if set
    model: str | None = None

    # Agent-specific configurations (using ADK's native config objects)
    chain_agent_config: LlmAgentConfig | None = None  # Config for chain pass agents
    aggregator_config: LlmAgentConfig | None = None  # Config for aggregator agent
