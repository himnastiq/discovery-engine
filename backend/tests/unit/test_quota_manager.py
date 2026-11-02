"""Discovery Engine - QuotaManager unit, concurrency, and property tests (P13.7)."""

from __future__ import annotations

import asyncio

from hypothesis import given
from hypothesis import strategies as st

from engine.llm import QuotaManager


class FakeClock:
    """Controllable clock for deterministic time manipulation in tests."""

    def __init__(self, start_time: float = 1000.0) -> None:
        self.current_time = start_time

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


def test_same_project_keys_collapse_into_one_bucket() -> None:
    """Multiple keys belonging to the same project share one bucket (zero extra quota)."""
    clock = FakeClock()
    keys = ["key_a1", "key_a2", "key_a3"]
    projects = ["project_alpha", "project_alpha", "project_alpha"]

    manager = QuotaManager(
        api_keys=keys,
        projects=projects,
        rpm_per_project=2.0,  # Only 2 requests per minute allowed
        clock=clock.time,
        rng=lambda: 0.0,
    )

    assert len(manager.buckets) == 1
    bucket = manager.buckets[0]
    assert bucket.project_id == "project_alpha"
    assert len(bucket.keys) == 3

    # First request
    k1, p1, _ = manager.pick_credential_sync()
    assert k1 == "key_a1"
    assert p1 == "project_alpha"

    # Second request
    k2, p2, _ = manager.pick_credential_sync()
    assert k2 == "key_a2"
    assert p2 == "project_alpha"

    # Third request blocked: token capacity consumed (no extra capacity from having 3 keys)
    k3, p3, wait_s = manager.pick_credential_sync()
    assert k3 is None
    assert p3 is None
    assert wait_s is not None and wait_s > 0


def test_round_robin_across_separate_projects() -> None:
    """Keys from distinct projects round-robin and each bucket has independent capacity."""
    clock = FakeClock()
    keys = ["key_p1", "key_p2"]
    projects = ["proj_one", "proj_two"]

    manager = QuotaManager(
        api_keys=keys,
        projects=projects,
        rpm_per_project=10.0,
        clock=clock.time,
        rng=lambda: 0.0,
    )

    assert len(manager.buckets) == 2

    k1, p1, _ = manager.pick_credential_sync()
    assert p1 == "proj_one"
    assert k1 == "key_p1"

    k2, p2, _ = manager.pick_credential_sync()
    assert p2 == "proj_two"
    assert k2 == "key_p2"

    k3, _p3, _ = manager.pick_credential_sync()
    assert p1 == "proj_one"
    assert k3 == "key_p1"


def test_rate_limited_cooldown_honours_retry_after_and_backoff_jitter() -> None:
    clock = FakeClock()
    keys = ["key_1"]
    projects = ["proj_1"]

    # Mock RNG returning 0.5 (representing 10% jitter since max is 20%)
    manager = QuotaManager(
        api_keys=keys,
        projects=projects,
        rpm_per_project=10.0,
        clock=clock.time,
        rng=lambda: 0.5,
    )

    k, p, _ = manager.pick_credential_sync()
    assert k == "key_1"
    assert p == "proj_1"

    # Trigger 429 with retry_after = 20s
    manager.record_rate_limited("proj_1", retry_after=20.0)
    # calc_delay = max(20.0, 2.0^1) = 20.0; jitter = 20 * 0.20 * 0.5 = 2.0; total = 22.0
    k_wait, _, wait_s = manager.pick_credential_sync()
    assert k_wait is None
    assert wait_s is not None and round(wait_s, 1) == 22.0

    # Advance clock by 10s -> still cooling down
    clock.advance(10.0)
    k_still_wait, _, wait_remain = manager.pick_credential_sync()
    assert k_still_wait is None
    assert wait_remain is not None and round(wait_remain, 1) == 12.0

    # Advance clock by 13s -> available again
    clock.advance(13.0)
    k_ready, p_ready, _ = manager.pick_credential_sync()
    assert k_ready == "key_1"
    assert p_ready == "proj_1"


def test_auth_error_disables_key_and_bucket() -> None:
    clock = FakeClock()
    keys = ["key_bad", "key_good"]
    projects = ["proj_single", "proj_single"]

    manager = QuotaManager(
        api_keys=keys,
        projects=projects,
        rpm_per_project=10.0,
        clock=clock.time,
        rng=lambda: 0.0,
    )

    # Disable key_bad
    manager.record_auth_error("proj_single", "key_bad")
    bucket = manager.buckets[0]
    assert "key_bad" not in bucket.keys
    assert "key_bad" in bucket.disabled_keys
    assert not bucket.disabled  # Still has key_good

    # Next pick must return key_good
    k1, _, _ = manager.pick_credential_sync()
    assert k1 == "key_good"

    # Disable key_good
    manager.record_auth_error("proj_single", "key_good")
    assert bucket.disabled  # Bucket now fully disabled

    # All buckets disabled returns None, None, None
    k_none, p_none, wait_none = manager.pick_credential_sync()
    assert k_none is None
    assert p_none is None
    assert wait_none is None


def test_all_cooling_returns_none_with_earliest_ready_time() -> None:
    clock = FakeClock()
    manager = QuotaManager(
        api_keys=["k1", "k2"],
        projects=["p1", "p2"],
        rpm_per_project=10.0,
        clock=clock.time,
        rng=lambda: 0.0,
    )

    manager.record_rate_limited("p1", retry_after=30.0)
    manager.record_rate_limited("p2", retry_after=10.0)

    k, p, wait_s = manager.pick_credential_sync()
    assert k is None
    assert p is None
    # Earliest ready time should be 10.0s (p2)
    assert wait_s is not None and round(wait_s, 1) == 10.0


def test_concurrent_callers_respect_capacity() -> None:
    clock = FakeClock()
    rpm = 5.0
    manager = QuotaManager(
        api_keys=["k1"],
        projects=["p1"],
        rpm_per_project=rpm,
        clock=clock.time,
        rng=lambda: 0.0,
    )

    async def run_concurrent() -> list[tuple[str | None, str | None, float | None]]:
        tasks = [manager.pick_credential() for _ in range(10)]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_concurrent())
    successes = [r for r in results if r[0] is not None]
    throttled = [r for r in results if r[0] is None]

    # Exactly 5 successes allowed by token bucket capacity
    assert len(successes) == int(rpm)
    assert len(throttled) == 5
    for t in throttled:
        assert t[2] is not None and t[2] > 0


@given(
    num_projects=st.integers(min_value=1, max_value=5),
    rpm=st.floats(min_value=1.0, max_value=60.0),
    time_advances=st.lists(st.floats(min_value=0.0, max_value=120.0), max_size=10),
)
def test_quota_manager_hypothesis_invariants(
    num_projects: int, rpm: float, time_advances: list[float]
) -> None:
    """Hypothesis property test asserting state invariants across random actions."""
    clock = FakeClock()
    keys = [f"k_{i}" for i in range(num_projects)]
    projects = [f"proj_{i}" for i in range(num_projects)]

    manager = QuotaManager(
        api_keys=keys,
        projects=projects,
        rpm_per_project=rpm,
        clock=clock.time,
    )

    for dt in time_advances:
        clock.advance(dt)
        k, p, wait_s = manager.pick_credential_sync()

        # Invariant 1: tokens never exceed capacity (rpm)
        for b in manager.buckets:
            assert b.tokens <= b.rpm + 1e-6
            assert b.tokens >= -1e-6

        # Invariant 2: if a key is picked, it must belong to an active bucket
        if k is not None:
            assert p is not None
            bucket = next(b for b in manager.buckets if b.project_id == p)
            assert not bucket.disabled
            assert k in bucket.keys
            assert wait_s is None
        else:
            # If no key picked, either all buckets disabled or waiting
            active = [b for b in manager.buckets if not b.disabled and b.keys]
            if active:
                assert wait_s is not None
