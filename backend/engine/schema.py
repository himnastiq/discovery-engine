"""Discovery Engine - Core schema definitions and domain models.

All IDs are represented as non-empty strings across engine and API boundaries.
Schemas are strictly validated via Pydantic v2.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemaBase(BaseModel):
    """Base class for engine schemas with strict configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Interaction(SchemaBase):
    """Unified user-item interaction schema."""

    user_id: str = Field(..., min_length=1, description="Unique string identifier for the user")
    item_id: str = Field(..., min_length=1, description="Unique string identifier for the item")
    signal: float = Field(..., description="Interaction strength (e.g. rating, or 1.0 for click)")
    timestamp: int = Field(..., ge=0, description="Unix timestamp in seconds")
    positive: bool = Field(..., description="Whether this interaction counts as positive")

    @field_validator("user_id", "item_id", mode="before")
    @classmethod
    def coerce_id_to_string(cls, v: Any) -> str:
        if v is None:
            raise ValueError("ID cannot be None")
        s = str(v).strip()
        if not s:
            raise ValueError("ID cannot be empty")
        return s

    @field_validator("signal")
    @classmethod
    def validate_finite_signal(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Signal must be a finite number")
        return v


class Item(SchemaBase):
    """Unified item metadata schema."""

    item_id: str = Field(..., min_length=1, description="Unique string identifier for the item")
    title: str = Field(..., min_length=1, description="Display title of the item")
    subtitle: str | None = Field(default=None, description="Subtitle or brand/category line")
    categories: list[str] = Field(
        default_factory=list, description="List of category/genre strings"
    )
    text: str | None = Field(default=None, description="Longer text description or abstract")
    year: int | None = Field(
        default=None, ge=1800, le=2100, description="Release or publication year"
    )
    image_url: str | None = Field(default=None, description="URL to poster or product image")
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Dataset-specific additional metadata"
    )

    @field_validator("item_id", "title", mode="before")
    @classmethod
    def coerce_str_fields(cls, v: Any) -> str:
        if v is None:
            raise ValueError("Field cannot be None")
        s = str(v).strip()
        if not s:
            raise ValueError("Field cannot be empty")
        return s


class ScoredItem(SchemaBase):
    """A recommended or similar item with raw score and rank."""

    item_id: str = Field(..., min_length=1, description="Item identifier")
    score: float = Field(..., description="Raw model score")
    rank: int = Field(..., ge=1, description="1-based ranking position")

    @field_validator("item_id", mode="before")
    @classmethod
    def coerce_item_id(cls, v: Any) -> str:
        s = str(v).strip() if v is not None else ""
        if not s:
            raise ValueError("item_id cannot be empty")
        return s

    @field_validator("score")
    @classmethod
    def validate_finite_score(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Score must be a finite number")
        return v


class Reason(SchemaBase):
    """Faithful explanation for a recommendation."""

    kind: str = Field(
        ..., min_length=1, description="Explanation type (e.g. similar_item, genre_match)"
    )
    item_id: str | None = Field(
        default=None, description="ID of history item contributing to the score"
    )
    text: str = Field(..., min_length=1, description="Human-readable explanation message")

    @field_validator("item_id", mode="before")
    @classmethod
    def clean_item_id(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class ValidationReport(SchemaBase):
    """Report generated during dataset validation (R1)."""

    total_interactions: int = Field(..., ge=0, description="Total number of interaction records")
    unique_users: int = Field(..., ge=0, description="Count of distinct users")
    unique_items: int = Field(..., ge=0, description="Count of distinct items")
    sparsity: float = Field(..., ge=0.0, le=1.0, description="Matrix sparsity 1 - (N / (U*I))")
    min_timestamp: int | None = Field(
        default=None, ge=0, description="Earliest interaction timestamp"
    )
    max_timestamp: int | None = Field(
        default=None, ge=0, description="Latest interaction timestamp"
    )
    positive_interactions: int = Field(
        default=0, ge=0, description="Count of positive interactions"
    )
    filtered_users: int = Field(default=0, ge=0, description="Count of users removed by filtering")
    filtered_items: int = Field(default=0, ge=0, description="Count of items removed by filtering")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional validation statistics"
    )

    @field_validator("max_timestamp")
    @classmethod
    def validate_timestamp_range(cls, v: int | None, info: Any) -> int | None:
        min_ts = info.data.get("min_timestamp") if hasattr(info, "data") else None
        if v is not None and min_ts is not None and v < min_ts:
            raise ValueError("max_timestamp cannot be less than min_timestamp")
        return v


class DatasetConfig(SchemaBase):
    """Dataset adapter configuration."""

    adapter: str = Field(..., min_length=1)
    variant: str = Field(default="default", min_length=1)
    display_name: str | None = Field(
        default=None, description="Human-readable dataset display name (e.g. 'MovieLens 1M')"
    )
    min_user_interactions: int = Field(default=1, ge=1)
    min_item_interactions: int = Field(default=1, ge=1)


class SignalConfig(SchemaBase):
    """Signal definition and threshold configuration."""

    positive_threshold: float = Field(
        ..., description="Threshold at or above which an interaction is positive"
    )
    use_rating_as_weight: bool = Field(
        default=True, description="Whether to use rating values as interaction weights"
    )


class SplitConfig(SchemaBase):
    """Dataset splitting strategy configuration."""

    strategy: Literal["chronological", "leave_last_n", "impression_time"] = Field(...)
    ratio: float = Field(default=0.8, gt=0.0, lt=1.0)
    seed: int = Field(default=42)


class ModelConfig(SchemaBase):
    """Recommender model configuration."""

    name: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    allow_repeat: bool = Field(default=False, description="Whether seen items may be recommended")
    supports_cold_start: bool = Field(
        default=True, description="Whether model natively supports cold start"
    )


class EvaluationConfig(SchemaBase):
    """Evaluation protocol and baseline configuration."""

    k: list[int] = Field(default_factory=lambda: [5, 10, 20])
    cold_start_history_sizes: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 5, 10, 20])
    baselines: list[str] = Field(default_factory=lambda: ["popularity", "random"])
    recency_window: int | str | None = Field(default=None)
    max_test_users: int = Field(default=2000, ge=1, description="Maximum test users to evaluate")
    protocol: str = Field(
        default="standard", description="Evaluation protocol ('standard' or 'dual_protocol')"
    )
    post_train: list[str] = Field(
        default_factory=list, description="Post-training hook names to execute"
    )


class ServingConfig(SchemaBase):
    """Serving and memory budget configuration."""

    top_neighbors_per_item: int = Field(default=50, ge=1)
    max_items_in_similarity: int = Field(default=8000, ge=1)
    recency_window: int | str | None = Field(
        default=None,
        description="Optional recency window in seconds or duration string to restrict fresh candidates",
    )
    min_positive_items_for_personalization: int = Field(
        default=3,
        ge=1,
        description="Minimum positive interactions required before serving personalized recommendations",
    )
    explanation_min_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Minimum contribution share required to display an explanation reason",
    )


class ChatConfig(SchemaBase):
    """Configuration for domain-specific conversational assistant concierge."""

    noun: str = Field(
        default="item", description="Domain item noun (e.g. 'movie', 'product', 'article')"
    )
    card_fields: list[str] = Field(
        default_factory=lambda: ["title", "subtitle", "categories", "year"],
        description="Metadata fields to display in chat recommendation pick cards",
    )
    starter_prompts: list[str] = Field(
        default_factory=lambda: [
            "Suggest top recommendations based on my profile",
            "What hidden gems do you recommend?",
            "Explain why these items match my taste",
        ],
        description="Starter prompt chips shown in the chat panel",
    )
    persona_wording: str = Field(
        default="taste preferences and history",
        description="Descriptive wording of the user persona/taste for system prompts",
    )


class ContentTypeSpec(SchemaBase):
    """Top-level specification for a content type loaded from YAML."""

    type: str = Field(
        ..., min_length=1, description="Internal slug (e.g. content domain identifier)"
    )
    display_name: str = Field(..., min_length=1, description="UI display title")
    card_type: Literal["movie", "product", "article"] = Field(
        ..., description="Frontend card presentation variant"
    )
    dataset: DatasetConfig
    signal: SignalConfig
    split: SplitConfig
    model: ModelConfig
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    serving: ServingConfig = Field(default_factory=ServingConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)
    fast: dict[str, Any] | None = Field(
        default=None, description="Optional overrides applied in --fast mode"
    )
    test_only: bool = Field(
        default=False,
        description="Whether this content type is test-only and excluded from public serving",
    )
