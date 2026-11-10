"""Whole-call monotonic budget, including admission waits and physical attempts."""

from __future__ import annotations

import asyncio
import math
import time
from datetime import UTC
from datetime import datetime

from ocai.core.errors import DeadlineExceededError
from ocai.core.result import CallContext


class Deadline:
    """Translate an aware wall-clock deadline once, then use monotonic time.

    Sync operations cooperate via request timeouts and checks before/after I/O;
    arbitrary blocking Python cannot be preempted. Late output is never accepted.
    Async drivers additionally cancel each pending operation at the remaining bound.
    """

    def __init__(self, ctx: CallContext | None = None) -> None:
        """Capture the remaining window; reject ambiguous naive datetimes."""
        self.expires: float | None = None
        if ctx is not None and ctx.deadline is not None:
            if ctx.deadline.utcoffset() is None:
                raise ValueError("CallContext.deadline must be timezone-aware")
            self.expires = time.monotonic() + (ctx.deadline - datetime.now(UTC)).total_seconds()

    def remaining(self) -> float | None:
        """Return the remaining seconds, raising when the budget has expired."""
        if self.expires is None:
            return None
        left = self.expires - time.monotonic()
        if left <= 0:
            raise DeadlineExceededError("whole-call deadline expired")
        return left

    def delay(self, seconds: float | None) -> float:
        """Validate a retry wait without allowing it to extend the deadline."""
        delay = seconds or 0.0
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("retry delay must be finite and nonnegative")
        left = self.remaining()
        if left is not None and delay >= left:
            raise DeadlineExceededError("retry wait exceeds whole-call deadline")
        return delay

    def sleep(self, seconds: float | None) -> None:
        """Wait synchronously within the remaining budget."""
        time.sleep(self.delay(seconds))
        self.remaining()

    async def asleep(self, seconds: float | None) -> None:
        """Wait asynchronously within the remaining budget."""
        await asyncio.sleep(self.delay(seconds))
        self.remaining()
