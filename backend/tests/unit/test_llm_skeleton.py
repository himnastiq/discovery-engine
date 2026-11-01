"""Discovery Engine - LLM skeleton protocol and error tests (P13.4)."""

from __future__ import annotations

import asyncio

from engine.llm import (
    LLMAuthError,
    LLMBadOutput,
    LLMClient,
    LLMError,
    LLMPick,
    LLMRateLimited,
    LLMRequest,
    LLMResult,
    LLMTimeout,
    LLMUpstreamError,
)


class DummyClient:
    async def complete(self, request: LLMRequest) -> LLMResult:
        return LLMResult(
            reply="dummy reply",
            picks=[LLMPick(item_id=request.candidate_ids[0], reason="dummy reason")],
            model="dummy-model",
            latency_ms=42,
        )


def test_llm_client_protocol_satisfaction() -> None:
    client = DummyClient()
    assert isinstance(client, LLMClient)

    req = LLMRequest(
        system_instruction="system prompt",
        contents=[{"role": "user", "parts": [{"text": "hello"}]}],
        candidate_ids=["item_1", "item_2"],
    )
    res = asyncio.run(client.complete(req))
    assert res.reply == "dummy reply"
    assert len(res.picks) == 1
    assert res.picks[0].item_id == "item_1"
    assert res.picks[0].reason == "dummy reason"
    assert res.latency_ms == 42


def test_llm_typed_errors_hierarchy() -> None:
    rate_err = LLMRateLimited("Rate limited", retry_after=12.5)
    assert isinstance(rate_err, LLMError)
    assert rate_err.retry_after == 12.5

    auth_err = LLMAuthError("Invalid API key")
    assert isinstance(auth_err, LLMError)

    timeout_err = LLMTimeout("Upstream timed out")
    assert isinstance(timeout_err, LLMError)

    upstream_err = LLMUpstreamError("503 Service Unavailable")
    assert isinstance(upstream_err, LLMError)

    bad_output_err = LLMBadOutput("Bad JSON schema")
    assert isinstance(bad_output_err, LLMError)
