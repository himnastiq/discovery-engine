"""Discovery Engine - LLM integration subsystem."""

from __future__ import annotations

from engine.llm.errors import (
    LLMAuthError,
    LLMBadOutput,
    LLMError,
    LLMRateLimited,
    LLMTimeout,
    LLMUpstreamError,
)
from engine.llm.fake import FakeLLMClient
from engine.llm.types import (
    LLMClient,
    LLMPick,
    LLMRequest,
    LLMResult,
)

__all__ = [
    "FakeLLMClient",
    "LLMAuthError",
    "LLMBadOutput",
    "LLMClient",
    "LLMError",
    "LLMPick",
    "LLMRateLimited",
    "LLMRequest",
    "LLMResult",
    "LLMTimeout",
    "LLMUpstreamError",
]
