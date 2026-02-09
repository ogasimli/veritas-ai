"""Unit tests for the generic FanOutAgent."""

from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from veritas_ai_agent.shared.fan_out.agent import FanOutAgent, _get_semaphore
from veritas_ai_agent.shared.fan_out.config import FanOutConfig

# --- Test Helpers ---


class MockOutput(BaseModel):
    findings: list[dict] = Field(default_factory=list)


def _make_agent_factory():
    """Return an agent factory that records calls and returns mock agents."""
    calls = []

    def factory(index, item, output_key):
        calls.append((index, item, output_key))
        agent = MagicMock(spec=LlmAgent)
        agent.name = f"test_item_{index}"

        async def _noop_run_async(ctx):
            return
            yield  # makes this an async generator

        agent.run_async = _noop_run_async
        return agent

    return factory, calls


class AsyncIterator:
    """Helper to mock async generator."""

    def __init__(self, seq=None):
        self.iter = iter(seq or [])

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration from None


def _create_config(**overrides) -> FanOutConfig:
    """Create a FanOutConfig with sensible defaults."""
    factory, _ = _make_agent_factory()
    defaults = {
        "prepare_work_items": lambda state: state.get("items", []),
        "create_agent": factory,
        "output_key": "test_output",
    }
    defaults.update(overrides)
    return FanOutConfig(**defaults)


# --- Initialization Tests ---


def test_initialization():
    config = _create_config()
    agent = FanOutAgent(name="TestFanOut", config=config)

    assert agent.name == "TestFanOut"
    assert agent.config is not None
    assert agent.config.output_key == "test_output"
    assert agent.config.results_field == "findings"
    assert agent.config.aggregate is None
    assert agent.config.empty_message is None


def test_initialization_with_overrides():
    custom_aggregate = lambda outputs: {"custom": True}  # noqa: E731
    config = _create_config(
        results_field="formulas",
        empty_message="Nothing to do.",
        aggregate=custom_aggregate,
    )
    agent = FanOutAgent(name="CustomFanOut", config=config)

    assert agent.config is not None
    assert agent.config.results_field == "formulas"
    assert agent.config.empty_message == "Nothing to do."
    assert agent.config.aggregate is custom_aggregate


# --- Early Exit Tests ---


@pytest.mark.asyncio
async def test_early_exit_empty_items():
    """When prepare_work_items returns [], state gets empty result, no agents run."""
    config = _create_config(
        prepare_work_items=lambda state: [],
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {}

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    # Exactly one event emitted carrying the state delta
    assert len(events) == 1
    assert events[0].author == "TestFanOut"
    assert events[0].actions.state_delta["test_output"] == {"findings": []}
    # State gets empty result
    assert ctx.session.state["test_output"] == {"findings": []}


@pytest.mark.asyncio
async def test_early_exit_with_empty_message():
    """When empty and empty_message is set, an informational event is yielded."""
    config = _create_config(
        prepare_work_items=lambda state: [],
        empty_message="No work items found.",
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {}

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    assert events[0].author == "TestFanOut"
    assert "No work items found." in events[0].content.parts[0].text
    assert events[0].actions.state_delta["test_output"] == {"findings": []}
    assert ctx.session.state["test_output"] == {"findings": []}


@pytest.mark.asyncio
async def test_early_exit_custom_results_field():
    """Empty result uses the configured results_field."""
    config = _create_config(
        prepare_work_items=lambda state: [],
        results_field="formulas",
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {}

    async for _ in agent._run_async_impl(ctx):
        pass

    assert ctx.session.state["test_output"] == {"formulas": []}


# --- Agent Creation & Concurrent Execution Tests ---


@pytest.mark.asyncio
async def test_creates_agents_with_correct_output_keys():
    """Verify create_agent is called with deterministic output keys."""
    factory, calls = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["item_a", "item_b", "item_c"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {}

    async for _ in agent._run_async_impl(ctx):
        pass

    assert len(calls) == 3
    assert calls[0] == (0, "item_a", "TestFanOut_item_0")
    assert calls[1] == (1, "item_b", "TestFanOut_item_1")
    assert calls[2] == (2, "item_c", "TestFanOut_item_2")


@pytest.mark.asyncio
async def test_all_agents_run_concurrently():
    """All agents are launched concurrently (throttled by semaphore)."""
    factory, calls = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b", "c"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {}

    async for _ in agent._run_async_impl(ctx):
        pass

    # All 3 agents were created and run
    assert len(calls) == 3

    # Dynamic agents not registered to self.sub_agents (ADK best practice)
    assert agent.sub_agents == []


@pytest.mark.asyncio
async def test_semaphore_is_shared():
    """The global semaphore is reused across calls."""
    sem1 = _get_semaphore()
    sem2 = _get_semaphore()
    assert sem1 is sem2


# --- Output Collection & Aggregation Tests ---


@pytest.mark.asyncio
async def test_default_aggregation():
    """Default aggregation concatenates results_field lists from all outputs."""
    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    # Simulate outputs from two sub-agents written to state
    ctx.session.state = {
        "TestFanOut_item_0": {"findings": [{"id": 1}, {"id": 2}]},
        "TestFanOut_item_1": {"findings": [{"id": 3}]},
    }

    async for _ in agent._run_async_impl(ctx):
        pass

    result = ctx.session.state["test_output"]
    assert result == {"findings": [{"id": 1}, {"id": 2}, {"id": 3}]}


@pytest.mark.asyncio
async def test_default_aggregation_custom_results_field():
    """Default aggregation uses configured results_field."""
    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b"],
        create_agent=factory,
        results_field="formulas",
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {
        "TestFanOut_item_0": {"formulas": [{"expr": "a+b"}]},
        "TestFanOut_item_1": {"formulas": [{"expr": "c-d"}, {"expr": "e*f"}]},
    }

    async for _ in agent._run_async_impl(ctx):
        pass

    result = ctx.session.state["test_output"]
    assert result == {"formulas": [{"expr": "a+b"}, {"expr": "c-d"}, {"expr": "e*f"}]}


@pytest.mark.asyncio
async def test_custom_aggregation():
    """Custom aggregate callback overrides default list concatenation."""

    def custom_aggregate(outputs):
        total = sum(len(o.get("findings", [])) for o in outputs)
        return {"summary": f"{total} findings", "findings": []}

    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b"],
        create_agent=factory,
        aggregate=custom_aggregate,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {
        "TestFanOut_item_0": {"findings": [{"id": 1}]},
        "TestFanOut_item_1": {"findings": [{"id": 2}, {"id": 3}]},
    }

    async for _ in agent._run_async_impl(ctx):
        pass

    result = ctx.session.state["test_output"]
    assert result == {"summary": "3 findings", "findings": []}


@pytest.mark.asyncio
async def test_pydantic_output_normalization():
    """Pydantic model outputs are converted to dicts via model_dump()."""
    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    # Simulate a pydantic model in state (as ADK would store it)
    ctx.session.state = {
        "TestFanOut_item_0": MockOutput(findings=[{"id": 1}]),
    }

    async for _ in agent._run_async_impl(ctx):
        pass

    result = ctx.session.state["test_output"]
    assert result == {"findings": [{"id": 1}]}


@pytest.mark.asyncio
async def test_none_outputs_skipped():
    """If a sub-agent produces no output (None in state), it's skipped."""
    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b", "c"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    ctx = MagicMock()
    ctx.session.state = {
        "TestFanOut_item_0": {"findings": [{"id": 1}]},
        # item_1 missing (None) — e.g. agent errored out
        "TestFanOut_item_2": {"findings": [{"id": 3}]},
    }

    async for _ in agent._run_async_impl(ctx):
        pass

    result = ctx.session.state["test_output"]
    assert result == {"findings": [{"id": 1}, {"id": 3}]}


# --- Dynamic Agent Creation Tests ---


@pytest.mark.asyncio
async def test_dynamic_agents_not_registered_statically():
    """Agents are created dynamically at runtime, not registered to sub_agents.

    This follows Google ADK best practices for dynamic parallel workflows.
    """
    factory, _ = _make_agent_factory()
    config = _create_config(
        prepare_work_items=lambda state: ["a", "b"],
        create_agent=factory,
    )
    agent = FanOutAgent(name="TestFanOut", config=config)

    # Before execution, no sub_agents (static graph is empty)
    assert agent.sub_agents == []

    ctx = MagicMock()
    ctx.session.state = {}

    async for _ in agent._run_async_impl(ctx):
        pass

    # After execution, sub_agents remains empty (dynamic agents not registered)
    assert agent.sub_agents == []


# --- Full Flow Test ---


@pytest.mark.asyncio
async def test_full_flow():
    """End-to-end: prepare → create → execute → collect → aggregate."""
    factory, calls = _make_agent_factory()

    def prepare(state):
        return state.get("detector_output", {}).get("findings", [])

    config = FanOutConfig(
        prepare_work_items=prepare,
        create_agent=factory,
        output_key="reviewer_output",
        results_field="findings",
    )
    agent = FanOutAgent(name="Reviewer", config=config)

    findings_in = [{"id": 1, "text": "issue A"}, {"id": 2, "text": "issue B"}]
    ctx = MagicMock()
    ctx.session.state = {
        "detector_output": {"findings": findings_in},
    }

    # Pre-populate state with expected outputs (simulating what sub-agents would write)
    # FanOutAgent creates output keys as "{agent_name}_item_{i}"
    ctx.session.state["Reviewer_item_0"] = {"findings": [{"id": 1, "reviewed": True}]}
    ctx.session.state["Reviewer_item_1"] = {"findings": [{"id": 2, "reviewed": True}]}

    async for _ in agent._run_async_impl(ctx):
        pass

    # Factory called once per finding
    assert len(calls) == 2
    assert calls[0][1] == {"id": 1, "text": "issue A"}
    assert calls[1][1] == {"id": 2, "text": "issue B"}

    # Aggregated output
    result = ctx.session.state["reviewer_output"]
    assert result == {
        "findings": [
            {"id": 1, "reviewed": True},
            {"id": 2, "reviewed": True},
        ]
    }
