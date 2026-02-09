"""Generic async rate limiter for serializing API calls with minimum intervals.

Uses an ``asyncio.Lock`` so that only one caller proceeds at a time and a
monotonic timestamp to ensure *min_interval* seconds have elapsed since the
previous call — even across different callers.

Usage::

    from veritas_ai_agent.shared.rate_limiter import RateLimiter

    _limiter = RateLimiter(min_interval=65)

    async with _limiter:
        await some_api_call()
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Async rate limiter that enforces a minimum interval between calls.

    Uses an ``asyncio.Lock`` so that only one caller proceeds at a time and
    a monotonic timestamp to ensure *min_interval* seconds have elapsed since
    the previous call — even across different callers.
    """

    def __init__(self, min_interval: float, *, name: str = "RateLimiter"):
        self.min_interval = min_interval
        self.name = name
        self._lock: asyncio.Lock | None = None
        self._last_call: float = 0.0  # monotonic

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> None:
        """Wait until it is safe to make the next API call."""
        lock = self._get_lock()
        await lock.acquire()
        # While holding the lock, sleep until the interval has elapsed.
        now = time.monotonic()
        wait = self._last_call + self.min_interval - now
        if wait > 0:
            logger.info(
                "%s: sleeping %.1fs before next call",
                self.name,
                wait,
            )
            await asyncio.sleep(wait)

    def release(self) -> None:
        """Record the call timestamp and release the lock."""
        self._last_call = time.monotonic()
        lock = self._get_lock()
        lock.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *exc):
        self.release()
