"""Discovery Engine - GeminiClient unit and security tests (P13.6)."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import TYPE_CHECKING

import httpx
import pytest

from engine.llm import (
    GeminiClient,
    LLMAuthError,
    LLMBadOutput,
    LLMClient,
    LLMRateLimited,
    LLMRequest,
    LLMTimeout,
    LLMUpstreamError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SECRET_KEY = "AIzaSySecretKeyNeverLeak123456789"


def test_gemini_client_protocol_and_representation() -> None:
    client = GeminiClient(api_key=SECRET_KEY, model="gemini-2.5-flash")
    assert isinstance(client, LLMClient)

    # Key must NOT appear in repr or str
    repr_str = repr(client)
    str_str = str(client)
    assert SECRET_KEY not in repr_str
    assert SECRET_KEY not in str_str
    assert "AIza...6789" in repr_str


def make_mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def test_gemini_client_success_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Check header authentication (never query param)
        assert request.headers.get("x-goog-api-key") == SECRET_KEY
        assert "key=" not in str(request.url)

        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"

        response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "reply": "Here is a top sci-fi pick.",
                                        "picks": [
                                            {
                                                "item_id": "item_123",
                                                "reason": "Matches your interest in classic sci-fi.",
                                            }
                                        ],
                                    }
                                )
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        return httpx.Response(200, json=response_payload)

    mock_http = make_mock_client(handler)
    client = GeminiClient(api_key=SECRET_KEY, client=mock_http)

    req = LLMRequest(
        system_instruction="System prompt",
        contents=[{"role": "user", "content": "hello"}],
        candidate_ids=["item_123", "item_456"],
    )

    coro = client.complete(req)
    try:
        coro.send(None)
    except StopIteration as e:
        res = e.value

    assert res.reply == "Here is a top sci-fi pick."
    assert len(res.picks) == 1
    assert res.picks[0].item_id == "item_123"
    assert res.picks[0].reason == "Matches your interest in classic sci-fi."
    assert res.model == "gemini-2.5-flash"
    assert res.latency_ms >= 0


def test_gemini_client_rate_limited_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"retry-after": "15"},
            json={
                "error": {
                    "code": 429,
                    "message": "Resource exhausted",
                    "details": [
                        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "15s"}
                    ],
                }
            },
        )

    client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(handler))
    req = LLMRequest("sys", [], ["item_1"])

    coro = client.complete(req)
    with pytest.raises(LLMRateLimited) as exc_info:
        coro.send(None)

    assert exc_info.value.retry_after == 15.0


@pytest.mark.parametrize("status_code", [401, 403])
def test_gemini_client_auth_error_401_403(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"message": "API key not valid."}})

    client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(handler))
    req = LLMRequest("sys", [], ["item_1"])

    coro = client.complete(req)
    with pytest.raises(LLMAuthError):
        coro.send(None)


@pytest.mark.parametrize("status_code", [500, 503])
def test_gemini_client_upstream_error_5xx(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="Internal Server Error")

    client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(handler))
    req = LLMRequest("sys", [], ["item_1"])

    coro = client.complete(req)
    with pytest.raises(LLMUpstreamError):
        coro.send(None)


def test_gemini_client_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(handler))
    req = LLMRequest("sys", [], ["item_1"])

    coro = client.complete(req)
    with pytest.raises(LLMTimeout):
        coro.send(None)


def test_gemini_client_malformed_json_bad_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Not valid JSON at all {"}]}}]},
        )

    client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(handler))
    req = LLMRequest("sys", [], ["item_1"])

    coro = client.complete(req)
    with pytest.raises(LLMBadOutput):
        coro.send(None)


def test_gemini_client_zero_secrets_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Quality Gate R11 & P13.6: Verify zero key material appears in logs across all scenarios."""
    caplog.set_level(logging.DEBUG)

    handlers = [
        lambda req: httpx.Response(401, json={"error": {"message": "Invalid key"}}),
        lambda req: httpx.Response(
            429, headers={"retry-after": "5"}, json={"error": {"message": "quota"}}
        ),
        lambda req: httpx.Response(500, text="error"),
        lambda req: httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
        ),
    ]

    for h in handlers:
        client = GeminiClient(api_key=SECRET_KEY, client=make_mock_client(h))
        req = LLMRequest("sys", [], ["item_1"])
        with contextlib.suppress(Exception):
            client.complete(req).send(None)

    # Assert SECRET_KEY never appears in captured log text
    assert SECRET_KEY not in caplog.text
    # But safe masked fingerprint can be present
    assert "AIza...6789" in caplog.text
