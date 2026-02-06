"""MultiPassRefinementAgent: N parallel chains x M sequential passes -> aggregation.

Uses ADK's LoopAgent for the M sequential passes within each chain.
"""

import json
import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .config import MultiPassRefinementConfig
from .protocols import MultiPassRefinementProtocol

logger = logging.getLogger(__name__)

_FALLBACK_MODEL = "gemini-3-pro-preview"


def _get_default_planner() -> BuiltInPlanner:
    """Get default planner with high thinking level."""
    return BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level="high"
        )
    )


def _get_default_generate_config() -> types.GenerateContentConfig:
    """Get default generation config with retry options."""
    return types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    )


class MultiPassRefinementAgent(BaseAgent):
    """Reusable agent that runs NxM LLM passes to maximize finding coverage.

    Architecture:
    - N parallel chains run independently (parallel branches explore different paths)
    - Each chain is a LoopAgent with M iterations (later passes see prior findings)
    - Final aggregator deduplicates all findings across all chains

    Parameters
    ----------
    name : str
        Agent name (e.g., "LogicConsistency")
    protocol : MultiPassRefinementProtocol
        Implementation-specific prompts, schemas, and config
    config : MultiPassRefinementConfig
        Runtime overrides for N, M, etc.
    output_key : str
        State key to write final aggregated output
    """

    # Define fields to satisfy Pydantic if BaseAgent is a BaseModel
    protocol: MultiPassRefinementProtocol | None = None
    config: MultiPassRefinementConfig | None = None
    output_key: str | None = None

    def __init__(
        self,
        name: str,
        protocol: MultiPassRefinementProtocol,
        config: MultiPassRefinementConfig | None = None,
        output_key: str | None = None,
    ):
        # We pass only name to super() to avoid ty-check unknown-argument errors,
        # but we must ensure fields are initialized for Pydantic.
        super().__init__(name=name)
        self.protocol = protocol
        self.config = config or MultiPassRefinementConfig()
        self.output_key = output_key or f"{name.lower()}_output"

    @property
    def _n_parallel(self) -> int:
        n = self.config.n_parallel_chains if self.config else None
        return n or self.protocol.default_n_parallel if self.protocol else 2

    @property
    def _m_sequential(self) -> int:
        m = self.config.m_sequential_passes if self.config else None
        return m or self.protocol.default_m_sequential if self.protocol else 3

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # --- Phase 1: Run N parallel chains, each is a LoopAgent with M iterations ---
        chain_agents = []
        for chain_idx in range(self._n_parallel):
            chain_loop = self._create_chain_loop(chain_idx)
            chain_agents.append(chain_loop)

        parallel = ParallelAgent(
            name=f"{self.name}_ParallelChains",
            sub_agents=chain_agents,
        )
        async for event in parallel.run_async(ctx):
            yield event

        # --- Phase 2: Collect all findings from all chains ---
        all_findings: list[dict] = []
        for chain_idx in range(self._n_parallel):
            # Each chain accumulates findings in state[f"chain_{idx}_accumulated_findings"]
            key = f"chain_{chain_idx}_accumulated_findings"
            chain_findings = state.get(key, [])
            all_findings.extend(chain_findings)

        logger.info(
            "%s: collected %d total findings from %d chains x %d passes",
            self.name,
            len(all_findings),
            self._n_parallel,
            self._m_sequential,
        )

        # --- Phase 3: Aggregate/deduplicate ---
        all_findings_json = json.dumps(all_findings, indent=2)
        aggregator = self._create_aggregator(all_findings_json)

        async for event in aggregator.run_async(ctx):
            yield event

        agg_output_key = getattr(aggregator, "output_key", None)
        if agg_output_key and agg_output_key != self.output_key:
            state[self.output_key] = state.get(agg_output_key)

    def _create_chain_loop(self, chain_idx: int) -> LoopAgent:
        """Create a LoopAgent that runs M sequential passes for one chain."""
        accumulated_key = f"chain_{chain_idx}_accumulated_findings"
        pass_output_key = f"chain_{chain_idx}_current_pass_output"

        def before_loop_callback(callback_context: CallbackContext) -> None:
            """Initialize accumulated findings list for this chain."""
            callback_context.state.setdefault(accumulated_key, [])

        def after_pass_callback(callback_context: CallbackContext) -> None:
            """Append findings from current pass to accumulated list."""
            output = callback_context.state.get(pass_output_key)
            if not output:
                return
            if hasattr(output, "model_dump"):
                output = output.model_dump()
            if self.protocol:
                new_findings = self.protocol.extract_findings(output)
                callback_context.state[accumulated_key].extend(new_findings)
            logger.debug(
                "%s chain %d: accumulated %d findings",
                self.name,
                chain_idx,
                len(callback_context.state[accumulated_key]),
            )

        # Get planner, generate config, and model from chain_agent_config or use defaults
        chain_config = self.config.chain_agent_config if self.config else None
        planner = (
            chain_config.planner
            if chain_config and chain_config.planner
            else _get_default_planner()
        )
        generate_config = (
            chain_config.generate_content_config
            if chain_config and chain_config.generate_content_config
            else _get_default_generate_config()
        )
        # Use specific chain model if set, otherwise fall back to default
        model = (
            chain_config.model
            if chain_config and chain_config.model
            else (self.config.model if self.config else _FALLBACK_MODEL)
            or _FALLBACK_MODEL
        )

        pass_agent = LlmAgent(
            name=f"{self.name}_Chain{chain_idx}_Pass",
            model=model,
            instruction=self.protocol.get_pass_instruction(chain_idx)
            if self.protocol
            else "",
            output_schema=self.protocol.pass_output_schema if self.protocol else None,
            output_key=pass_output_key,
            after_agent_callback=after_pass_callback,
            on_model_error_callback=default_model_error_handler,
            planner=planner,
            generate_content_config=generate_config,
        )

        return LoopAgent(
            name=f"{self.name}_Chain_{chain_idx}",
            sub_agents=[pass_agent],
            max_iterations=self._m_sequential,
            before_agent_callback=before_loop_callback,
        )

    def _create_aggregator(self, all_findings_json: str) -> LlmAgent:
        """Create LLM-based aggregator."""
        # Get planner and generate config from aggregator_config or use defaults
        agg_config = self.config.aggregator_config if self.config else None
        planner = (
            agg_config.planner
            if agg_config and agg_config.planner
            else _get_default_planner()
        )
        generate_config = (
            agg_config.generate_content_config
            if agg_config and agg_config.generate_content_config
            else _get_default_generate_config()
        )
        # Use specific aggregator model if set, otherwise fall back to default
        model = (
            agg_config.model
            if agg_config and agg_config.model
            else (self.config.model if self.config else _FALLBACK_MODEL)
            or _FALLBACK_MODEL
        )

        return LlmAgent(
            name=f"{self.name}Aggregator",
            model=model,
            instruction=self.protocol.get_aggregator_instruction(all_findings_json)
            if self.protocol
            else "",
            output_schema=self.protocol.aggregated_output_schema
            if self.protocol
            else None,
            output_key=self.output_key or "",
            on_model_error_callback=default_model_error_handler,
            planner=planner,
            generate_content_config=generate_config,
        )
