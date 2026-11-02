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
from engine.llm.settings import ChatSettings, load_chat_settings, log_chat_startup
from engine.llm.types import (
    LLMClient,
    LLMPick,
    LLMRequest,
    LLMResult,
)

__all__ = [
    "ChatSettings",
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
    "load_chat_settings",
    "log_chat_startup",
]
