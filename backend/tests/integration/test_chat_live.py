"""Live LLM smoke test suite (Phase 13, P13.26).

Marked `llm_live`: skipped in standard CI and without GEMINI_API_KEYS.
Executes live prompts against the registered Gemini model and validates candidate
grounding invariants on real responses.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from api.main import app
from engine.llm.settings import load_chat_settings


@pytest.mark.llm_live
def test_live_chat_smoke_grounding() -> None:
    settings = load_chat_settings()
    if not settings.enabled or not settings.api_keys:
        pytest.skip("Live LLM test skipped: CHAT_ENABLED=false or GEMINI_API_KEYS not set.")

    client = TestClient(app)

    # 1. Verify status endpoint reports ready
    status_resp = client.get("/v1/chat/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["enabled"] is True
    assert status_data["ready"] is True

    # 2. Test live prompts across registered content types
    test_queries = [
        ("movies", "Suggest top 90s science fiction movies"),
        ("products", "Recommend popular retro gaming titles"),
        ("articles", "Summarize latest machine learning breakthroughs"),
    ]

    artifacts = getattr(app.state, "artifacts", {})

    for ctype, query in test_queries:
        resp = client.post(
            "/v1/chat",
            json={
                "type": ctype,
                "user_id": None,
                "messages": [{"role": "user", "content": query}],
            },
        )
        assert resp.status_code == 200, f"Live query failed for {ctype}: {resp.text}"
        data = resp.json()

        assert "reply" in data
        assert len(data["reply"]) > 0
        assert data["mode"] in ("llm", "fallback")
        assert "picks" in data

        # Grounding check: verify all picks belong to engine catalogue
        if ctype in artifacts:
            valid_ids = set(artifacts[ctype].items.index.astype(str))
            for pick in data["picks"]:
                assert str(pick["item_id"]) in valid_ids, (
                    f"Pick ID {pick['item_id']} not found in {ctype} catalogue!"
                )
                assert pick["rank"] >= 1
                assert len(pick["reason"]) > 0
