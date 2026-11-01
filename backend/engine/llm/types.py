"""Discovery Engine - LLM type definitions and protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMPick:
    """Individual item picked by the LLM from engine candidates."""

    item_id: str
    reason: str


@dataclass(frozen=True)
class LLMRequest:
    """Request payload for completion by an LLM client."""

    system_instruction: str
    contents: list[dict[str, Any]]
    candidate_ids: list[str]
    max_output_tokens: int = 512
    temperature: float = 0.7


@dataclass(frozen=True)
class LLMResult:
    """Structured response produced by an LLM client."""

    reply: str
    picks: list[LLMPick]
    model: str
    latency_ms: int
    raw_text: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol implemented by LLM backend adapters."""

    async def complete(self, request: LLMRequest) -> LLMResult:
        """Complete an LLM request asynchronously and return structured picks."""
        ...
