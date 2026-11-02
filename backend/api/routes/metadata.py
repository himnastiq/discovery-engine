"""Discovery Engine - Read-only metadata endpoints (Phase 7, P7.3)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Path, Query, Request

from api.deps import resolve_loaded_artifacts, resolve_model
from api.schemas import (
    AboutResponse,
    DatasetAttribution,
    HealthResponse,
    HealthTypeStatus,
    ItemDetail,
    SearchResponse,
    TypeInfo,
    TypesResponse,
    UsersResponse,
    UserSummary,
)
from api.search import ItemSearchIndex
from engine import registry
from engine.artifacts import as_str_list
from engine.config import load_config
from engine.errors import UnknownItem

router = APIRouter(prefix="/v1", tags=["metadata"])


ATTRIBUTIONS: list[DatasetAttribution] = [
    DatasetAttribution(
        name="Microsoft Recommenders",
        citation="Recommenders Team. (2024). Recommenders: Examples and Best Practices for Recommendation Systems.",
        license="MIT License",
        source_url="https://github.com/recommenders-team/recommenders",
        original_vs_derived=(
            "Vendored, trimmed, and modernized into 'discovery' package; removed heavy deep-learning "
            "frameworks (PyTorch, TensorFlow, Spark); optimized sparse SAR co-occurrence operations."
        ),
    ),
    DatasetAttribution(
        name="MovieLens 1M",
        citation="F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM TIIS.",
        license="GroupLens Non-Commercial Research License",
        source_url="https://grouplens.org/datasets/movielens/1m/",
        original_vs_derived=(
            "Cleaned display titles (stripped years and alternate-title parentheses, normalized grammatical "
            "articles), filtered low-interaction users, and evaluated under strict chronological split."
        ),
    ),
    DatasetAttribution(
        name="Amazon Product Reviews (Video Games)",
        citation="Julian McAuley, Christopher Targett, Qinfeng Shi, Anton van den Hengel. 2015. Image-Based Recommendations on Styles and Substitutes. SIGIR.",
        license="Custom Academic / Research Use License",
        source_url="https://cseweb.ucsd.edu/~jmcauley/datasets.html",
        original_vs_derived=(
            "Filtered to 5-core interactions and top 8,000 items; joined product titles, brands, and categories; "
            "evaluated with popularity-capped sparse SAR."
        ),
    ),
    DatasetAttribution(
        name="Microsoft News Dataset (MIND)",
        citation="Fangzhao Wu et al. 2020. MIND: A Large-scale Dataset for News Recommendation. ACL.",
        license="Microsoft Research License for Data",
        source_url="https://msnews.github.io/",
        original_vs_derived=(
            "MIND-small: Serves news articles with TF-IDF content profiles, "
            "impression-ranking evaluation, and freshness recency window."
        ),
    ),
]


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    """System health check: reports overall and per-type serving status."""
    available_map = request.app.state.availability
    reasons_map = request.app.state.unavailable_reasons
    artifacts_map = request.app.state.artifacts

    types_status: dict[str, HealthTypeStatus] = {}
    registered_types = registry.public_types()

    all_available = True
    any_available = False

    for ctype in registered_types:
        is_avail = available_map.get(ctype, False)
        version: str | None = None
        reason: str | None = None

        if is_avail and ctype in artifacts_map:
            any_available = True
            version = artifacts_map[ctype].manifest.get("schema_version", "1.0.0")
        else:
            all_available = False
            reason = reasons_map.get(ctype, "Unavailable")

        types_status[ctype] = HealthTypeStatus(
            available=is_avail,
            version=version,
            reason=reason,
        )

    if all_available and registered_types:
        overall_status = "ok"
    elif any_available:
        overall_status = "degraded"
    else:
        overall_status = "error"

    return HealthResponse(
        status=overall_status,
        types=types_status,
        version="1.0.0",
    )


@router.get("/types", response_model=TypesResponse)
def get_types(request: Request) -> TypesResponse:
    """List registered content types with dataset statistics and UI configuration."""
    result: list[TypeInfo] = []
    registered_types = registry.public_types()

    for ctype in registered_types:
        spec = load_config(ctype, fast=True)
        is_avail = request.app.state.availability.get(ctype, False)

        user_count = 0
        item_count = 0
        interaction_count = 0

        if is_avail and ctype in request.app.state.artifacts:
            loaded = request.app.state.artifacts[ctype]
            user_count = len(loaded.users)
            item_count = len(loaded.items)
            interaction_count = len(loaded.interactions)

        result.append(
            TypeInfo(
                id=ctype,
                display_name=spec.display_name,
                card_type=spec.card_type,
                supports_cold_start=True,
                user_count=user_count,
                item_count=item_count,
                interaction_count=interaction_count,
                starter_prompts=list(spec.chat.starter_prompts)
                if hasattr(spec, "chat") and spec.chat
                else [],
            )
        )

    return TypesResponse(types=result)


@router.get("/types/{type}/users", response_model=UsersResponse)
def get_users_for_type(
    request: Request,
    type: str = Path(..., description="Content type identifier", max_length=50),
    limit: int = Query(default=50, ge=1, le=500, description="Max users to return"),
    persona: str | None = Query(default=None, max_length=50, description="Optional persona filter"),
) -> UsersResponse:
    """Retrieve users for exploration: diverse demo users appear first, followed by sampled users."""
    loaded = resolve_loaded_artifacts(request, type)
    model = resolve_model(request, type)
    modelled_users = model.get_modelled_user_ids()

    # 1. Process demo users first
    demo_users = loaded.demo_users
    demo_ids: set[str] = set()
    result_users: list[UserSummary] = []

    persona_clean = persona.strip().lower() if persona else None

    for d in demo_users:
        uid = str(d["user_id"])
        if modelled_users and uid not in modelled_users:
            continue
        user_persona = str(d.get("persona", ""))
        if persona_clean and user_persona.lower() != persona_clean:
            continue

        demo_ids.add(uid)
        categories = as_str_list(d.get("top_categories", []))

        result_users.append(
            UserSummary(
                user_id=uid,
                persona=user_persona or None,
                interaction_count=int(d.get("interaction_count", 0)),
                is_demo=True,
                top_categories=categories,
            )
        )
        if len(result_users) >= limit:
            break

    # 2. Append sampled non-demo users if space permits
    if len(result_users) < limit and loaded.users is not None and not loaded.users.empty:
        users_df = loaded.users
        if persona_clean:
            users_df = users_df[users_df["persona"].astype(str).str.lower() == persona_clean]

        for _, row in users_df.iterrows():
            uid = str(row["user_id"])
            if uid in demo_ids:
                continue
            if modelled_users and uid not in modelled_users:
                continue

            categories = as_str_list(row.get("top_categories"))
            persona_val = str(row["persona"]) if pd.notna(row.get("persona")) else None

            result_users.append(
                UserSummary(
                    user_id=uid,
                    persona=persona_val,
                    interaction_count=int(row.get("interaction_count", 0)),
                    is_demo=False,
                    top_categories=categories,
                )
            )
            if len(result_users) >= limit:
                break

    return UsersResponse(
        content_type=type,
        total=len(result_users),
        users=result_users,
    )


@router.get("/items/search", response_model=SearchResponse)
def search_items(
    request: Request,
    type: str = Query(..., description="Content type identifier", max_length=50),
    q: str = Query(..., min_length=1, max_length=100, description="Normalized search term"),
    limit: int = Query(default=20, ge=1, le=100, description="Max search results"),
) -> SearchResponse:
    """Execute normalized text search with exact > prefix > word-start > contains ranking."""
    loaded = resolve_loaded_artifacts(request, type)

    # Fetch pre-built search index or build on demand
    search_indexes = getattr(request.app.state, "search_indexes", None)
    if search_indexes is None:
        request.app.state.search_indexes = {}
        search_indexes = request.app.state.search_indexes

    if type not in search_indexes:
        search_indexes[type] = ItemSearchIndex(loaded.items, loaded.interactions)

    index: ItemSearchIndex = search_indexes[type]
    results, total_matches = index.search(query=q, limit=limit)

    return SearchResponse(
        content_type=type,
        query=q,
        total_matches=total_matches,
        results=results,
    )


@router.get("/items/{item_id}", response_model=ItemDetail)
def get_item_detail(
    request: Request,
    item_id: str = Path(..., description="Item unique identifier", max_length=100),
    type: str = Query(..., description="Content type identifier", max_length=50),
) -> ItemDetail:
    """Retrieve complete metadata and details for a single catalogue item."""
    loaded = resolve_loaded_artifacts(request, type)

    items_df = loaded.items
    matches = items_df[items_df["item_id"].astype(str) == str(item_id)]
    if matches.empty:
        raise UnknownItem(item_id=item_id, content_type=type)

    row = matches.iloc[0]
    categories = as_str_list(row.get("categories"))

    subtitle = str(row["subtitle"]) if pd.notna(row.get("subtitle")) else None
    year = int(row["year"]) if pd.notna(row.get("year")) else None
    image_url = str(row["image_url"]) if pd.notna(row.get("image_url")) else None
    text = str(row["text"]) if pd.notna(row.get("text")) else None

    # Gather extra metadata fields (e.g. price, brand)
    meta: dict[str, Any] = {}
    for col in items_df.columns:
        if col not in ("item_id", "title", "subtitle", "categories", "year", "image_url", "text"):
            val = row[col]
            if pd.notna(val):
                meta[col] = val

    # Popularity rank if search index available (F-019)
    popularity_rank: int | None = None
    search_indexes = getattr(request.app.state, "search_indexes", {})
    if type in search_indexes:
        popularity_rank = search_indexes[type].get_popularity_rank(str(item_id))

    return ItemDetail(
        item_id=str(row["item_id"]),
        title=str(row.get("title", item_id)),
        subtitle=subtitle,
        categories=categories,
        year=year,
        image_url=image_url,
        text=text,
        popularity_rank=popularity_rank,
        meta=meta,
    )


@router.get("/about", response_model=AboutResponse)
def get_about() -> AboutResponse:
    """Attribution, dataset citations, and original vs derived transformations."""
    return AboutResponse(
        title="Discovery Engine",
        version="1.0.0",
        description=(
            "Adaptive multi-domain recommendation engine serving multiple content domains "
            "with full auditability, zero deep-learning runtime overhead, and verified ranking integrity."
        ),
        attributions=ATTRIBUTIONS,
        non_commercial_notice=(
            "This software and dataset demonstrations are provided strictly for research, evaluation, "
            "and educational purposes. All original datasets retain their upstream copyright and license terms."
        ),
    )


@router.get("/metrics")
def get_metrics(
    request: Request,
    type: str = Query(..., description="Content type identifier", max_length=50),
) -> Any:
    """Retrieve verified evaluation metrics, cold-start degradation curves, and provenance."""
    loaded = resolve_loaded_artifacts(request, type)
    # Serves metrics.json unchanged
    return loaded.metrics
