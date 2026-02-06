"""MultiPassRefinementAgent: N parallel chains x M sequential passes → aggregation.

Uses ADK's LoopAgent for the M sequential passes within each chain.
"""

import json
import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from veritas_ai_agent.shared.error_handler import default_model_error_handler

from .config import MultiPassRefinementConfig

logger = logging.getLogger(__name__)


class MultiPassRefinementAgent(BaseAgent):
    """Reusable agent that runs NxM LLM passes to maximize finding coverage.

    Architecture:
    - N parallel chains run independently (parallel branches explore different paths)
    - Each chain is a LoopAgent with M iterations (later passes see prior findings)
    - Final aggregator deduplicates all findings across all chains

    Parameters
    ----------
    name : str
        Agent name (e.g., "LogicConsistencyDetector")
    config : MultiPassRefinementConfig
        Complete configuration including domain logic and runtime parameters
    output_key : str
        State key to write final aggregated output
    """

    config: MultiPassRefinementConfig | None = None
    output_key: str | None = None

    def __init__(
        self,
        name: str,
        config: MultiPassRefinementConfig,
        output_key: str | None = None,
    ):
        super().__init__(name=name)
        self.config = config
        self.output_key = output_key or f"{name.lower()}_output"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # --- Phase 1: Run N parallel chains, each is a LoopAgent with M iterations ---
        assert self.config is not None
        config = self.config
        chain_agents = []
        for chain_idx in range(config.n_parallel_chains):
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
        for chain_idx in range(config.n_parallel_chains):
            key = f"chain_{chain_idx}_accumulated_findings"
            chain_findings = state.get(key, [])
            all_findings.extend(chain_findings)

        logger.info(
            "%s: collected %d total findings from %d chains x %d passes",
            self.name,
            len(all_findings),
            config.n_parallel_chains,
            config.m_sequential_passes,
        )

        # --- Phase 3: Aggregate/deduplicate ---
        all_findings_json = json.dumps(all_findings, indent=2)
        aggregator = self._create_aggregator(all_findings_json)

        async for event in aggregator.run_async(ctx):
            yield event

    def _create_chain_loop(self, chain_idx: int) -> LoopAgent:
        """Create a LoopAgent that runs M sequential passes for one chain."""
        assert self.config is not None
        config = self.config

        accumulated_key = f"chain_{chain_idx}_accumulated_findings"
        pass_output_key = f"chain_{chain_idx}_current_pass_output"

        def before_loop_callback(callback_context: CallbackContext) -> None:
            """Initialize accumulated findings list for this chain."""
            callback_context.state.setdefault(accumulated_key, [])

        def after_pass_callback(callback_context: CallbackContext) -> None:
            """Append findings from current pass to accumulated list."""
            # Call user's callback first if provided
            if chain_config.after_agent_callback:
                chain_config.after_agent_callback(callback_context)

            # Then accumulate findings (required for multi-pass pattern)
            output = callback_context.state.get(pass_output_key)
            if not output:
                return
            if hasattr(output, "model_dump"):
                output = output.model_dump()
            new_findings = config.extract_findings(output)
            callback_context.state[accumulated_key].extend(new_findings)
            logger.debug(
                "%s chain %d: accumulated %d findings",
                self.name,
                chain_idx,
                len(callback_context.state[accumulated_key]),
            )

        # Build LlmAgent config
        chain_config = config.chain_agent_config
        model = chain_config.model
        planner = chain_config.planner
        generate_config = chain_config.generate_content_config

        # Build LlmAgent kwargs
        agent_kwargs = {
            "name": f"{self.name}_Chain{chain_idx}_Pass",
            "model": model,
            "instruction": chain_config.get_instruction(chain_idx),
            "output_schema": chain_config.output_schema,
            "output_key": pass_output_key,
            "after_agent_callback": after_pass_callback,
            "planner": planner,
            "generate_content_config": generate_config,
            "before_agent_callback": chain_config.before_agent_callback,
            "on_model_error_callback": chain_config.on_model_error_callback,
            "before_model_callback": chain_config.before_model_callback,
            "after_model_callback": chain_config.after_model_callback,
            "before_tool_callback": chain_config.before_tool_callback,
            "after_tool_callback": chain_config.after_tool_callback,
            "tools": chain_config.tools,
            "code_executor": chain_config.code_executor,
        }

        pass_agent = LlmAgent(**agent_kwargs)

        return LoopAgent(
            name=f"{self.name}_Chain_{chain_idx}",
            sub_agents=[pass_agent],
            max_iterations=self.config.m_sequential_passes,
            before_agent_callback=before_loop_callback,
        )

    def _create_aggregator(self, all_findings_json: str) -> LlmAgent:
        """Create LLM-based aggregator."""
        # Build aggregator config
        assert self.config is not None
        agg_config = self.config.aggregator_config
        model = agg_config.model
        planner = agg_config.planner
        generate_config = agg_config.generate_content_config

        # Build LlmAgent kwargs
        agent_kwargs = {
            "name": f"{self.name}Aggregator",
            "model": model,
            "instruction": agg_config.get_instruction(all_findings_json),
            "output_schema": agg_config.output_schema,
            "output_key": self.output_key,
            "planner": planner,
            "generate_content_config": generate_config,
            "before_agent_callback": agg_config.before_agent_callback,
            "after_agent_callback": agg_config.after_agent_callback,
            "on_model_error_callback": agg_config.on_model_error_callback
            or default_model_error_handler,
            "before_model_callback": agg_config.before_model_callback,
            "after_model_callback": agg_config.after_model_callback,
            "before_tool_callback": agg_config.before_tool_callback,
            "after_tool_callback": agg_config.after_tool_callback,
            "tools": agg_config.tools,
            "code_executor": agg_config.code_executor,
        }

        return LlmAgent(**agent_kwargs)
