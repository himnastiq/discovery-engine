"""Discovery Engine - LLM Chat Settings Loader and Validation (P13.8)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger("engine.llm.settings")


def _mask_key(key: str) -> str:
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


@dataclass(frozen=True)
class ChatSettings:
    """Immutable chat configuration settings."""

    enabled: bool = False
    api_keys: list[str] = field(default_factory=list)
    key_projects: list[str] | None = None
    model: str = "gemini-2.5-flash"
    rpm_per_project: float = 10.0
    timeout_s: float = 8.0
    max_output_tokens: int = 512
    ip_rpm: int = 6
    cache_ttl_s: int = 600

    def __repr__(self) -> str:
        proj_count = len(self.key_projects) if self.key_projects is not None else 1
        return (
            f"ChatSettings(enabled={self.enabled}, model={self.model!r}, "
            f"keys_count={len(self.api_keys)}, projects_count={proj_count}, "
            f"rpm_per_project={self.rpm_per_project}, timeout_s={self.timeout_s})"
        )

    def __str__(self) -> str:
        return self.__repr__()


def _parse_bool(val: str | None, var_name: str) -> bool:
    if val is None or not val.strip():
        return False
    clean = val.strip().lower()
    if clean in ("true", "1", "yes", "on"):
        return True
    if clean in ("false", "0", "no", "off"):
        return False
    raise ConfigError(f"Invalid boolean value for environment variable {var_name}: {val!r}")


def _parse_float(val: str | None, default: float, var_name: str, min_val: float = 0.0) -> float:
    if val is None or not val.strip():
        return default
    try:
        parsed = float(val.strip())
        if parsed <= min_val:
            raise ValueError()
        return parsed
    except ValueError as exc:
        raise ConfigError(
            f"Invalid numeric value for {var_name}: {val!r} (must be > {min_val})"
        ) from exc


def _parse_int(val: str | None, default: int, var_name: str, min_val: int = 0) -> int:
    if val is None or not val.strip():
        return default
    try:
        parsed = int(val.strip())
        if parsed < min_val:
            raise ValueError()
        return parsed
    except ValueError as exc:
        raise ConfigError(
            f"Invalid integer value for {var_name}: {val!r} (must be >= {min_val})"
        ) from exc


def load_chat_settings(env: Mapping[str, str] | None = None) -> ChatSettings:
    """Load and strictly validate chat settings from environment mapping."""
    e = env if env is not None else os.environ

    enabled = _parse_bool(e.get("CHAT_ENABLED"), "CHAT_ENABLED")

    raw_keys = e.get("GEMINI_API_KEYS", "")
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    raw_projects = e.get("GEMINI_KEY_PROJECTS")
    key_projects: list[str] | None = None
    if raw_projects is not None:
        key_projects = [p.strip() for p in raw_projects.split(",")]
        if len(key_projects) != len(api_keys):
            raise ConfigError(
                f"Configuration mismatch: GEMINI_KEY_PROJECTS has {len(key_projects)} items, "
                f"but GEMINI_API_KEYS has {len(api_keys)} keys."
            )

    model = e.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not model and enabled:
        raise ConfigError("GEMINI_MODEL must not be empty when CHAT_ENABLED=true.")

    rpm_per_project = _parse_float(
        e.get("GEMINI_RPM_PER_PROJECT"), default=10.0, var_name="GEMINI_RPM_PER_PROJECT", min_val=0.0
    )
    timeout_s = _parse_float(
        e.get("CHAT_TIMEOUT_S"), default=8.0, var_name="CHAT_TIMEOUT_S", min_val=0.0
    )
    max_output_tokens = _parse_int(
        e.get("CHAT_MAX_OUTPUT_TOKENS"), default=512, var_name="CHAT_MAX_OUTPUT_TOKENS", min_val=1
    )
    ip_rpm = _parse_int(e.get("CHAT_IP_RPM"), default=6, var_name="CHAT_IP_RPM", min_val=1)
    cache_ttl_s = _parse_int(
        e.get("CHAT_CACHE_TTL_S"), default=600, var_name="CHAT_CACHE_TTL_S", min_val=0
    )

    settings = ChatSettings(
        enabled=enabled,
        api_keys=api_keys,
        key_projects=key_projects,
        model=model or "gemini-2.5-flash",
        rpm_per_project=rpm_per_project,
        timeout_s=timeout_s,
        max_output_tokens=max_output_tokens,
        ip_rpm=ip_rpm,
        cache_ttl_s=cache_ttl_s,
    )

    return settings


def log_chat_startup(settings: ChatSettings) -> None:
    """Log startup configuration safely without disclosing secrets."""
    proj_count = len(settings.key_projects) if settings.key_projects is not None else 1
    logger.info(
        "Chatbot configured: enabled=%s, model=%s, keys_count=%d, projects_count=%d, "
        "rpm_per_project=%.1f, ip_rpm=%d, timeout_s=%.1fs, cache_ttl_s=%ds",
        settings.enabled,
        settings.model,
        len(settings.api_keys),
        proj_count,
        settings.rpm_per_project,
        settings.ip_rpm,
        settings.timeout_s,
        settings.cache_ttl_s,
    )
