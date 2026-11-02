"""Discovery Engine - Health-aware QuotaManager across GCP projects (P13.7)."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("engine.llm.quota")


def _mask_key(key: str) -> str:
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


@dataclass
class ProjectBucket:
    """Bucket representing a distinct Google Cloud project with its own quota pool."""

    project_id: str
    keys: list[str]
    rpm: float = 10.0
    disabled_keys: set[str] = field(default_factory=set)
    key_cursor: int = 0
    tokens: float = 10.0
    last_token_update: float = 0.0
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    disabled: bool = False

    def refill_tokens(self, now: float) -> None:
        """Refill tokens based on elapsed time since last update."""
        if self.last_token_update <= 0.0:
            self.last_token_update = now
            self.tokens = self.rpm
            return

        elapsed = max(0.0, now - self.last_token_update)
        fill_rate = self.rpm / 60.0
        self.tokens = min(self.rpm, self.tokens + elapsed * fill_rate)
        self.last_token_update = now


class QuotaManager:
    """Health-aware rate-limiter and round-robin credential router across GCP projects."""

    def __init__(
        self,
        api_keys: list[str],
        projects: list[str] | None = None,
        rpm_per_project: float = 10.0,
        clock: Callable[[], float] | None = None,
        rng: Callable[[], float] | None = None,
    ) -> None:
        self._clock = clock or time.time
        self._rng = rng or random.random
        self.rpm_per_project = max(1.0, float(rpm_per_project))
        self._lock = asyncio.Lock()
        self._bucket_cursor: int = 0

        # Group keys by project label (unlabelled keys form one shared bucket 'default')
        project_map: dict[str, list[str]] = {}
        if projects and len(projects) == len(api_keys):
            for key, prj in zip(api_keys, projects, strict=False):
                clean_k = key.strip()
                clean_p = prj.strip() or "default"
                if clean_k:
                    project_map.setdefault(clean_p, []).append(clean_k)
        else:
            # All keys map to a single project bucket
            clean_keys = [k.strip() for k in api_keys if k.strip()]
            if clean_keys:
                project_map["default"] = clean_keys

        now = self._clock()
        self.buckets: list[ProjectBucket] = [
            ProjectBucket(
                project_id=prj,
                keys=keys,
                rpm=self.rpm_per_project,
                tokens=self.rpm_per_project,
                last_token_update=now,
            )
            for prj, keys in project_map.items()
        ]

    def __repr__(self) -> str:
        return (
            f"QuotaManager(projects={len(self.buckets)}, "
            f"rpm_per_project={self.rpm_per_project}, "
            f"active_buckets={sum(1 for b in self.buckets if not b.disabled)})"
        )

    def pick_credential_sync(self) -> tuple[str | None, str | None, float | None]:
        """Synchronously pick a ready credential bucket or return the earliest ready delay.

        Returns: (api_key, project_id, retry_after_s)
        """
        if not self.buckets:
            return None, None, None

        now = self._clock()
        n = len(self.buckets)
        earliest_wait: float | None = None

        for i in range(n):
            idx = (self._bucket_cursor + i) % n
            b = self.buckets[idx]

            if b.disabled or not b.keys:
                continue

            # Check cooldown
            if now < b.cooldown_until:
                wait_time = b.cooldown_until - now
                earliest_wait = min(earliest_wait, wait_time) if earliest_wait is not None else wait_time
                continue

            # Check token bucket
            b.refill_tokens(now)
            if b.tokens >= 1.0:
                b.tokens -= 1.0
                # Round-robin key selection within project
                key_idx = b.key_cursor % len(b.keys)
                selected_key = b.keys[key_idx]
                b.key_cursor = (b.key_cursor + 1) % len(b.keys)
                self._bucket_cursor = (idx + 1) % n
                return selected_key, b.project_id, None
            else:
                fill_rate = b.rpm / 60.0
                tokens_needed = 1.0 - b.tokens
                token_wait = tokens_needed / fill_rate if fill_rate > 0 else 60.0
                earliest_wait = min(earliest_wait, token_wait) if earliest_wait is not None else token_wait

        return None, None, earliest_wait

    async def pick_credential(self) -> tuple[str | None, str | None, float | None]:
        """Asynchronously pick a ready credential under concurrency lock."""
        async with self._lock:
            return self.pick_credential_sync()

    def record_success(self, project_id: str) -> None:
        """Reset consecutive failures on successful 2xx request."""
        for b in self.buckets:
            if b.project_id == project_id:
                b.consecutive_failures = 0
                return

    def record_rate_limited(self, project_id: str, retry_after: float | None = None) -> None:
        """Apply backoff, cooldown, and jitter on HTTP 429 rate limit."""
        now = self._clock()
        for b in self.buckets:
            if b.project_id == project_id:
                b.consecutive_failures += 1
                base_backoff = min(300.0, 2.0 ** min(b.consecutive_failures, 8))
                calc_delay = max(float(retry_after or 0.0), base_backoff)
                # 0 to 20% jitter
                jitter = calc_delay * 0.20 * self._rng()
                total_delay = min(300.0, calc_delay + jitter)
                b.cooldown_until = now + total_delay
                logger.warning(
                    "Project bucket '%s' cooling down for %.1fs (failures=%d)",
                    project_id,
                    total_delay,
                    b.consecutive_failures,
                )
                return

    def record_auth_error(self, project_id: str, key: str) -> None:
        """Disable a rejected API key; disable bucket if all keys are invalid."""
        for b in self.buckets:
            if b.project_id == project_id:
                if key in b.keys:
                    b.keys.remove(key)
                    b.disabled_keys.add(key)
                    logger.error(
                        "Disabled invalid API key %s in project '%s'",
                        _mask_key(key),
                        project_id,
                    )
                if not b.keys:
                    b.disabled = True
                    logger.error("Project bucket '%s' disabled (zero active keys)", project_id)
                return

    def record_upstream_error(self, project_id: str) -> None:
        """Apply short cooldown (2-10s with backoff) on 5xx or network timeout."""
        now = self._clock()
        for b in self.buckets:
            if b.project_id == project_id:
                b.consecutive_failures += 1
                delay = min(10.0, 2.0 + 2.0 * b.consecutive_failures)
                b.cooldown_until = now + delay
                logger.warning(
                    "Project bucket '%s' upstream error cooldown for %.1fs",
                    project_id,
                    delay,
                )
                return
