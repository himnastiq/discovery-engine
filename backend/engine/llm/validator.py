"""Discovery Engine - LLM Output Validator (P13.11).

Validates and sanitizes structured LLM outputs:
1. Strict JSON parsing and schema structure check ({reply: str, picks: list}).
2. Grounding invariant: all pick item IDs MUST be an exact subset of engine candidate IDs.
3. Deduplication of picks, capped at 5 picks maximum.
4. Reason length capped at 200 characters; reply capped at 800 characters.
5. Markup (HTML tags) and URLs stripped from reply and reasons.
6. Pick card metadata hydrated exclusively from engine candidate records.
Violations strictly raise LLMBadOutput to trigger immediate fallback.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from engine.llm.errors import LLMBadOutput

_HTML_TAG_REGEX = re.compile(r"<[^>]+>")
_URL_REGEX = re.compile(r"https?://[^\s!?,;]+|www\.[^\s!?,;]+", re.IGNORECASE)
_WHITESPACE_REGEX = re.compile(r"\s+")


def strip_markup_and_urls(text: str) -> str:
    """Strip HTML tags and URLs, normalizing internal whitespace."""
    if not text:
        return ""
    # Strip HTML tags
    no_html = _HTML_TAG_REGEX.sub(" ", text)
    # Strip URLs
    no_url = _URL_REGEX.sub("", no_html)
    # Normalize whitespace before punctuation
    no_space_punct = re.sub(r"\s+([!?,;.:])", r"\1", no_url)
    # Normalize whitespace
    return _WHITESPACE_REGEX.sub(" ", no_space_punct).strip()


@dataclass(frozen=True)
class ValidatedPick:
    """A validated recommendation pick hydrated from the engine candidate pool."""

    item_id: str
    title: str
    subtitle: str | None
    categories: list[str]
    year: int | None
    reason: str
    rank: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation matching API response."""
        return {
            "item_id": self.item_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "categories": list(self.categories),
            "year": self.year,
            "reason": self.reason,
            "rank": self.rank,
        }


@dataclass(frozen=True)
class ValidatedChatOutput:
    """Validated chat response with sanitized reply and hydrated candidate picks."""

    reply: str
    picks: list[ValidatedPick] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "reply": self.reply,
            "picks": [p.to_dict() for p in self.picks],
        }


def validate_chat_output(
    raw_output: str | dict[str, Any],
    candidates: list[dict[str, Any]],
    max_picks: int = 5,
    max_reply_length: int = 800,
    max_reason_length: int = 200,
) -> ValidatedChatOutput:
    """Validate and sanitize model output against engine candidates.

    Args:
        raw_output: Raw JSON string or dictionary produced by the LLM client.
        candidates: Candidate items pool assembled from the engine.
        max_picks: Maximum number of picks to allow (default 5).
        max_reply_length: Maximum allowed characters in reply (default 800).
        max_reason_length: Maximum allowed characters in reason (default 200).

    Returns:
        ValidatedChatOutput: Sanitized reply and grounded picks.

    Raises:
        LLMBadOutput: If output is malformed, contains non-candidate IDs, or violates constraints.
    """
    # 1. Parse JSON if string
    if isinstance(raw_output, str):
        try:
            data = json.loads(raw_output)
        except Exception as e:
            raise LLMBadOutput(f"Failed to parse LLM JSON output: {e}") from e
    elif isinstance(raw_output, dict):
        data = raw_output
    else:
        raise LLMBadOutput(f"Expected JSON string or dict, got {type(raw_output).__name__}")

    # 2. Check top-level schema
    if not isinstance(data, dict):
        raise LLMBadOutput("LLM output must be a JSON object (dict)")
    if "reply" not in data or not isinstance(data["reply"], str):
        raise LLMBadOutput("Missing or non-string 'reply' in LLM output")
    if "picks" not in data or not isinstance(data["picks"], list):
        raise LLMBadOutput("Missing or non-list 'picks' in LLM output")

    # 3. Sanitize and validate reply
    cleaned_reply = strip_markup_and_urls(data["reply"])
    if not cleaned_reply:
        raise LLMBadOutput("LLM 'reply' is empty after sanitization")
    if len(cleaned_reply) > max_reply_length:
        raise LLMBadOutput(
            f"LLM 'reply' length ({len(cleaned_reply)}) exceeds maximum of {max_reply_length} characters"
        )

    # 4. Map candidates for O(1) membership check and metadata hydration
    candidate_map: dict[str, dict[str, Any]] = {}
    for idx, c in enumerate(candidates, start=1):
        iid = str(c.get("item_id", "")).strip()
        if iid:
            candidate_map[iid] = {
                **c,
                "rank": int(c.get("candidate_rank", idx)),
            }

    # 5. Validate picks and enforce grounding invariant
    raw_picks = data["picks"]
    validated_picks: list[ValidatedPick] = []
    seen_pick_ids: set[str] = set()

    for p in raw_picks:
        if not isinstance(p, dict):
            raise LLMBadOutput("Each pick item in 'picks' must be an object")
        if "item_id" not in p or not isinstance(p["item_id"], str):
            raise LLMBadOutput("Pick missing string 'item_id'")

        item_id = p["item_id"].strip()
        if not item_id:
            raise LLMBadOutput("Empty item_id in pick")

        # Grounding invariant: every single pick item_id MUST be in candidate pool
        if item_id not in candidate_map:
            raise LLMBadOutput(f"Pick item_id '{item_id}' does not exist in candidate pool")

        # Deduplicate picks
        if item_id in seen_pick_ids:
            continue
        seen_pick_ids.add(item_id)

        # Validate and sanitize reason
        raw_reason = p.get("reason", "")
        if not isinstance(raw_reason, str):
            raise LLMBadOutput(f"Pick '{item_id}' has non-string reason")

        cleaned_reason = strip_markup_and_urls(raw_reason)
        if not cleaned_reason:
            cleaned_reason = "Recommended based on your taste profile."
        elif len(cleaned_reason) > max_reason_length:
            raise LLMBadOutput(
                f"Pick '{item_id}' reason length ({len(cleaned_reason)}) exceeds maximum of {max_reason_length} characters"
            )

        cand = candidate_map[item_id]
        validated_picks.append(
            ValidatedPick(
                item_id=item_id,
                title=str(cand.get("title", item_id)),
                subtitle=cand.get("subtitle"),
                categories=list(cand.get("categories", [])),
                year=cand.get("year"),
                reason=cleaned_reason,
                rank=int(cand.get("rank", len(validated_picks) + 1)),
            )
        )

        if len(validated_picks) >= max_picks:
            break

    return ValidatedChatOutput(reply=cleaned_reply, picks=validated_picks)
