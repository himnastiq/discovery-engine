"""Discovery Engine - LLM Candidate Assembly Unit Tests (P13.10).

Verifies:
1. Known warm user receives personalized candidates.
2. Unknown or cold user falls back to popular candidates.
3. Search hits for the last user message are added to the candidate pool.
4. Empty message hits or empty queries gracefully degrade without error.
5. Deduplication across pools preserves stable ranking order.
6. Candidate pool is strictly capped at max_candidates (40).
7. Exclusions (e.g. seen items when allow_repeat is False) are strictly honored.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from api.lookups import TypeLookups
from api.search import ItemSearchIndex
from engine.config import load_config
from engine.llm.candidates import assemble_candidates
from engine.schema import ScoredItem


@pytest.fixture
def dummy_lookups() -> TypeLookups:
    """Construct an in-memory TypeLookups with 60 items and 2 users."""
    spec = load_config("toy")
    # Set allow_repeat to False for exclusion testing
    spec.model.allow_repeat = False

    catalogue_ids = {f"item_{i}" for i in range(1, 61)}
    item_metadata = {
        f"item_{i}": {
            "title": f"Item Title {i}",
            "subtitle": f"Subtitle {i}",
            "categories": ["Sci-Fi", "Action"] if i % 2 == 0 else ["Drama"],
            "year": 2000 + (i % 20),
            "image_url": f"https://example.com/{i}.jpg",
        }
        for i in range(1, 61)
    }

    user_ids = {"user_warm", "user_cold"}
    user_positive_count = {"user_warm": 10, "user_cold": 0}
    user_seen_items = {"user_warm": {"item_1", "item_2"}, "user_cold": set()}

    # Precomputed topn for user_warm: item_1 (seen), item_3, item_4, ..., item_25
    user_topn = {
        "user_warm": [(f"item_{i}", float(100 - i)) for i in range(1, 26)],
        "user_cold": [],
    }

    lookups = TypeLookups(
        content_type="toy",
        spec=spec,
        catalogue_ids=catalogue_ids,
        user_ids=user_ids,
        item_metadata=item_metadata,
        user_seen_items=user_seen_items,
        user_positive_count=user_positive_count,
        user_topn=user_topn,
    )
    return lookups


@pytest.fixture
def mock_model() -> MagicMock:
    """Mock RecommenderModel returning popular and recommend_user items."""
    model = MagicMock()

    def mock_popular(k: int = 10, exclude_ids: Any = ()) -> list[ScoredItem]:
        results: list[ScoredItem] = []
        # Popular items from item_10 to item_50
        for i in range(10, 50):
            iid = f"item_{i}"
            if iid not in exclude_ids:
                results.append(ScoredItem(item_id=iid, score=float(100 - i), rank=len(results) + 1))
                if len(results) >= k:
                    break
        return results

    def mock_recommend_user(user_id: str, k: int = 20, exclude_ids: Any = ()) -> list[ScoredItem]:
        results: list[ScoredItem] = []
        for i in range(1, 40):
            iid = f"item_{i}"
            if iid not in exclude_ids:
                results.append(ScoredItem(item_id=iid, score=float(200 - i), rank=len(results) + 1))
                if len(results) >= k:
                    break
        return results

    model.popular.side_effect = mock_popular
    model.recommend_user.side_effect = mock_recommend_user
    return model


@pytest.fixture
def dummy_search_index() -> ItemSearchIndex:
    """ItemSearchIndex built from 60 items."""
    items_data = [
        {
            "item_id": f"item_{i}",
            "title": f"Matrix Resurrection {i}" if i == 55 else f"Item Title {i}",
            "subtitle": f"Subtitle {i}",
            "categories": ["Sci-Fi"] if i % 2 == 0 else ["Drama"],
            "year": 2020,
            "image_url": None,
        }
        for i in range(1, 61)
    ]
    items_df = pd.DataFrame(items_data)
    interactions_df = pd.DataFrame(
        [{"user_id": "u1", "item_id": f"item_{i}", "signal": 1.0} for i in range(1, 61)]
    )
    return ItemSearchIndex(items_df, interactions_df)


def test_candidates_known_warm_user(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Warm user receives personalised items, with exclusions applied and popular fill."""
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id="user_warm",
        last_user_message="Matrix",
        search_index=dummy_search_index,
        max_candidates=40,
    )

    candidate_ids = [c["item_id"] for c in candidates]
    # item_1 and item_2 are in user_seen_items and allow_repeat=False, so must be excluded
    assert "item_1" not in candidate_ids
    assert "item_2" not in candidate_ids
    # Precomputed topn item_3 should be present
    assert "item_3" in candidate_ids
    # Search hit for "Matrix" (item_55) should be present
    assert "item_55" in candidate_ids
    # Every item must have catalogue metadata
    for c in candidates:
        assert c["item_id"] in dummy_lookups.catalogue_ids
        assert c["title"] == dummy_lookups.item_metadata[c["item_id"]]["title"]
        assert c["candidate_rank"] >= 1


def test_candidates_unknown_user(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Unknown user (user_id=None or unindexed user) receives popular candidates."""
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id=None,
        last_user_message=None,
        search_index=dummy_search_index,
        max_candidates=40,
    )

    assert len(candidates) > 0
    candidate_ids = [c["item_id"] for c in candidates]
    # Pool 1 popular starts at item_10
    assert "item_10" in candidate_ids


def test_candidates_cold_user(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Cold user (positive_count < threshold) receives popular candidates."""
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id="user_cold",
        last_user_message=None,
        search_index=dummy_search_index,
        max_candidates=40,
    )

    assert len(candidates) > 0
    candidate_ids = [c["item_id"] for c in candidates]
    assert "item_10" in candidate_ids


def test_candidates_empty_message_hits(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Queries with zero search matches or empty string still return candidates from other pools."""
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id="user_warm",
        last_user_message="NonexistentTitleXYZ12345",
        search_index=dummy_search_index,
        max_candidates=40,
    )

    assert len(candidates) > 0
    # Search pool gave 0 hits, but personalised/popular pools provide candidates
    for c in candidates:
        assert c["item_id"] in dummy_lookups.catalogue_ids


def test_candidates_deduplication_and_order(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Items appearing in multiple pools are strictly deduplicated, keeping earliest rank."""
    # item_10 is in precomputed topn AND in popular
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id="user_warm",
        last_user_message="Item Title 10",
        search_index=dummy_search_index,
        max_candidates=40,
    )

    candidate_ids = [c["item_id"] for c in candidates]
    assert len(candidate_ids) == len(set(candidate_ids)), "Duplicate candidate IDs found"
    assert candidate_ids.count("item_10") == 1


def test_candidates_hard_cap(
    dummy_lookups: TypeLookups,
    mock_model: MagicMock,
    dummy_search_index: ItemSearchIndex,
) -> None:
    """Candidate assembly respects max_candidates limit."""
    candidates = assemble_candidates(
        lookups=dummy_lookups,
        model=mock_model,
        user_id="user_warm",
        last_user_message="Item",
        search_index=dummy_search_index,
        max_candidates=15,
    )

    assert len(candidates) == 15
    for rank, c in enumerate(candidates, start=1):
        assert c["candidate_rank"] == rank
