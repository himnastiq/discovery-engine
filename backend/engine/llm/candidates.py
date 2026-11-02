"""Discovery Engine - LLM Candidate Assembly from Engine Pools (P13.10).

Assembles candidates exclusively from the recommendation engine:
1. Personalised top-20 (or global popular top-20 if user is unknown or cold).
2. Global popular top-10.
3. Keyword search hits for the user's latest query (top-10).
Deduplicates IDs while preserving stable ranking order, capped at 40 items.
All candidate metadata is hydrated from catalogue lookups, never from the model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from api.lookups import TypeLookups
    from api.search import ItemSearchIndex
    from engine.models.base import RecommenderModel


def assemble_candidates(
    lookups: TypeLookups,
    model: RecommenderModel | Any | None,
    user_id: str | None = None,
    last_user_message: str | None = None,
    search_index: ItemSearchIndex | None = None,
    max_candidates: int = 40,
) -> list[dict[str, Any]]:
    """Assemble candidate pool for the LLM concierge from the engine.

    Args:
        lookups: Precomputed TypeLookups containing item metadata, user profiles, and top-n.
        model: Trained recommender model for the active content type (optional if lookups suffice).
        user_id: Target user ID, or None for anonymous user.
        last_user_message: The text of the user's latest chat inquiry.
        search_index: In-memory ItemSearchIndex for keyword retrieval against catalogue titles.
        max_candidates: Hard upper bound on candidate pool size (default 40).

    Returns:
        list[dict[str, Any]]: Deduplicated, catalogue-grounded candidate items with metadata.
    """
    candidate_ids: list[str] = []
    seen_ids: set[str] = set()

    # 1. Compute exclusions (e.g. seen items if allow_repeat is False)
    exclusions: set[str] = set()
    spec = lookups.spec
    uid_str = str(user_id) if user_id is not None else None

    if (
        uid_str is not None
        and uid_str in lookups.user_ids
        and not getattr(spec.model, "allow_repeat", True)
    ):
        exclusions.update(lookups.user_seen_items.get(uid_str, set()))

    # 2. Pool 1: Personalised top-20 (or popular top-20 if unknown or cold user)
    is_known = uid_str is not None and uid_str in lookups.user_ids
    pos_count = (
        lookups.user_positive_count.get(uid_str, 0) if is_known and uid_str is not None else 0
    )
    min_pos = getattr(spec.serving, "min_positive_items_for_personalization", 1)
    is_warm = is_known and pos_count >= min_pos

    pool1_ids: list[str] = []

    if is_warm and uid_str is not None:
        # Check precomputed user_topn first
        topn_tuples = lookups.user_topn.get(uid_str, [])
        for iid, _ in topn_tuples:
            if iid not in exclusions and iid in lookups.catalogue_ids:
                pool1_ids.append(iid)
                if len(pool1_ids) >= 20:
                    break

        # If precomputed topn was insufficient and model is available, compute live
        if len(pool1_ids) < 20 and model is not None and hasattr(model, "recommend_user"):
            try:
                recs = model.recommend_user(user_id=uid_str, k=20, exclude_ids=exclusions)
                for item in recs:
                    iid = str(getattr(item, "item_id", item))
                    if iid not in pool1_ids and iid in lookups.catalogue_ids:
                        pool1_ids.append(iid)
                        if len(pool1_ids) >= 20:
                            break
            except Exception:
                pass

    # If user is unknown or cold, or if personalised recs yielded nothing, fall back to popular
    if not pool1_ids and model is not None and hasattr(model, "popular"):
        try:
            pop_items = model.popular(k=20, exclude_ids=exclusions)
            for item in pop_items:
                iid = str(getattr(item, "item_id", item))
                if iid in lookups.catalogue_ids:
                    pool1_ids.append(iid)
                    if len(pool1_ids) >= 20:
                        break
        except Exception:
            pass

    for iid in pool1_ids:
        if iid not in seen_ids:
            seen_ids.add(iid)
            candidate_ids.append(iid)

    # 3. Pool 2: Popular top-10
    pool2_ids: list[str] = []
    if model is not None and hasattr(model, "popular"):
        try:
            pop_items = model.popular(k=30, exclude_ids=exclusions)
            for item in pop_items:
                iid = str(getattr(item, "item_id", item))
                if iid in lookups.catalogue_ids and iid not in seen_ids:
                    seen_ids.add(iid)
                    candidate_ids.append(iid)
                    pool2_ids.append(iid)
                    if len(pool2_ids) >= 10:
                        break
        except Exception:
            pass

    # 4. Pool 3: Search hits for the last user message (top-10)
    if search_index is not None and last_user_message and last_user_message.strip():
        try:
            search_results, _ = search_index.search(query=last_user_message.strip(), limit=10)
            search_added = 0
            for hit in search_results:
                iid = str(getattr(hit, "item_id", ""))
                if iid in lookups.catalogue_ids and iid not in seen_ids and iid not in exclusions:
                    seen_ids.add(iid)
                    candidate_ids.append(iid)
                    search_added += 1
                    if search_added >= 10:
                        break
        except Exception:
            pass

    # 5. Cap candidates at max_candidates
    capped_ids = candidate_ids[:max_candidates]

    # 6. Hydrate metadata from catalogue lookups
    candidates: list[dict[str, Any]] = []
    for rank, iid in enumerate(capped_ids, start=1):
        meta = lookups.item_metadata.get(iid, {})
        candidates.append(
            {
                "item_id": iid,
                "title": str(meta.get("title", iid)),
                "subtitle": meta.get("subtitle"),
                "categories": meta.get("categories", []),
                "year": meta.get("year"),
                "image_url": meta.get("image_url"),
                "candidate_rank": rank,
            }
        )

    return candidates
