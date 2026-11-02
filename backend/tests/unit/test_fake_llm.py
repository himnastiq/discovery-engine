"""Discovery Engine - FakeLLMClient unit tests (P13.5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from engine.llm import (
    FakeLLMClient,
    LLMAuthError,
    LLMBadOutput,
    LLMClient,
    LLMPick,
    LLMRateLimited,
    LLMRequest,
    LLMResult,
    LLMTimeout,
    LLMUpstreamError,
)


def test_fake_llm_satisfies_protocol() -> None:
    client = FakeLLMClient()
    assert isinstance(client, LLMClient)


def test_fake_llm_records_prompts_and_default_picks() -> None:
    client = FakeLLMClient()
    req = LLMRequest(
        system_instruction="system prompt",
        contents=[{"role": "user", "content": "find something good"}],
        candidate_ids=["cand_10", "cand_20", "cand_30", "cand_40"],
    )

    coro = client.complete(req)
    try:
        coro.send(None)
    except StopIteration as e:
        res: LLMResult = e.value

    assert client.call_count == 1
    assert len(client.history) == 1
    assert client.history[0] == req
    assert len(res.picks) == 3
    assert [p.item_id for p in res.picks] == ["cand_10", "cand_20", "cand_30"]
    assert "cand_10" in res.reply
    assert res.latency_ms > 0


def test_fake_llm_scripted_results() -> None:
    custom_pick = LLMPick(item_id="cand_custom", reason="Custom test reason")
    custom_res = LLMResult(
        reply="Custom answer",
        picks=[custom_pick],
        model="custom-test-model",
        latency_ms=10,
    )
    client = FakeLLMClient(scripted_results=[custom_res])

    req = LLMRequest("sys", [], ["cand_custom"])
    coro = client.complete(req)
    try:
        coro.send(None)
    except StopIteration as e:
        res = e.value

    assert res.reply == "Custom answer"
    assert res.picks[0].item_id == "cand_custom"
    assert res.model == "custom-test-model"


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: LLMRateLimited("Rate limited", retry_after=10.0),
        lambda: LLMAuthError("Invalid key"),
        lambda: LLMTimeout("Timed out"),
        lambda: LLMUpstreamError("500 Internal error"),
        lambda: LLMBadOutput("Output parsing failed"),
    ],
)
def test_fake_llm_raises_scripted_errors(error_factory: Callable[[], Exception]) -> None:
    expected_err = error_factory()
    client = FakeLLMClient(scripted_results=[expected_err])

    req = LLMRequest("sys", [], ["item_1"])
    coro = client.complete(req)
    with pytest.raises(type(expected_err)) as exc_info:
        coro.send(None)

    assert exc_info.value == expected_err
    assert client.call_count == 1


def test_fake_llm_reset() -> None:
    client = FakeLLMClient(scripted_results=[LLMTimeout()])
    client.history.append(LLMRequest("sys", [], []))
    client.call_count = 5

    client.reset()
    assert client.call_count == 0
    assert len(client.history) == 0
    assert len(client.scripted_results) == 0
