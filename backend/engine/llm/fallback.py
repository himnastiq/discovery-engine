"""Discovery Engine - LLM Fallback Response Builder (P13.12).

Provides guaranteed graceful degradation when the LLM service experiences
rate limits, timeouts, upstream failures, authentication errors, or invalid outputs.
Returns candidate recommendations directly from the engine with mode="fallback".
Chat always answers with HTTP 200 unless the request itself is malformed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.llm.errors import (
    LLMAuthError,
    LLMBadOutput,
    LLMRateLimited,
    LLMTimeout,
    LLMUpstreamError,
)

if TYPE_CHECKING:
    from engine.schema import ContentTypeSpec


def map_error_to_fallback_reason(exc: Exception) -> tuple[str, int | None]:
    """Map an exception to standard fallback reason string and optional retry-after seconds."""
    if isinstance(exc, LLMRateLimited):
        retry_s = int(exc.retry_after) if exc.retry_after is not None else None
        return "rate_limited", retry_s
    if isinstance(exc, LLMTimeout):
        return "timeout", None
    if isinstance(exc, LLMAuthError):
        return "no_credentials", None
    if isinstance(exc, LLMBadOutput):
        return "bad_output", None
    if isinstance(exc, LLMUpstreamError):
        return "upstream_error", None
    return "upstream_error", None


def build_fallback_response(
    spec: ContentTypeSpec | None,
    candidates: list[dict[str, Any]],
    fallback_reason: str,
    model_name: str | None = None,
    latency_ms: int = 0,
    retry_after_s: int | None = None,
    k_picks: int = 3,
) -> dict[str, Any]:
    """Build a grounded engine-only fallback response.

    Args:
        spec: Optional ContentTypeSpec for domain-adapted phrasing.
        candidates: Candidate items pool assembled from the recommendation engine.
        fallback_reason: Reason code ("rate_limited", "timeout", "upstream_error",
                         "bad_output", "disabled", "no_credentials").
        model_name: Active model identifier (or None).
        latency_ms: Request elapsed time in milliseconds.
        retry_after_s: Recommended cooldown in seconds if rate limited.
        k_picks: Number of candidate items to include in picks (default 3, max 5).

    Returns:
        dict[str, Any]: Complete chat response with mode="fallback".
    """
    noun = spec.chat.noun if spec and spec.chat else "item"

    # Select friendly templated plain-text reply based on reason
    if fallback_reason == "rate_limited":
        reply = (
            f"Our AI concierge is currently experiencing high demand. "
            f"Here are top {noun} recommendations generated directly by the engine:"
        )
    elif fallback_reason == "timeout":
        reply = (
            f"The AI service took longer than expected to respond. "
            f"Here are top-ranked {noun} recommendations retrieved directly from the engine:"
        )
    elif fallback_reason in ("disabled", "no_credentials"):
        reply = f"Here are personalized {noun} recommendations served directly by the engine:"
    elif fallback_reason == "bad_output":
        reply = f"Here are verified {noun} recommendations directly from the discovery engine:"
    else:  # upstream_error or generic
        reply = (
            f"Our AI assistant is temporarily unavailable. "
            f"Here are top {noun} recommendations directly from the engine:"
        )

    if not candidates:
        reply = f"No matching {noun} recommendations could be retrieved from the catalogue at this time."

    num_picks = min(max(k_picks, 1), 5)
    selected_candidates = candidates[:num_picks]

    picks: list[dict[str, Any]] = []
    for idx, c in enumerate(selected_candidates, start=1):
        item_id = str(c.get("item_id", ""))
        rank = int(c.get("candidate_rank", idx))
        picks.append(
            {
                "item_id": item_id,
                "title": str(c.get("title", item_id)),
                "subtitle": c.get("subtitle"),
                "categories": list(c.get("categories", [])),
                "year": c.get("year"),
                "reason": f"Top recommendation from the engine's ranking algorithm (Rank #{rank}).",
                "rank": rank,
            }
        )

    return {
        "reply": reply,
        "picks": picks,
        "mode": "fallback",
        "meta": {
            "model": model_name,
            "latency_ms": latency_ms,
            "cache_hit": False,
            "fallback_reason": fallback_reason,
            "retry_after_s": retry_after_s,
        },
    }
