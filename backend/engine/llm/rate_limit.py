"""Discovery Engine - Per-IP Sliding Window Rate Limiter (P13.14).

Provides sliding-window rate limiting per client IP address with
accurate Retry-After cooldown calculation.
"""

from __future__ import annotations

import collections
import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class IPRateLimiter:
    """In-memory sliding-window request rate limiter per IP address."""

    def __init__(
        self,
        rpm: int = 6,
        window_s: float = 60.0,
        time_func: Callable[[], float] = time.time,
    ) -> None:
        """Initialize sliding window rate limiter.

        Args:
            rpm: Maximum allowed requests per IP within window_s.
            window_s: Sliding window duration in seconds (default 60.0).
            time_func: Injectable clock function.
        """
        self.rpm = rpm
        self.window_s = window_s
        self._time_func = time_func
        self._requests: dict[str, collections.deque[float]] = collections.defaultdict(
            collections.deque
        )

    def check_and_record(self, ip: str) -> tuple[bool, int]:
        """Check if request from ip is allowed, and record timestamp.

        Args:
            ip: Client IP address string.

        Returns:
            tuple[bool, int]: (is_allowed, retry_after_seconds)
        """
        now = self._time_func()
        q = self._requests[ip]
        cutoff = now - self.window_s

        # Evict timestamps outside the sliding window
        while q and q[0] <= cutoff:
            q.popleft()

        if len(q) >= self.rpm:
            oldest = q[0]
            retry_after = max(1, math.ceil(self.window_s - (now - oldest)))
            return False, retry_after

        q.append(now)
        return True, 0

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._requests.clear()
