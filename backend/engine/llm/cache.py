"""Discovery Engine - LLM Response Cache and In-Flight Coalescing (P13.13).

Provides:
1. Deterministic cache key generation over content type, user ID, normalized message,
   candidate IDs, and model.
2. TTL LRU cache with configurable expiration and capacity limits.
3. In-flight request coalescing (SingleFlight pattern): concurrent identical requests
   share a single upstream execution without duplicate LLM calls.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import re
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


def normalize_message(msg: str) -> str:
    """Normalize inquiry message: strip whitespace, collapse consecutive spaces, lowercase."""
    if not msg:
        return ""
    return re.sub(r"\s+", " ", msg.strip().lower())


def compute_cache_key(
    content_type: str,
    user_id: str | None,
    last_message: str,
    candidate_ids: list[str] | tuple[str, ...],
    model: str,
) -> str:
    """Compute deterministic SHA-256 cache key.

    Args:
        content_type: Content type identifier.
        user_id: String user ID, or None for anonymous user.
        last_message: Raw user query or inquiry string.
        candidate_ids: Sequence of candidate item IDs in candidate order.
        model: Model identifier.

    Returns:
        str: Hexadecimal SHA-256 digest representing this exact request context.
    """
    norm_type = content_type.strip().lower()
    norm_user = str(user_id).strip() if user_id is not None else "anonymous"
    norm_msg = normalize_message(last_message)
    cands_str = ",".join(str(c) for c in candidate_ids)
    norm_model = model.strip()

    raw_key = f"{norm_type}|{norm_user}|{norm_msg}|{cands_str}|{norm_model}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class ChatResponseCache:
    """In-memory TTL LRU cache with in-flight request coalescing."""

    def __init__(
        self,
        ttl_s: float = 600.0,
        max_size: int = 1000,
        time_func: Callable[[], float] = time.time,
    ) -> None:
        """Initialize cache with TTL, capacity, and injectable clock.

        Args:
            ttl_s: Time-to-live in seconds (default 600.0 = 10 minutes).
            max_size: Maximum entries before LRU eviction (default 1000).
            time_func: Clock function returning current epoch seconds.
        """
        self.ttl_s = ttl_s
        self.max_size = max_size
        self._time_func = time_func
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._inflight: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()

    def get(self, key: str) -> Any | None:
        """Retrieve unexpired value from cache, moving it to MRU position."""
        if key not in self._cache:
            return None

        val, expires_at = self._cache[key]
        now = self._time_func()
        if now >= expires_at:
            del self._cache[key]
            return None

        self._cache.move_to_end(key)
        return copy.deepcopy(val)

    def set(self, key: str, value: Any) -> None:
        """Store value in cache with TTL, evicting oldest item if at capacity."""
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        expires_at = self._time_func() + self.ttl_s
        self._cache[key] = (copy.deepcopy(value), expires_at)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Awaitable[T]],
    ) -> tuple[T, bool]:
        """Retrieve from cache or compute with in-flight coalescing.

        If another task is already computing for the same key, this task waits
        for the active computation to complete and returns the shared result.

        Args:
            key: Cache key.
            compute_fn: Async factory function producing the value if not cached.

        Returns:
            tuple[T, bool]: (result_value, is_cache_hit)
        """
        # 1. Fast path: check cache outside lock
        cached = self.get(key)
        if cached is not None:
            return cached, True

        # 2. Check or register in-flight future under lock
        async with self._lock:
            cached = self.get(key)
            if cached is not None:
                return cached, True

            if key in self._inflight:
                fut = self._inflight[key]
                is_leader = False
            else:
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                self._inflight[key] = fut
                is_leader = True

        # 3. Follower path: await leader's future
        if not is_leader:
            result = await fut
            return copy.deepcopy(result), True

        # 4. Leader path: execute computation and notify followers
        try:
            result = await compute_fn()
            self.set(key, result)
            fut.set_result(result)
            return copy.deepcopy(result), False
        except BaseException as exc:
            fut.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)
