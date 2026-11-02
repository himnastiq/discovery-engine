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
from engine.llm.gemini import GeminiClient
from engine.llm.quota import QuotaManager
from engine.llm.types import (
    LLMClient,
    LLMPick,
    LLMRequest,
    LLMResult,
)

__all__ = [
    "FakeLLMClient",
    "GeminiClient",
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
    "QuotaManager",
]
