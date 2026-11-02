"""Discovery Engine - Chat settings validation and logging tests (P13.8)."""

from __future__ import annotations

import logging

import pytest

from engine.errors import ConfigError
from engine.llm import ChatSettings, load_chat_settings, log_chat_startup


def test_load_chat_settings_defaults() -> None:
    settings = load_chat_settings({})
    assert not settings.enabled
    assert settings.api_keys == []
    assert settings.key_projects is None
    assert settings.model == "gemini-2.5-flash"
    assert settings.rpm_per_project == 10.0
    assert settings.timeout_s == 8.0
    assert settings.max_output_tokens == 512
    assert settings.ip_rpm == 6
    assert settings.cache_ttl_s == 600


def test_load_chat_settings_valid_custom() -> None:
    env = {
        "CHAT_ENABLED": "true",
        "GEMINI_API_KEYS": "key_one, key_two",
        "GEMINI_KEY_PROJECTS": "proj_1, proj_2",
        "GEMINI_MODEL": "gemini-2.0-flash",
        "GEMINI_RPM_PER_PROJECT": "15.5",
        "CHAT_TIMEOUT_S": "12.0",
        "CHAT_MAX_OUTPUT_TOKENS": "256",
        "CHAT_IP_RPM": "10",
        "CHAT_CACHE_TTL_S": "300",
    }
    settings = load_chat_settings(env)
    assert settings.enabled is True
    assert settings.api_keys == ["key_one", "key_two"]
    assert settings.key_projects == ["proj_1", "proj_2"]
    assert settings.model == "gemini-2.0-flash"
    assert settings.rpm_per_project == 15.5
    assert settings.timeout_s == 12.0
    assert settings.max_output_tokens == 256
    assert settings.ip_rpm == 10
    assert settings.cache_ttl_s == 300


@pytest.mark.parametrize(
    ("invalid_env", "err_match"),
    [
        ({"CHAT_ENABLED": "maybe"}, "Invalid boolean value"),
        (
            {"GEMINI_API_KEYS": "k1,k2", "GEMINI_KEY_PROJECTS": "p1"},
            "Configuration mismatch: GEMINI_KEY_PROJECTS has 1 items, but GEMINI_API_KEYS has 2",
        ),
        (
            {"CHAT_ENABLED": "true", "GEMINI_MODEL": "   "},
            "GEMINI_MODEL must not be empty",
        ),
        ({"GEMINI_RPM_PER_PROJECT": "-5"}, "Invalid numeric value"),
        ({"CHAT_TIMEOUT_S": "zero"}, "Invalid numeric value"),
        ({"CHAT_MAX_OUTPUT_TOKENS": "0"}, "Invalid integer value"),
        ({"CHAT_IP_RPM": "-1"}, "Invalid integer value"),
        ({"CHAT_CACHE_TTL_S": "-10"}, "Invalid integer value"),
    ],
)
def test_load_chat_settings_invalid_configs_fail_loudly(
    invalid_env: dict[str, str], err_match: str
) -> None:
    with pytest.raises(ConfigError, match=err_match):
        load_chat_settings(invalid_env)


def test_log_chat_startup_zero_secrets_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    secret_key = "AIzaSySuperSecretKey12345"

    settings = ChatSettings(
        enabled=True,
        api_keys=[secret_key, "AIzaSyAnotherSecretKey67890"],
        key_projects=["project_1", "project_2"],
        model="gemini-2.5-flash",
    )

    log_chat_startup(settings)

    # Must contain counts, model, and status
    assert "Chatbot configured" in caplog.text
    assert "keys_count=2" in caplog.text
    assert "projects_count=2" in caplog.text
    assert "model=gemini-2.5-flash" in caplog.text

    # Must NEVER contain the actual key strings
    assert secret_key not in caplog.text
    assert "AIzaSyAnotherSecretKey67890" not in caplog.text

    # Representation check
    repr_str = repr(settings)
    assert secret_key not in repr_str
    assert "keys_count=2" in repr_str
