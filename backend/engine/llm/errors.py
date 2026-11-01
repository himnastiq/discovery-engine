"""Discovery Engine - LLM exception hierarchy."""

from __future__ import annotations

from engine.errors import DiscoveryEngineError


class LLMError(DiscoveryEngineError):
    """Base exception for LLM operations."""


class LLMRateLimited(LLMError):  # noqa: N818
    """Raised when upstream LLM service signals rate limiting (429 or quota)."""

    def __init__(
        self,
        message: str = "Upstream LLM rate limit reached.",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMAuthError(LLMError):
    """Raised when LLM authentication credentials are missing or rejected (401/403)."""


class LLMTimeout(LLMError):  # noqa: N818
    """Raised when an upstream LLM request times out."""


class LLMUpstreamError(LLMError):
    """Raised when the upstream LLM service fails (5xx, network error)."""


class LLMBadOutput(LLMError):  # noqa: N818
    """Raised when the LLM output violates schema, syntax, or candidate boundaries."""
