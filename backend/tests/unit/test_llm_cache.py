"""Discovery Engine - LLM Response Cache and Coalescing Tests (P13.13).

Verifies:
1. Cache key normalization and deterministic SHA-256 generation.
2. TTL expiration and LRU capacity eviction.
3. Second call is a cache hit with zero upstream calls.
4. 5 concurrent identical requests make exactly 1 upstream call (SingleFlight coalescing).
5. Error propagation during coalesced requests cleans up state.
"""

from __future__ import annotations

import asyncio
from typing import Any

from engine.llm.cache import ChatResponseCache, compute_cache_key, normalize_message


def test_normalize_message() -> None:
    """Whitespace collapsing and lowercase normalization."""
    assert normalize_message("  Recommend  Something   Nice ") == "recommend something nice"
    assert normalize_message("") == ""
    assert normalize_message("   ") == ""


def test_compute_cache_key_deterministic_and_sensitive() -> None:
    """Keys are invariant to whitespace variations in message but sensitive to parameters."""
    k1 = compute_cache_key("toy", "u1", "Find Action", ["i1", "i2"], "gemini-2.5-flash")
    k2 = compute_cache_key("toy", "u1", "  find   action  ", ["i1", "i2"], "gemini-2.5-flash")
    assert k1 == k2

    # Different user
    k3 = compute_cache_key("toy", "u2", "Find Action", ["i1", "i2"], "gemini-2.5-flash")
    assert k1 != k3

    # Different candidate order or content
    k4 = compute_cache_key("toy", "u1", "Find Action", ["i2", "i1"], "gemini-2.5-flash")
    assert k1 != k4

    # Anonymous user
    k5 = compute_cache_key("toy", None, "Find Action", ["i1", "i2"], "gemini-2.5-flash")
    assert k1 != k5


def test_cache_ttl_and_lru() -> None:
    """TTL expiration and LRU eviction with fake clock."""
    fake_time = 1000.0

    def clock() -> float:
        return fake_time

    cache = ChatResponseCache(ttl_s=10.0, max_size=2, time_func=clock)

    cache.set("k1", {"val": 1})
    cache.set("k2", {"val": 2})

    assert cache.get("k1") == {"val": 1}
    assert cache.get("k2") == {"val": 2}

    # Advance clock past TTL
    fake_time += 11.0
    assert cache.get("k1") is None
    assert cache.get("k2") is None

    # Test LRU eviction: capacity 2
    fake_time = 2000.0
    cache.set("k1", 1)
    cache.set("k2", 2)
    # Touch k1 to make k2 the oldest
    assert cache.get("k1") == 1
    # Insert k3: k2 should be evicted
    cache.set("k3", 3)
    assert cache.get("k1") == 1
    assert cache.get("k2") is None
    assert cache.get("k3") == 3


def test_second_call_is_cache_hit_with_zero_upstream_calls() -> None:
    """Acceptance: second call is a cache hit with zero upstream calls."""

    async def run() -> None:
        cache = ChatResponseCache(ttl_s=60.0)
        upstream_calls = 0

        async def mock_compute() -> dict[str, Any]:
            nonlocal upstream_calls
            upstream_calls += 1
            return {"reply": "computed response", "picks": []}

        key = "test_key_1"

        # Call 1: Miss, executes compute_fn
        res1, hit1 = await cache.get_or_compute(key, mock_compute)
        assert hit1 is False
        assert upstream_calls == 1
        assert res1["reply"] == "computed response"

        # Call 2: Hit, zero upstream calls
        res2, hit2 = await cache.get_or_compute(key, mock_compute)
        assert hit2 is True
        assert upstream_calls == 1  # Still 1!
        assert res2 == res1

    asyncio.run(run())


def test_five_concurrent_identical_requests_make_one_upstream_call() -> None:
    """Acceptance: 5 concurrent identical requests make exactly 1 upstream call."""

    async def run() -> None:
        cache = ChatResponseCache(ttl_s=60.0)
        upstream_calls = 0

        async def slow_compute() -> dict[str, Any]:
            nonlocal upstream_calls
            upstream_calls += 1
            await asyncio.sleep(0.05)  # simulate upstream API latency
            return {"reply": "coalesced response", "count": upstream_calls}

        key = "concurrent_key"

        # Launch 5 concurrent calls
        tasks = [cache.get_or_compute(key, slow_compute) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all 5 received identical result
        assert len(results) == 5
        for res, _ in results:
            assert res["reply"] == "coalesced response"
            assert res["count"] == 1

        # Exactly 1 upstream call was made
        assert upstream_calls == 1

        # Exactly 1 was leader (hit=False) and 4 were followers (hit=True)
        hits = [hit for _, hit in results]
        assert hits.count(False) == 1
        assert hits.count(True) == 4

    asyncio.run(run())


def test_coalescing_error_propagation_and_cleanup() -> None:
    """If the leader fails, all concurrent tasks receive the error and state cleans up."""

    async def run() -> None:
        cache = ChatResponseCache(ttl_s=60.0)

        async def failing_compute() -> dict[str, Any]:
            await asyncio.sleep(0.02)
            raise RuntimeError("Upstream failure")

        key = "failing_key"
        tasks = [cache.get_or_compute(key, failing_compute) for _ in range(3)]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 3
        for exc in results:
            assert isinstance(exc, RuntimeError)
            assert str(exc) == "Upstream failure"

        # Cache should not store failing result
        assert cache.get(key) is None
        # In-flight map must be empty
        assert len(cache._inflight) == 0

    asyncio.run(run())
