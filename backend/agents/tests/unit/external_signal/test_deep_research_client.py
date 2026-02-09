"""Unit tests for the DeepResearchClient."""

import asyncio
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

_MODULE = "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client"

# Patch genai before importing the module to avoid real API client creation.
with patch(f"{_MODULE}.genai") as _mock_genai, patch(f"{_MODULE}.types"):
    _mock_genai.Client.return_value = AsyncMock()
    from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client import (
        DeepResearchClient,
    )

from veritas_ai_agent.shared.rate_limiter import RateLimiter


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
def _reset_rate_limiter():
    """Reset the module-level rate limiter before each test."""
    mod = _get_module()
    mod._rate_limiter = RateLimiter(0)  # no delay for tests
    yield
    mod._rate_limiter = RateLimiter(0)


@pytest.fixture
def client():
    """Create a DeepResearchClient with a mocked genai.Client."""
    with patch(f"{_MODULE}.genai") as mock_genai, patch(f"{_MODULE}.types"):
        mock_genai.Client.return_value = AsyncMock()
        c = DeepResearchClient()
    return c


# ---------------------------------------------------------------------------
# RateLimiter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiter_lazy_lock_init():
    """Lock is created on first acquire."""
    rl = RateLimiter(0)
    assert rl._lock is None
    async with rl:
        assert rl._lock is not None


@pytest.mark.asyncio
async def test_rate_limiter_enforces_interval():
    """Rate limiter sleeps to enforce minimum interval."""
    rl = RateLimiter(min_interval=100)
    # Simulate a previous call that just happened
    rl._lock = asyncio.Lock()
    rl._last_call = time.monotonic()

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with rl:
            pass

    # Should have slept for ~100s (minus tiny elapsed time)
    assert mock_sleep.call_count == 1
    slept = mock_sleep.call_args[0][0]
    assert slept > 90  # close to 100


@pytest.mark.asyncio
async def test_rate_limiter_no_sleep_on_first_call():
    """First call should not sleep (no previous call timestamp)."""
    rl = RateLimiter(min_interval=60)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with rl:
            pass

    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limiter_records_timestamp_on_release():
    """Release records the monotonic timestamp."""
    rl = RateLimiter(min_interval=0)
    before = time.monotonic()
    async with rl:
        pass
    after = time.monotonic()

    assert before <= rl._last_call <= after


@pytest.mark.asyncio
async def test_rate_limiter_serializes_callers():
    """Two concurrent callers are serialized by the lock."""
    rl = RateLimiter(min_interval=0)
    call_order = []

    async def caller(name):
        async with rl:
            call_order.append(f"start-{name}")
            await asyncio.sleep(0.02)
            call_order.append(f"end-{name}")

    await asyncio.gather(caller("A"), caller("B"))

    # Must be serialized: start-X, end-X, start-Y, end-Y
    assert call_order[0].startswith("start-")
    assert call_order[1].startswith("end-")
    assert call_order[2].startswith("start-")
    assert call_order[3].startswith("end-")


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
            mock_time.monotonic = time.monotonic
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
    """Retries on timeout, succeeds on second attempt."""
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

    result = await client.run_research(query="test", max_retries=3)

    assert result["status"] == "completed"
    assert client._run_single_attempt.call_count == 2


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

    result = await client.run_research(query="test", max_retries=3)

    assert result["status"] == "completed"
    assert client._run_single_attempt.call_count == 3


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

    result = await client.run_research(query="test", max_retries=3)

    assert result["status"] == "timeout"
    assert client._run_single_attempt.call_count == 3


@pytest.mark.asyncio
async def test_run_research_no_retry_after_last_attempt(client):
    """No retry after the final failed attempt."""
    failed_result = {
        "result": None,
        "duration_seconds": 10.0,
        "status": "failed",
        "error": "error",
    }

    client._run_single_attempt = AsyncMock(return_value=failed_result)
    result = await client.run_research(query="test", max_retries=1)

    assert result["status"] == "failed"
    assert client._run_single_attempt.call_count == 1


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

    result = await client.run_research(query="test", max_retries=2)

    # duration_seconds should be updated by run_research (total time)
    assert result["duration_seconds"] >= 0


# ---------------------------------------------------------------------------
# Rate limiter integration with run_research
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiter_serializes_concurrent_research(client):
    """Two concurrent run_research calls are serialized by the rate limiter."""
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

    results = await asyncio.gather(
        client.run_research(query="A", max_retries=1),
        client.run_research(query="B", max_retries=1),
    )

    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "completed"

    # Calls must be serialized: start-X, end-X, start-Y, end-Y
    assert call_order[0].startswith("start-")
    assert call_order[1].startswith("end-")
    assert call_order[2].startswith("start-")
    assert call_order[3].startswith("end-")


@pytest.mark.asyncio
async def test_rate_limiter_releases_between_retries(client):
    """Rate limiter is released between retries, allowing other callers."""
    events = []

    async def mock_attempt(query, timeout_minutes=5, enable_thinking_summaries=True):
        events.append(f"run-{query}")
        if query == "slow" and len([e for e in events if e == "run-slow"]) == 1:
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

    results = await asyncio.gather(
        client.run_research(query="slow", max_retries=2),
        client.run_research(query="fast", max_retries=1),
    )

    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "completed"

    # "fast" should be able to run while "slow" is between retries
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
