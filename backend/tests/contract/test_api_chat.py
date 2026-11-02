"""Discovery Engine - Chatbot Contract Tests (Phase 13, P13.14).

Verifies:
1. GET /v1/chat/status: configuration and readiness contract.
2. POST /v1/chat: successful completion across all public content types (movies, products, articles).
3. Grounding invariant: all returned picks exist in engine catalogue with authentic metadata.
4. Anonymous user and known persona users are supported.
5. Cache hit behavior on repeated requests.
6. Unified error handling:
   - 404 unknown_type
   - 404 unknown_user
   - 503 chat_unavailable when disabled
   - 422 validation_error for malformed requests (empty, oversize, bad role, non-user last message)
   - 429 chat_rate_limited with Retry-After header on IP limit
7. Graceful degradation: all upstream LLM failures return HTTP 200 with mode="fallback".
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.schemas import ChatResponse, ChatStatusResponse
from engine import registry
from engine.llm.errors import (
    LLMAuthError,
    LLMBadOutput,
    LLMRateLimited,
    LLMTimeout,
)
from engine.llm.fake import FakeLLMClient
from engine.llm.settings import ChatSettings
from engine.llm.types import LLMResult


@pytest.fixture(scope="module")
def app_instance() -> Any:
    """Create test application instance with loaded artifacts."""
    app = create_app()
    return app


@pytest.fixture
def client(app_instance: Any) -> Any:
    """TestClient with FakeLLMClient attached and reset between tests."""
    with TestClient(app_instance) as c:
        app_instance.state.chat_settings = ChatSettings(
            enabled=True,
            api_keys=["test-key-fake"],
            model="gemini-2.5-flash",
            ip_rpm=10,
            cache_ttl_s=600,
        )
        fake_client = FakeLLMClient(default_model="gemini-2.5-flash")
        app_instance.state.llm_client = fake_client
        if hasattr(app_instance.state, "chat_cache"):
            app_instance.state.chat_cache.clear()
        if hasattr(app_instance.state, "chat_ip_limiter"):
            app_instance.state.chat_ip_limiter.reset()
        yield c


def test_chat_status_endpoint(client: TestClient, app_instance: Any) -> None:
    """Verify /v1/chat/status reports readiness and active model."""
    # When enabled and fake client present
    resp = client.get("/v1/chat/status")
    assert resp.status_code == 200
    status_data = ChatStatusResponse.model_validate(resp.json())
    assert status_data.enabled is True
    assert status_data.ready is True
    assert status_data.model == "gemini-2.5-flash"

    # When disabled
    app_instance.state.chat_settings = ChatSettings(enabled=False)
    resp_disabled = client.get("/v1/chat/status")
    assert resp_disabled.status_code == 200
    disabled_status = ChatStatusResponse.model_validate(resp_disabled.json())
    assert disabled_status.enabled is False
    assert disabled_status.ready is False
    assert disabled_status.model is None


def test_chat_success_across_all_types(client: TestClient, app_instance: Any) -> None:
    """Contract test: POST /v1/chat succeeds across all public content types."""
    public_types = registry.public_types()
    assert len(public_types) >= 3

    for ctype in public_types:
        lookups = app_instance.state.lookups[ctype]
        demo_user = next(iter(lookups.user_ids)) if lookups.user_ids else None

        payload = {
            "type": ctype,
            "user_id": demo_user,
            "messages": [
                {"role": "user", "content": "Can you recommend something popular and exciting?"}
            ],
        }

        resp = client.post("/v1/chat", json=payload)
        assert resp.status_code == 200, f"Failed for type {ctype}: {resp.text}"

        chat_resp = ChatResponse.model_validate(resp.json())
        assert chat_resp.mode == "llm"
        assert len(chat_resp.reply) > 0
        assert len(chat_resp.reply) <= 800
        assert chat_resp.meta.model == "gemini-2.5-flash"
        assert chat_resp.meta.fallback_reason is None
        assert chat_resp.meta.cache_hit is False

        # Invariant: all picks must be from the engine's catalogue
        assert len(chat_resp.picks) >= 1
        for pick in chat_resp.picks:
            assert pick.item_id in lookups.catalogue_ids
            assert pick.title == lookups.item_metadata[pick.item_id]["title"]
            assert pick.rank >= 1
            assert len(pick.reason) <= 200


def test_chat_anonymous_user(client: TestClient, app_instance: Any) -> None:
    """Anonymous user (user_id=None) receives recommendations grounded in popular candidates."""
    ctype = registry.public_types()[0]
    lookups = app_instance.state.lookups[ctype]

    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "What should I start with?"}],
    }

    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    chat_resp = ChatResponse.model_validate(resp.json())
    assert chat_resp.mode == "llm"
    assert len(chat_resp.picks) > 0
    for pick in chat_resp.picks:
        assert pick.item_id in lookups.catalogue_ids


def test_chat_cache_hit_on_identical_request(client: TestClient) -> None:
    """Identical successive requests return cache_hit=True."""
    ctype = registry.public_types()[0]
    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "Unique cache testing query"}],
    }

    # Request 1: Cache miss
    resp1 = client.post("/v1/chat", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["meta"]["cache_hit"] is False

    # Request 2: Cache hit
    resp2 = client.post("/v1/chat", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["meta"]["cache_hit"] is True
    assert resp2.json()["reply"] == resp1.json()["reply"]


def test_chat_error_unknown_type(client: TestClient) -> None:
    """Unknown content type returns 404 with code='unknown_type'."""
    payload = {
        "type": "nonexistent_domain",
        "user_id": None,
        "messages": [{"role": "user", "content": "hello"}],
    }
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "unknown_type"


def test_chat_error_unknown_user(client: TestClient) -> None:
    """Unknown user ID returns 404 with code='unknown_user'."""
    ctype = registry.public_types()[0]
    payload = {
        "type": ctype,
        "user_id": "nonexistent_user_999999",
        "messages": [{"role": "user", "content": "hello"}],
    }
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "unknown_user"


def test_chat_disabled_returns_503(client: TestClient, app_instance: Any) -> None:
    """When CHAT_ENABLED=false, POST /v1/chat returns 503 chat_unavailable."""
    app_instance.state.chat_settings = ChatSettings(enabled=False)
    ctype = registry.public_types()[0]
    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "hello"}],
    }
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "chat_unavailable"


def test_chat_validation_errors(client: TestClient) -> None:
    """Malformed request bodies return 422 validation_error."""
    ctype = registry.public_types()[0]

    # Empty messages list
    r1 = client.post("/v1/chat", json={"type": ctype, "messages": []})
    assert r1.status_code == 422

    # Last message is assistant
    r2 = client.post(
        "/v1/chat",
        json={
            "type": ctype,
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        },
    )
    assert r2.status_code == 422

    # Invalid role
    r3 = client.post(
        "/v1/chat",
        json={"type": ctype, "messages": [{"role": "system", "content": "hi"}]},
    )
    assert r3.status_code == 422

    # Oversized single message (> 500 chars)
    r4 = client.post(
        "/v1/chat",
        json={"type": ctype, "messages": [{"role": "user", "content": "a" * 501}]},
    )
    assert r4.status_code == 422


def test_chat_ip_rate_limiting(client: TestClient, app_instance: Any) -> None:
    """Per-IP sliding window rate limit returns 429 with Retry-After header."""
    app_instance.state.chat_settings = ChatSettings(
        enabled=True,
        api_keys=["test-key"],
        model="gemini-2.5-flash",
        ip_rpm=3,  # tight limit for test
    )
    app_instance.state.chat_ip_limiter.reset()

    ctype = registry.public_types()[0]
    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "rate limit test"}],
    }

    # 3 allowed requests
    for _ in range(3):
        r = client.post("/v1/chat", json=payload, headers={"X-Forwarded-For": "198.51.100.1"})
        assert r.status_code == 200

    # 4th request must be rate limited
    r_blocked = client.post("/v1/chat", json=payload, headers={"X-Forwarded-For": "198.51.100.1"})
    assert r_blocked.status_code == 429
    assert r_blocked.json()["error"]["code"] == "chat_rate_limited"
    assert "Retry-After" in r_blocked.headers
    assert int(r_blocked.headers["Retry-After"]) >= 1


@pytest.mark.parametrize(
    ("error_class", "expected_fallback_reason"),
    [
        (LLMRateLimited(retry_after=20), "rate_limited"),
        (LLMTimeout(), "timeout"),
        (LLMBadOutput("malformed"), "bad_output"),
        (LLMAuthError("unauthorized"), "no_credentials"),
    ],
)
def test_chat_upstream_failures_degrade_to_engine_fallback(
    client: TestClient,
    app_instance: Any,
    error_class: Exception,
    expected_fallback_reason: str,
) -> None:
    """Upstream LLM failures yield HTTP 200 with mode='fallback' and valid engine picks."""
    fake_client = FakeLLMClient(scripted_results=[error_class])
    app_instance.state.llm_client = fake_client

    ctype = registry.public_types()[0]
    lookups = app_instance.state.lookups[ctype]

    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "Something during outage"}],
    }

    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["mode"] == "fallback"
    assert data["meta"]["fallback_reason"] == expected_fallback_reason
    assert len(data["picks"]) > 0

    # Fallback picks are grounded catalogue items
    for p in data["picks"]:
        assert p["item_id"] in lookups.catalogue_ids
        assert p["rank"] >= 1
        assert "Rank #" in p["reason"]


def test_chat_hallucinated_candidate_degrades_to_fallback(
    client: TestClient,
    app_instance: Any,
) -> None:
    """If LLM client returns a non-existent item_id, output validator fails and engine fallback is served."""
    bad_output_json = json.dumps(
        {
            "reply": "I invented a new movie!",
            "picks": [{"item_id": "totally_hallucinated_item_9999", "reason": "Not in catalogue"}],
        }
    )
    fake_client = FakeLLMClient(
        scripted_results=[
            LLMResult(
                reply="I invented a new movie!",
                picks=[],
                model="gemini-2.5-flash",
                latency_ms=10,
                raw_text=bad_output_json,
            )
        ]
    )
    app_instance.state.llm_client = fake_client

    ctype = registry.public_types()[0]
    payload = {
        "type": ctype,
        "user_id": None,
        "messages": [{"role": "user", "content": "Recommend anything"}],
    }

    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "fallback"
    assert data["meta"]["fallback_reason"] == "bad_output"
