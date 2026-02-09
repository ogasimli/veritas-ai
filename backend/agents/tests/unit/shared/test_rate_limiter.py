"""Unit tests for the shared RateLimiter."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from veritas_ai_agent.shared.rate_limiter import RateLimiter

# ---------------------------------------------------------------------------
# Construction & lazy init
# ---------------------------------------------------------------------------


def test_initial_state():
    """RateLimiter starts with no lock and zero timestamp."""
    rl = RateLimiter(60)
    assert rl.min_interval == 60
    assert rl._lock is None
    assert rl._last_call == 0.0


def test_custom_name():
    """Name parameter is stored for logging."""
    rl = RateLimiter(10, name="TestLimiter")
    assert rl.name == "TestLimiter"


def test_default_name():
    """Default name is 'RateLimiter'."""
    rl = RateLimiter(10)
    assert rl.name == "RateLimiter"


@pytest.mark.asyncio
async def test_lazy_lock_init():
    """Lock is created on first acquire, not at construction."""
    rl = RateLimiter(0)
    assert rl._lock is None
    async with rl:
        assert rl._lock is not None


@pytest.mark.asyncio
async def test_lock_is_reused():
    """Subsequent acquires reuse the same lock instance."""
    rl = RateLimiter(0)
    async with rl:
        lock1 = rl._lock
    async with rl:
        lock2 = rl._lock
    assert lock1 is lock2


# ---------------------------------------------------------------------------
# Interval enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_sleep_on_first_call():
    """First call should not sleep (no previous call timestamp)."""
    rl = RateLimiter(min_interval=60)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with rl:
            pass

    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_enforces_interval():
    """Rate limiter sleeps to enforce minimum interval."""
    rl = RateLimiter(min_interval=100)
    # Simulate a previous call that just happened
    rl._lock = asyncio.Lock()
    rl._last_call = time.monotonic()

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with rl:
            pass

    assert mock_sleep.call_count == 1
    slept = mock_sleep.call_args[0][0]
    assert slept > 90  # close to 100


@pytest.mark.asyncio
async def test_no_sleep_after_interval_elapsed():
    """No sleep if enough time has already passed since last call."""
    rl = RateLimiter(min_interval=1)
    rl._lock = asyncio.Lock()
    rl._last_call = time.monotonic() - 10  # 10 seconds ago

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with rl:
            pass

    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Timestamp recording
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_records_timestamp_on_release():
    """Release records the monotonic timestamp."""
    rl = RateLimiter(min_interval=0)
    before = time.monotonic()
    async with rl:
        pass
    after = time.monotonic()

    assert before <= rl._last_call <= after


@pytest.mark.asyncio
async def test_timestamp_updated_each_call():
    """Each release updates the timestamp."""
    rl = RateLimiter(min_interval=0)

    async with rl:
        pass
    ts1 = rl._last_call

    await asyncio.sleep(0.01)

    async with rl:
        pass
    ts2 = rl._last_call

    assert ts2 > ts1


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serializes_concurrent_callers():
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


@pytest.mark.asyncio
async def test_three_callers_serialized():
    """Three concurrent callers are fully serialized."""
    rl = RateLimiter(min_interval=0)
    call_order = []

    async def caller(name):
        async with rl:
            call_order.append(f"start-{name}")
            await asyncio.sleep(0.01)
            call_order.append(f"end-{name}")

    await asyncio.gather(caller("A"), caller("B"), caller("C"))

    # 6 events, alternating start/end
    assert len(call_order) == 6
    for i in range(0, 6, 2):
        assert call_order[i].startswith("start-")
        assert call_order[i + 1].startswith("end-")


# ---------------------------------------------------------------------------
# Release on exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_released_on_exception():
    """Lock is released even when the body raises an exception."""
    rl = RateLimiter(min_interval=0)

    with pytest.raises(ValueError, match="boom"):
        async with rl:
            raise ValueError("boom")

    # Lock should be released — acquiring again should not deadlock
    acquired = False
    async with rl:
        acquired = True
    assert acquired


@pytest.mark.asyncio
async def test_timestamp_recorded_on_exception():
    """Timestamp is still recorded when the body raises."""
    rl = RateLimiter(min_interval=0)
    before = time.monotonic()

    with pytest.raises(RuntimeError):
        async with rl:
            raise RuntimeError("fail")

    after = time.monotonic()
    assert before <= rl._last_call <= after
