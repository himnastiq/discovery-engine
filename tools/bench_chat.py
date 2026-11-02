"""Discovery Engine - Chatbot Performance & Concurrency Benchmark (Phase 13, P13.17).

Verifies Gate R12 Performance Invariants:
1. With FakeLLMClient, /v1/chat adds under 50 ms p95 overhead over engine candidate retrieval calls.
2. Async LLM execution does not block other endpoints: /v1/recommend while chat is in-flight stays within its budget (p95 < 150 ms).
3. Produces structured metrics recorded into docs/RESULTS.md.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from api.main import create_app, lifespan
from api.routes.chat import assemble_candidates
from engine import registry
from engine.llm.fake import FakeLLMClient
from engine.llm.settings import ChatSettings


def percentile(data: list[float], pct: float) -> float:
    """Compute percentile from float list."""
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return s[f] * (1.0 - d) + s[c] * d


async def run_benchmark() -> dict[str, Any]:
    app = create_app()

    async with lifespan(app):
        app.state.chat_settings = ChatSettings(
            enabled=True,
            api_keys=["bench-key"],
            model="gemini-2.5-flash",
            ip_rpm=10000,
            cache_ttl_s=0,  # disable cache during latency benchmark to test full pipeline
        )
        fake_client = FakeLLMClient(default_model="gemini-2.5-flash")
        app.state.llm_client = fake_client

        content_types = registry.public_types()
        bench_results: dict[str, Any] = {}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            # 1. Warm-up all types and initialize lazy search indexes
            for ct in content_types:
                lookups = app.state.lookups[ct]
                demo_user = next(iter(lookups.user_ids)) if lookups.user_ids else None
                for _ in range(10):
                    await client.post(
                        "/v1/chat",
                        json={
                            "type": ct,
                            "user_id": demo_user,
                            "messages": [
                                {"role": "user", "content": "Warmup search query"}
                            ],
                        },
                    )
                    await client.get(
                        f"/v1/recommend?type={ct}&user_id={demo_user}&k=10"
                    )

            # 2. Benchmark overhead of /v1/chat over engine candidate retrieval
            for ct in content_types:
                lookups = app.state.lookups[ct]
                model = app.state.models[ct]
                search_idx = app.state.search_indexes.get(ct)
                demo_user = next(iter(lookups.user_ids)) if lookups.user_ids else None

                engine_latencies: list[float] = []
                chat_latencies: list[float] = []

                num_samples = 50
                for i in range(num_samples):
                    msg = f"Recommendation inquiry test query {i}"

                    # Measure pure engine candidate assembly
                    t0 = time.perf_counter()
                    assemble_candidates(
                        lookups=lookups,
                        model=model,
                        user_id=demo_user,
                        last_user_message=msg,
                        search_index=search_idx,
                        max_candidates=40,
                    )
                    t_engine = (time.perf_counter() - t0) * 1000.0
                    engine_latencies.append(t_engine)

                    # Measure full /v1/chat endpoint with FakeLLMClient
                    t0 = time.perf_counter()
                    resp = await client.post(
                        "/v1/chat",
                        json={
                            "type": ct,
                            "user_id": demo_user,
                            "messages": [{"role": "user", "content": msg}],
                        },
                    )
                    assert resp.status_code == 200
                    t_chat = (time.perf_counter() - t0) * 1000.0
                    chat_latencies.append(t_chat)

                eng_p50 = percentile(engine_latencies, 50)
                eng_p95 = percentile(engine_latencies, 95)
                chat_p50 = percentile(chat_latencies, 50)
                chat_p95 = percentile(chat_latencies, 95)
                overhead_p95 = max(0.0, chat_p95 - eng_p95)

                bench_results[ct] = {
                    "engine_p50_ms": round(eng_p50, 2),
                    "engine_p95_ms": round(eng_p95, 2),
                    "chat_p50_ms": round(chat_p50, 2),
                    "chat_p95_ms": round(chat_p95, 2),
                    "overhead_p95_ms": round(overhead_p95, 2),
                    "p95_under_50ms": overhead_p95 < 50.0,
                }

            # 3. Concurrency non-blocking load check:
            # While in-flight chat requests are awaiting async LLM completion,
            # execute concurrent /v1/recommend requests and verify p95 stays under 150 ms.
            recommend_latencies: list[float] = []
            test_types = ["movies", "products"]

            for round_idx in range(20):
                target_type = test_types[round_idx % len(test_types)]
                lookups = app.state.lookups[target_type]
                demo_user = next(iter(lookups.user_ids)) if lookups.user_ids else None

                async def in_flight_chat(
                    ttype: str = target_type,
                    uid: str | None = demo_user,
                    r_idx: int = round_idx,
                ) -> None:
                    # Chat request in flight
                    r = await client.post(
                        "/v1/chat",
                        json={
                            "type": ttype,
                            "user_id": uid,
                            "messages": [
                                {"role": "user", "content": f"In-flight query {r_idx}"}
                            ],
                        },
                    )
                    assert r.status_code == 200

                async def concurrent_recommend(
                    ttype: str = target_type,
                    uid: str | None = demo_user,
                ) -> None:
                    # Stagger slightly (2ms) so chat request is active in event loop
                    await asyncio.sleep(0.002)
                    t0 = time.perf_counter()
                    r = await client.get(
                        f"/v1/recommend?type={ttype}&user_id={uid}&k=10"
                    )
                    assert r.status_code == 200
                    recommend_latencies.append((time.perf_counter() - t0) * 1000.0)

                await asyncio.gather(in_flight_chat(), concurrent_recommend())

            rec_p50 = percentile(recommend_latencies, 50)
            rec_p95 = percentile(recommend_latencies, 95)

            bench_results["concurrency"] = {
                "concurrent_rounds": len(recommend_latencies),
                "recommend_p50_ms": round(rec_p50, 2),
                "recommend_p95_ms": round(rec_p95, 2),
                "recommend_budget_150ms": rec_p95 < 150.0,
            }

    return bench_results


def main() -> None:
    print("Running P13.17 Chatbot Performance & Concurrency Benchmark...")
    results = asyncio.run(run_benchmark())
    print("\nBenchmark Results:")
    print(json.dumps(results, indent=2))

    for ct, metrics in results.items():
        if ct == "concurrency":
            continue
        print(
            f"[{ct.upper()}] Engine p95: {metrics['engine_p95_ms']} ms | Chat p95: {metrics['chat_p95_ms']} ms | Overhead p95: {metrics['overhead_p95_ms']} ms (Budget: < 50 ms)"
        )
        assert metrics["p95_under_50ms"], (
            f"Overhead p95 for {ct} is {metrics['overhead_p95_ms']} ms, exceeding 50 ms budget!"
        )

    print(
        f"[CONCURRENCY] GET /v1/recommend during in-flight chat: p50={results['concurrency']['recommend_p50_ms']} ms, p95={results['concurrency']['recommend_p95_ms']} ms (Budget: < 150 ms)"
    )
    assert results["concurrency"]["recommend_budget_150ms"], (
        f"Recommend p95 under load is {results['concurrency']['recommend_p95_ms']} ms, exceeding 150 ms budget!"
    )
    print("\nAll performance and concurrency budgets verified successfully!")


if __name__ == "__main__":
    main()
