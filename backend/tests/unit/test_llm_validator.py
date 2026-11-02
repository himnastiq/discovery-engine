"""Discovery Engine - LLM Output Validator Tests (P13.11).

Verifies:
1. Schema parsing, validation, and sanitization of LLM outputs.
2. Grounding invariant: picks must be an exact subset of engine candidates.
3. Deduplication of picks, capped at at most 5 items.
4. Strict length limits: reply <= 800 chars, reason <= 200 chars.
5. Markup (HTML tags) and URLs are stripped from reply and reasons.
6. Candidate metadata and rank are faithfully hydrated from engine records.
7. Hypothesis property test: for arbitrary model outputs, validated picks
   are GUARANTEED to be a strict subset of candidate IDs.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.llm.errors import LLMBadOutput
from engine.llm.validator import ValidatedChatOutput, validate_chat_output


@pytest.fixture
def sample_candidates() -> list[dict[str, Any]]:
    """Sample candidate items pool."""
    return [
        {
            "item_id": "item_1",
            "title": "The Matrix",
            "subtitle": "A Sci-Fi Classic",
            "categories": ["Sci-Fi", "Action"],
            "year": 1999,
            "candidate_rank": 1,
        },
        {
            "item_id": "item_2",
            "title": "Inception",
            "subtitle": "Your mind is the scene of the crime",
            "categories": ["Sci-Fi", "Thriller"],
            "year": 2010,
            "candidate_rank": 2,
        },
        {
            "item_id": "item_3",
            "title": "Interstellar",
            "subtitle": "Mankind was born on Earth",
            "categories": ["Sci-Fi", "Adventure"],
            "year": 2014,
            "candidate_rank": 3,
        },
        {
            "item_id": "item_4",
            "title": "Memento",
            "subtitle": "Some memories are best forgotten",
            "categories": ["Mystery", "Thriller"],
            "year": 2000,
            "candidate_rank": 4,
        },
        {
            "item_id": "item_5",
            "title": "Tenet",
            "subtitle": "Time runs out",
            "categories": ["Action", "Sci-Fi"],
            "year": 2020,
            "candidate_rank": 5,
        },
        {
            "item_id": "item_6",
            "title": "The Prestige",
            "subtitle": "Are you watching closely?",
            "categories": ["Drama", "Mystery"],
            "year": 2006,
            "candidate_rank": 6,
        },
    ]


def test_validator_valid_output(sample_candidates: list[dict[str, Any]]) -> None:
    """Valid JSON with valid picks hydrates correctly."""
    raw = {
        "reply": "Here are two mind-bending sci-fi films for you.",
        "picks": [
            {"item_id": "item_1", "reason": "Groundbreaking cyber thriller."},
            {"item_id": "item_2", "reason": "Intricate dream heist narrative."},
        ],
    }

    result = validate_chat_output(raw, sample_candidates)
    assert isinstance(result, ValidatedChatOutput)
    assert result.reply == "Here are two mind-bending sci-fi films for you."
    assert len(result.picks) == 2

    p1 = result.picks[0]
    assert p1.item_id == "item_1"
    assert p1.title == "The Matrix"
    assert p1.subtitle == "A Sci-Fi Classic"
    assert p1.categories == ["Sci-Fi", "Action"]
    assert p1.year == 1999
    assert p1.reason == "Groundbreaking cyber thriller."
    assert p1.rank == 1


def test_validator_strips_html_and_urls(sample_candidates: list[dict[str, Any]]) -> None:
    """HTML tags and URLs are stripped from reply and reason."""
    raw = {
        "reply": "Watch <b>The Matrix</b> now! Visit https://example.com for info. <script>alert(1)</script>",
        "picks": [
            {
                "item_id": "item_1",
                "reason": "Top pick <a href='http://evil.com'>click here</a> check www.movie.org!",
            }
        ],
    }

    result = validate_chat_output(raw, sample_candidates)
    assert "<" not in result.reply
    assert ">" not in result.reply
    assert "https://" not in result.reply
    assert "script" not in result.reply
    assert "The Matrix now! Visit for info. alert(1)" in result.reply

    p1 = result.picks[0]
    assert "<" not in p1.reason
    assert "http://" not in p1.reason
    assert "www.movie.org" not in p1.reason
    assert p1.reason == "Top pick click here check!"


def test_validator_rejects_hallucinated_candidate_id(
    sample_candidates: list[dict[str, Any]],
) -> None:
    """If the LLM invents an item_id not in candidates, LLMBadOutput is strictly raised."""
    raw = {
        "reply": "I recommend this movie.",
        "picks": [{"item_id": "hallucinated_id_999", "reason": "Made up movie."}],
    }

    with pytest.raises(LLMBadOutput) as exc_info:
        validate_chat_output(raw, sample_candidates)
    assert "does not exist in candidate pool" in str(exc_info.value)


def test_validator_deduplicates_picks(sample_candidates: list[dict[str, Any]]) -> None:
    """Duplicate candidate IDs in picks are deduplicated preserving the first."""
    raw = {
        "reply": "Recommendations with duplicates.",
        "picks": [
            {"item_id": "item_2", "reason": "First reason."},
            {"item_id": "item_2", "reason": "Second reason duplicate."},
            {"item_id": "item_3", "reason": "Another pick."},
        ],
    }

    result = validate_chat_output(raw, sample_candidates)
    assert len(result.picks) == 2
    assert result.picks[0].item_id == "item_2"
    assert result.picks[0].reason == "First reason."
    assert result.picks[1].item_id == "item_3"


def test_validator_caps_at_five_picks(sample_candidates: list[dict[str, Any]]) -> None:
    """Output with more than 5 picks is capped at 5."""
    raw = {
        "reply": "Many picks.",
        "picks": [{"item_id": f"item_{i}", "reason": f"Reason {i}"} for i in range(1, 7)],
    }

    result = validate_chat_output(raw, sample_candidates)
    assert len(result.picks) == 5
    assert [p.item_id for p in result.picks] == [f"item_{i}" for i in range(1, 6)]


def test_validator_rejects_oversized_reply(sample_candidates: list[dict[str, Any]]) -> None:
    """Replies longer than 800 characters are rejected."""
    raw = {
        "reply": "x" * 801,
        "picks": [],
    }

    with pytest.raises(LLMBadOutput) as exc_info:
        validate_chat_output(raw, sample_candidates)
    assert "exceeds maximum of 800 characters" in str(exc_info.value)


def test_validator_rejects_oversized_reason(sample_candidates: list[dict[str, Any]]) -> None:
    """Reasons longer than 200 characters are rejected."""
    raw = {
        "reply": "Here is a movie.",
        "picks": [{"item_id": "item_1", "reason": "r" * 201}],
    }

    with pytest.raises(LLMBadOutput) as exc_info:
        validate_chat_output(raw, sample_candidates)
    assert "exceeds maximum of 200 characters" in str(exc_info.value)


def test_validator_rejects_malformed_json_or_schema(
    sample_candidates: list[dict[str, Any]],
) -> None:
    """Non-JSON string, missing keys, or invalid types raise LLMBadOutput."""
    with pytest.raises(LLMBadOutput):
        validate_chat_output("{not valid json", sample_candidates)

    with pytest.raises(LLMBadOutput):
        validate_chat_output([], sample_candidates)  # type: ignore[arg-type]

    with pytest.raises(LLMBadOutput):
        validate_chat_output({"reply": "hello"}, sample_candidates)  # missing picks

    with pytest.raises(LLMBadOutput):
        validate_chat_output({"picks": []}, sample_candidates)  # missing reply

    with pytest.raises(LLMBadOutput):
        validate_chat_output({"reply": "hi", "picks": [{"no_item_id": 1}]}, sample_candidates)


# Hypothesis Property Test
# Generating arbitrary JSON-like structures and verifying that validated picks
# are ALWAYS an exact subset of the candidate IDs.
json_primitives = st.none() | st.booleans() | st.integers() | st.floats() | st.text()
json_values = st.recursive(
    json_primitives,
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=15,
)


@given(raw_output=json_values | st.text())
@settings(max_examples=100)
def test_hypothesis_arbitrary_output_grounding_invariant(raw_output: Any) -> None:
    """Property Invariant: For ANY arbitrary model output, validated picks are ALWAYS a subset of candidates."""
    candidates = [
        {"item_id": f"cand_{i}", "title": f"Title {i}", "candidate_rank": i} for i in range(1, 10)
    ]
    candidate_ids = {c["item_id"] for c in candidates}

    # Format as JSON string if not already string
    input_payload: str | Any = (
        raw_output
        if isinstance(raw_output, str)
        else (json.dumps(raw_output) if raw_output is not None else "")
    )

    try:
        result = validate_chat_output(input_payload, candidates)
    except LLMBadOutput:
        # Expected failure on invalid, malformed, or hallucinated outputs
        return

    # Invariant 1: Result is ValidatedChatOutput
    assert isinstance(result, ValidatedChatOutput)

    # Invariant 2: Every single pick item_id MUST be in candidate_ids
    assert all(p.item_id in candidate_ids for p in result.picks), (
        f"Pick outside candidates found in: {[p.item_id for p in result.picks]}"
    )

    # Invariant 3: Picks length is bounded by max_picks (5)
    assert len(result.picks) <= 5

    # Invariant 4: Reply length is bounded by 800
    assert len(result.reply) <= 800

    # Invariant 5: Each pick reason length is bounded by 200
    assert all(len(p.reason) <= 200 for p in result.picks)
