"""Discovery Engine - Chatbot / Concierge API Endpoints (Phase 13, P13.14).

Provides:
- GET /v1/chat/status: Readiness and model status for UI onboarding.
- POST /v1/chat: Natural language recommendations concierge over engine candidates.
Grounded exclusively in recommendation engine candidates with guaranteed engine-only fallback.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request

from api.deps import resolve_model, resolve_type_lookups
from api.errors import ChatRateLimitedError, ChatUnavailableError
from api.schemas import ChatRequest, ChatResponse, ChatStatusResponse
from engine.errors import UnknownUser
from engine.llm.cache import ChatResponseCache, compute_cache_key
from engine.llm.candidates import assemble_candidates
from engine.llm.fallback import build_fallback_response, map_error_to_fallback_reason
from engine.llm.gemini import GeminiClient
from engine.llm.prompt import build_chat_request
from engine.llm.rate_limit import IPRateLimiter
from engine.llm.settings import ChatSettings, load_chat_settings
from engine.llm.validator import validate_chat_output

if TYPE_CHECKING:
    from engine.llm.quota import QuotaManager
    from engine.llm.types import LLMClient

router = APIRouter(prefix="/v1", tags=["chat"])


@router.get("/chat/status", response_model=ChatStatusResponse)
def get_chat_status(request: Request) -> ChatStatusResponse:
    """Readiness and configuration status for the Discovery Assistant."""
    settings: ChatSettings = (
        getattr(request.app.state, "chat_settings", None) or load_chat_settings()
    )
    quota_mgr: QuotaManager | None = getattr(request.app.state, "chat_quota_manager", None)
    llm_client: LLMClient | None = getattr(request.app.state, "llm_client", None)

    ready = False
    if settings.enabled:
        if llm_client is not None:
            ready = True
        elif settings.api_keys:
            if quota_mgr is not None:
                ready = any(not b.disabled for b in quota_mgr.buckets)
            else:
                ready = True

    return ChatStatusResponse(
        enabled=settings.enabled,
        ready=ready,
        model=settings.model if settings.enabled else None,
    )


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    request: Request,
    payload: ChatRequest,
) -> ChatResponse:
    """Conversational recommendations grounded in candidate items from the engine."""
    t0 = time.perf_counter()

    # 1. Kill switch verification
    settings: ChatSettings = (
        getattr(request.app.state, "chat_settings", None) or load_chat_settings()
    )
    if not settings.enabled:
        raise ChatUnavailableError("Chat concierge is currently disabled.")

    # 2. Per-IP sliding-window rate limit
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "127.0.0.1"
    )
    ip_limiter: IPRateLimiter | None = getattr(request.app.state, "chat_ip_limiter", None)
    if ip_limiter is None:
        ip_limiter = IPRateLimiter(rpm=settings.ip_rpm)
        request.app.state.chat_ip_limiter = ip_limiter
    else:
        ip_limiter.rpm = settings.ip_rpm

    allowed, retry_after = ip_limiter.check_and_record(client_ip)
    if not allowed:
        raise ChatRateLimitedError(retry_after=retry_after)

    # 3. Content type and user verification
    type_slug = payload.type.strip().lower()
    lookups = resolve_type_lookups(request, type_slug)
    model = resolve_model(request, type_slug)
    spec = lookups.spec

    uid_str: str | None = None
    if payload.user_id is not None:
        uid_str = str(payload.user_id).strip()
        if uid_str not in lookups.user_ids:
            raise UnknownUser(user_id=uid_str, content_type=type_slug)

    # 4. In-memory search index for keyword retrieval
    search_indexes = getattr(request.app.state, "search_indexes", {})
    search_index = search_indexes.get(type_slug)

    # 5. Candidate pool assembly strictly from recommendation engine
    last_message = payload.messages[-1].content
    candidates = assemble_candidates(
        lookups=lookups,
        model=model,
        user_id=uid_str,
        last_user_message=last_message,
        search_index=search_index,
        max_candidates=40,
    )

    # 6. Response cache and in-flight request coalescing
    cache: ChatResponseCache | None = getattr(request.app.state, "chat_cache", None)
    if cache is None:
        cache = ChatResponseCache(ttl_s=float(settings.cache_ttl_s))
        request.app.state.chat_cache = cache

    candidate_ids = [c["item_id"] for c in candidates]
    cache_key = compute_cache_key(
        content_type=type_slug,
        user_id=uid_str,
        last_message=last_message,
        candidate_ids=candidate_ids,
        model=settings.model or "gemini",
    )

    async def compute_response() -> dict[str, Any]:
        llm_client: LLMClient | None = getattr(request.app.state, "llm_client", None)
        quota_mgr: QuotaManager | None = getattr(request.app.state, "chat_quota_manager", None)

        # If no client and no credentials configured -> immediate fallback
        if not settings.api_keys and llm_client is None:
            return build_fallback_response(
                spec=spec,
                candidates=candidates,
                fallback_reason="no_credentials",
                model_name=settings.model,
            )

        # Pick credential from QuotaManager
        project_id: str | None = None
        key_for_req: str | None = None
        if quota_mgr is not None and llm_client is None:
            key_for_req, project_id, retry_after_s = await quota_mgr.pick_credential()
            if key_for_req is None:
                retry_s = max(1, math.ceil(retry_after_s)) if retry_after_s is not None else None
                return build_fallback_response(
                    spec=spec,
                    candidates=candidates,
                    fallback_reason="rate_limited",
                    model_name=settings.model,
                    retry_after_s=retry_s,
                )

        # Instantiate client if needed
        client: LLMClient | None = llm_client
        if client is None and key_for_req is not None:
            client = GeminiClient(
                api_key=key_for_req,
                model=settings.model,
                timeout_s=float(settings.timeout_s),
            )

        if client is None:
            return build_fallback_response(
                spec=spec,
                candidates=candidates,
                fallback_reason="no_credentials",
                model_name=settings.model,
            )

        recent_interactions = [
            i.get("title", "") for i in lookups.user_recent_interactions.get(uid_str or "", [])
        ]
        llm_req = build_chat_request(
            spec=spec,
            messages=[{"role": m.role, "content": m.content} for m in payload.messages],
            candidates=candidates,
            persona=lookups.user_persona.get(uid_str or ""),
            top_categories=lookups.user_category_shares.get(uid_str or ""),
            recent_items=recent_interactions,
            max_output_tokens=settings.max_output_tokens,
        )

        try:
            result = await client.complete(llm_req)
            raw_text = result.raw_text or ""
            validated = validate_chat_output(raw_text, candidates)
            if quota_mgr is not None and project_id is not None:
                quota_mgr.record_success(project_id)

            return {
                "reply": validated.reply,
                "picks": [p.to_dict() for p in validated.picks],
                "mode": "llm",
                "meta": {
                    "model": settings.model,
                    "latency_ms": 0,
                    "cache_hit": False,
                    "fallback_reason": None,
                    "retry_after_s": None,
                },
            }
        except Exception as exc:
            if quota_mgr is not None and project_id is not None:
                from engine.llm.errors import LLMAuthError, LLMRateLimited

                if isinstance(exc, LLMRateLimited):
                    quota_mgr.record_rate_limited(project_id, exc.retry_after)
                elif isinstance(exc, LLMAuthError) and key_for_req:
                    quota_mgr.record_auth_error(project_id, key_for_req)
            fallback_reason, retry_s = map_error_to_fallback_reason(exc)
            return build_fallback_response(
                spec=spec,
                candidates=candidates,
                fallback_reason=fallback_reason,
                model_name=settings.model,
                retry_after_s=retry_s,
            )

    resp_dict, is_cache_hit = await cache.get_or_compute(cache_key, compute_response)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    resp_dict["meta"]["latency_ms"] = elapsed_ms
    resp_dict["meta"]["cache_hit"] = is_cache_hit

    return ChatResponse.model_validate(resp_dict)
