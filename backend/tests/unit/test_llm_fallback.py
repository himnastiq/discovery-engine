"""Discovery Engine - LLM Fallback Response Builder Tests (P13.12).

Verifies:
1. Error mapping maps every error class to its exact canonical fallback_reason.
2. Every failure mode of FakeLLMClient produces a valid HTTP 200 fallback response body.
3. Fallback picks are strictly grounded in engine candidates with candidate rank.
4. Edge cases like empty candidates pool degrade gracefully without crashing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from engine.config import load_config
from engine.llm.errors import (
    LLMAuthError,
    LLMBadOutput,
    LLMRateLimited,
    LLMTimeout,
    LLMUpstreamError,
)
from engine.llm.fake import FakeLLMClient
from engine.llm.fallback import build_fallback_response, map_error_to_fallback_reason
from engine.llm.types import LLMRequest


@pytest.fixture
def sample_candidates() -> list[dict[str, Any]]:
    return [
        {
            "item_id": f"item_{i}",
            "title": f"Candidate Title {i}",
            "subtitle": f"Subtitle {i}",
            "categories": ["Action"],
            "year": 2020,
            "candidate_rank": i,
        }
        for i in range(1, 10)
    ]


def test_map_error_to_fallback_reason() -> None:
    """Verifies that typed LLM exceptions map to standard fallback reasons."""
    r_lim, retry = map_error_to_fallback_reason(LLMRateLimited(retry_after=12.5))
    assert r_lim == "rate_limited"
    assert retry == 12

    r_timeout, _ = map_error_to_fallback_reason(LLMTimeout())
    assert r_timeout == "timeout"

    r_auth, _ = map_error_to_fallback_reason(LLMAuthError())
    assert r_auth == "no_credentials"

    r_upstream, _ = map_error_to_fallback_reason(LLMUpstreamError())
    assert r_upstream == "upstream_error"

    r_bad, _ = map_error_to_fallback_reason(LLMBadOutput())
    assert r_bad == "bad_output"

    r_generic, _ = map_error_to_fallback_reason(RuntimeError("Unexpected"))
    assert r_generic == "upstream_error"


@pytest.mark.parametrize(
    ("reason", "expected_phrase"),
    [
        ("rate_limited", "high demand"),
        ("timeout", "longer than expected"),
        ("disabled", "directly by the engine"),
        ("no_credentials", "directly by the engine"),
        ("bad_output", "verified"),
        ("upstream_error", "temporarily unavailable"),
    ],
)
def test_build_fallback_response_phrasing(
    reason: str,
    expected_phrase: str,
    sample_candidates: list[dict[str, Any]],
) -> None:
    """Verifies that templated fallback responses are informative and plain-text."""
    spec = load_config("toy")
    res = build_fallback_response(
        spec=spec,
        candidates=sample_candidates,
        fallback_reason=reason,
        model_name="gemini-2.5-flash",
        latency_ms=120,
        retry_after_s=15 if reason == "rate_limited" else None,
        k_picks=3,
    )

    assert res["mode"] == "fallback"
    assert expected_phrase in res["reply"]
    assert len(res["picks"]) == 3
    assert res["meta"]["fallback_reason"] == reason
    assert res["meta"]["model"] == "gemini-2.5-flash"
    assert res["meta"]["latency_ms"] == 120
    if reason == "rate_limited":
        assert res["meta"]["retry_after_s"] == 15

    for idx, pick in enumerate(res["picks"], start=1):
        assert pick["item_id"] == f"item_{idx}"
        assert pick["rank"] == idx
        assert "Rank #" in pick["reason"]


def test_build_fallback_response_empty_candidates() -> None:
    """Empty candidates pool yields empty picks list without throwing."""
    spec = load_config("toy")
    res = build_fallback_response(
        spec=spec,
        candidates=[],
        fallback_reason="upstream_error",
    )
    assert res["mode"] == "fallback"
    assert len(res["picks"]) == 0
    assert "No matching" in res["reply"]


@pytest.mark.parametrize(
    ("fake_error", "expected_reason", "expected_retry"),
    [
        (LLMRateLimited(retry_after=30), "rate_limited", 30),
        (LLMTimeout(), "timeout", None),
        (LLMAuthError(), "no_credentials", None),
        (LLMUpstreamError(), "upstream_error", None),
        (LLMBadOutput(), "bad_output", None),
    ],
)
def test_all_fake_llm_client_failures_yield_valid_fallback(
    fake_error: Exception,
    expected_reason: str,
    expected_retry: int | None,
    sample_candidates: list[dict[str, Any]],
) -> None:
    """Simulates pipeline execution where FakeLLMClient errors are caught and transformed to fallback."""
    spec = load_config("toy")
    client = FakeLLMClient(scripted_results=[fake_error])
    req = LLMRequest(
        system_instruction="sys",
        contents=[{"role": "user", "parts": [{"text": "hello"}]}],
        candidate_ids=["item_1"],
    )

    try:
        asyncio.run(client.complete(req))
        pytest.fail("Client should have raised error")
    except Exception as exc:
        reason, retry_s = map_error_to_fallback_reason(exc)
        fallback = build_fallback_response(
            spec=spec,
            candidates=sample_candidates,
            fallback_reason=reason,
            retry_after_s=retry_s,
        )

        assert fallback["mode"] == "fallback"
        assert fallback["meta"]["fallback_reason"] == expected_reason
        assert fallback["meta"]["retry_after_s"] == expected_retry
        assert len(fallback["picks"]) > 0
