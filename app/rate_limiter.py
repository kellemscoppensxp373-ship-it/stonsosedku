from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """Serialize explicitly requested outbound diagnostics with a minimum interval."""

    def __init__(self, min_interval: float = 15.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
        if min_interval < 0:
            raise ValueError("min_interval cannot be negative")
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last_call: float | None = None

    async def wait_turn(self) -> None:
        async with self._lock:
            now = self._clock()
            if self._last_call is not None:
                remaining = self.min_interval - (now - self._last_call)
                if remaining > 0:
                    await self._sleep(remaining)
            self._last_call = self._clock()

    def seconds_until_slot(self) -> float:
        if self._last_call is None:
            return 0.0
        return max(0.0, self.min_interval - (self._clock() - self._last_call))
