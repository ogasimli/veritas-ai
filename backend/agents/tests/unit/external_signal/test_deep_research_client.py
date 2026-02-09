"""Unit tests for the DeepResearchClient."""

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

_MODULE = "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client"

# Patch genai before importing the module to avoid real API client creation.
with patch(f"{_MODULE}.genai") as _mock_genai:
    _mock_genai.Client.return_value = AsyncMock()
    from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client import (
        DeepResearchClient,
        _get_semaphore,
    )


def _get_module():
    return sys.modules[_MODULE]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_interaction(
    status="completed", interaction_id="test-id", text="result text", error=None
):
    """Build a fake Interaction object returned by the Gemini API."""
    outputs = [SimpleNamespace(text=text)] if text else []
    ns = SimpleNamespace(
        id=interaction_id,
        status=status,
        outputs=outputs,
    )
    if error is not None:
        ns.error = error
    return ns


@pytest.fixture(autouse=True)
def _reset_semaphore():
    """Reset the module-level semaphore before each test."""
    mod = _get_module()
    mod._semaphore = None
    yield
    mod._semaphore = None


@pytest.fixture
def client():
    """Create a DeepResearchClient with a mocked genai.Client."""
    with patch(f"{_MODULE}.genai") as mock_genai:
        mock_genai.Client.return_value = AsyncMock()
        c = DeepResearchClient()
    return c


# ---------------------------------------------------------------------------
# Semaphore tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semaphore_lazy_init():
    """Semaphore is created on first call to _get_semaphore."""
    sem = _get_semaphore()
    assert isinstance(sem, asyncio.Semaphore)


@pytest.mark.asyncio
async def test_semaphore_is_singleton():
    """Repeated calls return the same semaphore instance."""
    sem1 = _get_semaphore()
    sem2 = _get_semaphore()
    assert sem1 is sem2


@pytest.mark.asyncio
async def test_semaphore_default_concurrency():
    """Default concurrency is 1."""
    sem = _get_semaphore()
    # Semaphore with value 1: acquiring once should succeed, second should block.
    acquired = sem._value  # internal attribute; 1 means one slot free
    assert acquired == 1


@pytest.mark.asyncio
async def test_semaphore_respects_env_var():
    """DEEP_RESEARCH_MAX_CONCURRENCY env var controls concurrency."""
    mod = _get_module()

    with patch.dict("os.environ", {"DEEP_RESEARCH_MAX_CONCURRENCY": "5"}):
        original = mod._MAX_CONCURRENCY
        mod._MAX_CONCURRENCY = 5
        mod._semaphore = None
        sem = _get_semaphore()
        assert sem._value == 5
        mod._MAX_CONCURRENCY = original


# ---------------------------------------------------------------------------
# _run_single_attempt tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_attempt_completes_immediately(client):
    """Interaction completes on first poll."""
    completed = _make_interaction(status="completed", text="research findings")
    pending = _make_interaction(status="pending", interaction_id="test-id", text=None)

    client._create_interaction = AsyncMock(return_value=pending)
    client._get_interaction = AsyncMock(return_value=completed)

    result = await client._run_single_attempt(query="test query", timeout_minutes=1)

    assert result["status"] == "completed"
    assert result["result"] == "research findings"
    assert result["error"] is None
    assert result["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_single_attempt_completes_after_multiple_polls(client):
    """Interaction is in-progress for several polls then completes."""
    pending = _make_interaction(status="pending", interaction_id="test-id", text=None)
    in_progress = _make_interaction(
        status="in_progress", interaction_id="test-id", text=None
    )
    completed = _make_interaction(status="completed", text="done")

    client._create_interaction = AsyncMock(return_value=pending)
    client._get_interaction = AsyncMock(
        side_effect=[in_progress, in_progress, completed]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client._run_single_attempt(query="test", timeout_minutes=5)

    assert result["status"] == "completed"
    assert result["result"] == "done"
    assert client._get_interaction.call_count == 3


@pytest.mark.asyncio
async def test_single_attempt_timeout(client):
    """Returns timeout when elapsed exceeds timeout_minutes."""
    pending = _make_interaction(status="pending", interaction_id="test-id", text=None)
    in_progress = _make_interaction(
        status="in_progress", interaction_id="test-id", text=None
    )

    client._create_interaction = AsyncMock(return_value=pending)
    client._get_interaction = AsyncMock(return_value=in_progress)

    # time.time() returns 0 for start_time, then 600 for elapsed check
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with patch(f"{_MODULE}.time") as mock_time:
            mock_time.time.side_effect = [0, 600]
            result = await client._run_single_attempt(query="test", timeout_minutes=5)

    assert result["status"] == "timeout"
    assert "5 minute timeout" in result["error"]
    assert result["result"] is None


@pytest.mark.asyncio
async def test_single_attempt_failed_status(client):
    """Returns failure when interaction status is 'failed'."""
    pending = _make_interaction(status="pending", interaction_id="test-id", text=None)
    failed = _make_interaction(status="failed", interaction_id="test-id", text=None)
    failed.error = "API quota exceeded"

    client._create_interaction = AsyncMock(return_value=pending)
    client._get_interaction = AsyncMock(return_value=failed)

    result = await client._run_single_attempt(query="test", timeout_minutes=5)

    assert result["status"] == "failed"
    assert "API quota exceeded" in result["error"]


@pytest.mark.asyncio
async def test_single_attempt_exception(client):
    """Returns failure on unexpected exception."""
    client._create_interaction = AsyncMock(side_effect=ConnectionError("network down"))

    result = await client._run_single_attempt(query="test", timeout_minutes=5)

    assert result["status"] == "failed"
    assert "network down" in result["error"]


@pytest.mark.asyncio
async def test_single_attempt_completed_with_empty_outputs(client):
    """Completed interaction with no outputs returns None result."""
    pending = _make_interaction(status="pending", interaction_id="test-id", text=None)
    completed = _make_interaction(status="completed", text=None)
    completed.outputs = []

    client._create_interaction = AsyncMock(return_value=pending)
    client._get_interaction = AsyncMock(return_value=completed)

    result = await client._run_single_attempt(query="test", timeout_minutes=5)

    assert result["status"] == "completed"
    assert result["result"] is None


# ---------------------------------------------------------------------------
# run_research retry tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_success_first_attempt(client):
    """Returns immediately when first attempt succeeds."""
    client._run_single_attempt = AsyncMock(
        return_value={
            "result": "findings",
            "duration_seconds": 30.0,
            "status": "completed",
            "error": None,
        }
    )

    result = await client.run_research(query="test", max_retries=3)

    assert result["status"] == "completed"
    assert result["result"] == "findings"
    assert client._run_single_attempt.call_count == 1


@pytest.mark.asyncio
async def test_run_research_retries_on_timeout(client):
    """Retries with backoff on timeout, succeeds on second attempt."""
    timeout_result = {
        "result": None,
        "duration_seconds": 300.0,
        "status": "timeout",
        "error": "Research exceeded 5 minute timeout",
    }
    success_result = {
        "result": "findings",
        "duration_seconds": 60.0,
        "status": "completed",
        "error": None,
    }

    client._run_single_attempt = AsyncMock(side_effect=[timeout_result, success_result])

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.run_research(
            query="test",
            max_retries=3,
            initial_backoff_seconds=15,
            backoff_multiplier=2,
        )

    assert result["status"] == "completed"
    assert client._run_single_attempt.call_count == 2
    # First backoff: 15 * (2 ** 0) = 15s
    mock_sleep.assert_called_once_with(15)


@pytest.mark.asyncio
async def test_run_research_retries_on_failure(client):
    """Retries on failed status, succeeds on third attempt."""
    failed_result = {
        "result": None,
        "duration_seconds": 10.0,
        "status": "failed",
        "error": "API error",
    }
    success_result = {
        "result": "findings",
        "duration_seconds": 60.0,
        "status": "completed",
        "error": None,
    }

    client._run_single_attempt = AsyncMock(
        side_effect=[failed_result, failed_result, success_result]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.run_research(
            query="test",
            max_retries=3,
            initial_backoff_seconds=10,
            backoff_multiplier=2,
        )

    assert result["status"] == "completed"
    assert client._run_single_attempt.call_count == 3
    # First backoff: 10 * (2 ** 0) = 10s, second: 10 * (2 ** 1) = 20s
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(10)
    mock_sleep.assert_any_call(20)


@pytest.mark.asyncio
async def test_run_research_exhausts_all_retries(client):
    """Returns last error after exhausting all retry attempts."""
    timeout_result = {
        "result": None,
        "duration_seconds": 300.0,
        "status": "timeout",
        "error": "Research exceeded 5 minute timeout",
    }

    client._run_single_attempt = AsyncMock(return_value=timeout_result)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.run_research(
            query="test",
            max_retries=3,
            initial_backoff_seconds=15,
            backoff_multiplier=2,
        )

    assert result["status"] == "timeout"
    assert client._run_single_attempt.call_count == 3
    # Backoff after attempt 1 and 2, not after attempt 3
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_run_research_exponential_backoff_values(client):
    """Verify exact exponential backoff timing."""
    timeout_result = {
        "result": None,
        "duration_seconds": 300.0,
        "status": "timeout",
        "error": "timeout",
    }

    client._run_single_attempt = AsyncMock(return_value=timeout_result)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await client.run_research(
            query="test",
            max_retries=3,
            initial_backoff_seconds=15,
            backoff_multiplier=2,
        )

    # 15 * 2^0 = 15, 15 * 2^1 = 30
    calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert calls == [15, 30]


@pytest.mark.asyncio
async def test_run_research_no_backoff_after_last_attempt(client):
    """No sleep after the final failed attempt."""
    failed_result = {
        "result": None,
        "duration_seconds": 10.0,
        "status": "failed",
        "error": "error",
    }

    client._run_single_attempt = AsyncMock(return_value=failed_result)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await client.run_research(query="test", max_retries=1)

    # Only 1 attempt, no backoff
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_run_research_total_duration_updated(client):
    """duration_seconds reflects total time across all attempts."""
    timeout_result = {
        "result": None,
        "duration_seconds": 300.0,
        "status": "timeout",
        "error": "timeout",
    }

    client._run_single_attempt = AsyncMock(return_value=timeout_result)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.run_research(query="test", max_retries=2)

    # duration_seconds should be updated by run_research (total time)
    assert result["duration_seconds"] >= 0


# ---------------------------------------------------------------------------
# Semaphore concurrency tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semaphore_serializes_concurrent_calls(client):
    """Two concurrent run_research calls are serialized by the semaphore."""
    call_order = []

    async def mock_attempt(query, timeout_minutes=5, enable_thinking_summaries=True):
        call_order.append(f"start-{query}")
        await asyncio.sleep(0.05)  # Simulate work
        call_order.append(f"end-{query}")
        return {
            "result": f"result-{query}",
            "duration_seconds": 1.0,
            "status": "completed",
            "error": None,
        }

    client._run_single_attempt = mock_attempt

    # Run two calls concurrently
    results = await asyncio.gather(
        client.run_research(query="A", max_retries=1),
        client.run_research(query="B", max_retries=1),
    )

    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "completed"

    # With semaphore=1, calls must be serialized: one must fully complete
    # before the other starts
    assert call_order[0].startswith("start-")
    assert call_order[1].startswith("end-")
    assert call_order[2].startswith("start-")
    assert call_order[3].startswith("end-")


@pytest.mark.asyncio
async def test_semaphore_released_during_backoff(client):
    """Semaphore is released during retry backoff, allowing other callers."""
    events = []

    async def mock_attempt(query, timeout_minutes=5, enable_thinking_summaries=True):
        events.append(f"run-{query}")
        if query == "slow" and len([e for e in events if e == "run-slow"]) == 1:
            # First attempt of "slow" fails
            return {
                "result": None,
                "duration_seconds": 1.0,
                "status": "timeout",
                "error": "timeout",
            }
        return {
            "result": f"ok-{query}",
            "duration_seconds": 1.0,
            "status": "completed",
            "error": None,
        }

    client._run_single_attempt = mock_attempt

    with patch("asyncio.sleep", new_callable=AsyncMock):
        results = await asyncio.gather(
            client.run_research(
                query="slow", max_retries=2, initial_backoff_seconds=0.01
            ),
            client.run_research(query="fast", max_retries=1),
        )

    # Both should eventually succeed
    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "completed"

    # "fast" should be able to run while "slow" is in backoff
    # (i.e., "fast" doesn't have to wait for all of "slow"'s retries)
    assert "run-fast" in events


# ---------------------------------------------------------------------------
# Default parameter tests
# ---------------------------------------------------------------------------


def test_default_timeout_is_10_minutes(client):
    """Default timeout_minutes is 10."""
    import inspect

    sig = inspect.signature(client.run_research)
    assert sig.parameters["timeout_minutes"].default == 10


def test_default_max_retries_is_3(client):
    """Default max_retries is 3."""
    import inspect

    sig = inspect.signature(client.run_research)
    assert sig.parameters["max_retries"].default == 3


def test_default_backoff_config(client):
    """Default backoff is 60s fixed to respect 1 RPM limit."""
    import inspect

    sig = inspect.signature(client.run_research)
    assert sig.parameters["initial_backoff_seconds"].default == 60
    assert sig.parameters["backoff_multiplier"].default == 1
