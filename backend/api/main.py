"""Discovery Engine - FastAPI application (Phase 7, P7.1)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Critical performance and thread isolation: Set thread limits before importing numpy
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except (ImportError, OSError):
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_error_handlers
from api.lookups import build_type_lookups
from api.routes.chat import router as chat_router
from api.routes.metadata import router as metadata_router
from api.routes.recommend import router as recommend_router
from api.routes.users import router as users_router
from api.search import LazySearchIndex
from api.security import SecurityMiddleware
from engine import registry
from engine.artifacts import load_artifacts, verify_artifacts
from engine.config import resolve_serving_config
from engine.llm.cache import ChatResponseCache
from engine.llm.quota import QuotaManager
from engine.llm.rate_limit import IPRateLimiter
from engine.llm.settings import load_chat_settings, log_chat_startup
from engine.logging_utils import configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def get_env_config() -> dict[str, Any]:
    """Load configuration from environment variables."""
    art_dir_str = os.environ.get("ARTIFACT_DIR")
    artifact_dir = Path(art_dir_str) if art_dir_str else DEFAULT_ARTIFACTS_DIR

    api_key = os.environ.get("RECOMMENDER_API_KEY")

    cors_str = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [o.strip() for o in cors_str.split(",") if o.strip()]

    env_mode = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    if "*" in cors_origins:
        if env_mode in ("prod", "production"):
            raise ValueError(
                "Insecure configuration: CORS wildcard '*' is not permitted when ENV=production."
            )
        logging.getLogger("api.main").warning(
            "SECURITY WARNING: CORS wildcard '*' is active. Disabling credentials. Do not use wildcard CORS in production."
        )

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    return {
        "artifact_dir": artifact_dir,
        "api_key": api_key,
        "cors_origins": cors_origins,
        "log_level": log_level,
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager: loads artifacts on startup."""
    config = get_env_config()
    configure_logging(level=getattr(logging, config["log_level"], logging.INFO))
    logger = get_logger("api.main")

    app.state.artifact_dir = config["artifact_dir"]
    app.state.api_key = config["api_key"]
    app.state.configs = {}
    app.state.lookups = {}
    app.state.artifacts = {}
    app.state.models = {}
    app.state.search_indexes = {}
    app.state.availability = {}
    app.state.unavailable_reasons = {}

    artifact_root = config["artifact_dir"]
    logger.info("Initializing Discovery Engine API from artifacts: %s", artifact_root)

    available_types = registry.public_types()
    for content_type in available_types:
        type_dir = artifact_root / content_type
        if not type_dir.exists():
            reason = f"Artifact directory not found at {type_dir}"
            app.state.availability[content_type] = False
            app.state.unavailable_reasons[content_type] = reason
            logger.warning("Content type '%s' unavailable: %s", content_type, reason)
            continue

        try:
            # 1. Cryptographic verification & artifact bundle loading
            verify_artifacts(type_dir)
            loaded = load_artifacts(type_dir, verify=False)

            # 2. Recommender model reconstitution from manifest-verified serving config (FIX-37)
            spec = resolve_serving_config(content_type, type_dir)
            model = registry.build_model(spec)
            model.load(loaded.model_dir)

            # 3. Build in-memory lookup structures (FIX-34)
            lookups = build_type_lookups(spec, loaded)

            # 4. Build text search index (lazy initialization for fast startup)
            search_index = LazySearchIndex(loaded.items, loaded.interactions)

            app.state.configs[content_type] = spec
            app.state.lookups[content_type] = lookups
            app.state.artifacts[content_type] = loaded
            app.state.models[content_type] = model
            app.state.search_indexes[content_type] = search_index
            app.state.availability[content_type] = True
            logger.info("Content type '%s' loaded successfully.", content_type)
        except Exception as exc:
            reason = f"Failed to load artifacts for '{content_type}': {exc}"
            app.state.availability[content_type] = False
            app.state.unavailable_reasons[content_type] = reason
            logger.warning(
                "Content type '%s' failed to load (marking unavailable): %s", content_type, reason
            )

    # 5. Initialize Chat concierge state (Phase 13, P13.14)
    chat_settings = load_chat_settings()
    log_chat_startup(chat_settings)
    app.state.chat_settings = chat_settings
    app.state.chat_cache = ChatResponseCache(ttl_s=float(chat_settings.cache_ttl_s))
    app.state.chat_ip_limiter = IPRateLimiter(rpm=chat_settings.ip_rpm)
    if chat_settings.api_keys:
        app.state.chat_quota_manager = QuotaManager(
            api_keys=chat_settings.api_keys,
            projects=chat_settings.key_projects,
            rpm_per_project=chat_settings.rpm_per_project,
        )
    else:
        app.state.chat_quota_manager = None
    app.state.llm_client = None

    yield

    logger.info("Discovery Engine API shutting down.")


def create_app() -> FastAPI:
    """Factory function for FastAPI application."""
    config = get_env_config()
    app = FastAPI(
        title="Discovery Engine",
        version="1.0.0",
        debug=False,
        lifespan=lifespan,
    )

    # Security middleware (API key check & body size limit)
    app.add_middleware(SecurityMiddleware)

    # CORS Middleware configuration (outermost so CORS headers apply to all responses)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config["cors_origins"],
        allow_credentials="*" not in config["cors_origins"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register standardized error handlers (P7.2)
    register_error_handlers(app)

    # Register routers (P7.3, P7.4, P7.5, P13.14)
    app.include_router(metadata_router)
    app.include_router(users_router)
    app.include_router(recommend_router)
    app.include_router(chat_router)

    # Root /health alias for load balancers and platform monitors
    @app.get("/health", include_in_schema=False)
    def root_health(request: Request) -> Any:
        from api.routes.metadata import get_health

        return get_health(request)

    return app


app = create_app()
