"""Discovery Engine - Google Gemini API Client (P13.6)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from engine.llm.errors import (
    LLMAuthError,
    LLMBadOutput,
    LLMRateLimited,
    LLMTimeout,
    LLMUpstreamError,
)
from engine.llm.types import (
    LLMPick,
    LLMRequest,
    LLMResult,
)

logger = logging.getLogger("engine.llm.gemini")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _mask_key(key: str) -> str:
    """Return a safe fingerprint mask of an API key for logs and representation."""
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def _extract_retry_after(resp: httpx.Response) -> float | None:
    """Extract retry delay in seconds from HTTP headers or Gemini error payload."""
    # 1. Standard HTTP header
    header_val = resp.headers.get("retry-after")
    if header_val:
        try:
            return float(header_val)
        except ValueError:
            pass

    # 2. Inspect Google API JSON error details (RetryInfo delay e.g. '12s' or '12.5s')
    try:
        data = resp.json()
        error_obj = data.get("error", {})
        details = error_obj.get("details", [])
        for item in details:
            if isinstance(item, dict) and "retryDelay" in item:
                delay_str = str(item["retryDelay"])
                match = re.match(r"^([0-9]+(?:\.[0-9]+)?)s?$", delay_str)
                if match:
                    return float(match.group(1))
    except Exception:
        pass

    return None


class GeminiClient:
    """Async client communicating with the Google Gemini Developer API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        timeout_s: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self._external_client = client

    def __repr__(self) -> str:
        return (
            f"GeminiClient(model={self.model!r}, "
            f"api_key={_mask_key(self._api_key)!r}, "
            f"timeout_s={self.timeout_s})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    async def complete_with_fallback(
        self,
        request: LLMRequest,
        fallback_models: tuple[str, ...] = ("gemini-3.6-flash",),
    ) -> LLMResult:
        """Try this client's model first, then each backup model once.

        Only server errors (5xx such as 503) and timeouts move on to the
        next model. Auth errors (401/403) and rate limits (429) are raised
        straight away, because a different model would not fix them.
        """
        last_error: Exception | None = None

        for model in (self.model, *fallback_models):
            # Build a temporary client for this model. This is safer than
            # changing self.model, which could affect overlapping requests.
            client = GeminiClient(
                self._api_key,
                model=model,
                timeout_s=self.timeout_s,
                client=self._external_client,
            )
            try:
                return await client.complete(request)
            except (LLMUpstreamError, LLMTimeout) as exc:
                logger.warning("Model %s failed (%s), trying next", model, exc)
                last_error = exc

        # Every model failed: let the caller handle it (e.g. the fallback reply).
        assert last_error is not None  # the loop always runs at least once
        raise last_error

    async def complete(self, request: LLMRequest) -> LLMResult:
        """Send a generateContent request to Gemini and return structured picks."""
        url = f"{GEMINI_BASE_URL}/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        # Structured output schema: validate candidate IDs in validator.py
        # Avoid huge enums in responseSchema which cause Gemini server-side grammar compilation timeouts
        item_id_schema: dict[str, Any] = {"type": "STRING"}

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "reply": {
                    "type": "STRING",
                    "description": "Conversational reply in plain text.",
                },
                "picks": {
                    "type": "ARRAY",
                    "description": "Selected items chosen strictly from candidate pool.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "item_id": item_id_schema,
                            "reason": {
                                "type": "STRING",
                                "description": "Brief explanation for recommendation.",
                            },
                        },
                        "required": ["item_id", "reason"],
                    },
                },
            },
            "required": ["reply", "picks"],
        }

        contents = []
        for msg in request.contents:
            role = "model" if msg.get("role") in ("model", "assistant") else "user"
            parts = msg.get("parts") or [{"text": str(msg.get("content", ""))}]
            contents.append({"role": role, "parts": parts})

        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
        # Disable thinking tokens for flash/preview models to prevent token budget exhaustion
        if "preview" in self.model or "gemini-3.6" in self.model or "gemini-2.5" in self.model:
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}

        body = {
            "systemInstruction": {"parts": [{"text": request.system_instruction}]},
            "contents": contents,
            "generationConfig": generation_config,
        }

        start_time = time.perf_counter()
        async_client = self._external_client or httpx.AsyncClient(timeout=self.timeout_s)
        try:
            resp = await async_client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            logger.warning(
                "Gemini request timed out (model=%s, timeout=%.1fs)",
                self.model,
                self.timeout_s,
            )
            raise LLMTimeout(f"Gemini request timed out after {self.timeout_s}s.") from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini transport failure (model=%s): %s", self.model, type(exc).__name__)
            raise LLMUpstreamError(f"Gemini transport error: {exc}") from exc
        finally:
            if self._external_client is None:
                await async_client.aclose()

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Status code error mapping
        if resp.status_code == 429:
            retry_after = _extract_retry_after(resp)
            logger.warning(
                "Gemini rate limit 429 received (model=%s, retry_after=%s)",
                self.model,
                retry_after,
            )
            raise LLMRateLimited(
                message=f"Gemini rate limited (HTTP 429). Retry after {retry_after}s.",
                retry_after=retry_after,
            )

        if resp.status_code in (401, 403):
            logger.error(
                "Gemini auth error HTTP %d (model=%s, key_fingerprint=%s)",
                resp.status_code,
                self.model,
                _mask_key(self._api_key),
            )
            raise LLMAuthError(f"Gemini authentication failed with HTTP {resp.status_code}.")

        if resp.status_code >= 500:
            logger.error(
                "Gemini server error HTTP %d (model=%s)",
                resp.status_code,
                self.model,
            )
            raise LLMUpstreamError(f"Gemini service returned HTTP {resp.status_code}.")

        if resp.status_code != 200:
            logger.error(
                "Gemini unexpected status HTTP %d (model=%s)",
                resp.status_code,
                self.model,
            )
            raise LLMUpstreamError(f"Gemini returned unexpected status HTTP {resp.status_code}.")

        # Parse JSON output from Gemini response envelope
        raw_text: str | None = None
        try:
            resp_data = resp.json()
            candidates = resp_data.get("candidates", [])
            if not candidates:
                raise ValueError("Response contains zero candidates")

            first_candidate = candidates[0]
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("Candidate contains zero parts")

            raw_text = parts[0].get("text", "")
            parsed_json = json.loads(raw_text)
            reply = str(parsed_json.get("reply", ""))
            raw_picks = parsed_json.get("picks", [])

            picks: list[LLMPick] = []
            for p in raw_picks:
                if isinstance(p, dict) and "item_id" in p and "reason" in p:
                    picks.append(
                        LLMPick(
                            item_id=str(p["item_id"]),
                            reason=str(p["reason"]),
                        )
                    )

            return LLMResult(
                reply=reply,
                picks=picks,
                model=self.model,
                latency_ms=latency_ms,
                raw_text=raw_text,
                meta={"finish_reason": first_candidate.get("finishReason")},
            )
        except Exception as exc:
            logger.warning("Failed to parse Gemini response as structured JSON: %s", exc)
            raise LLMBadOutput(f"Malformed Gemini JSON output: {exc}") from exc
