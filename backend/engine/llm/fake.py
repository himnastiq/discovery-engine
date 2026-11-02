"""Discovery Engine - Fake LLM Client for hermetic testing (P13.5)."""

from __future__ import annotations

import json

from engine.llm.types import (
    LLMPick,
    LLMRequest,
    LLMResult,
)


class FakeLLMClient:
    """Scriptable in-memory LLM client for testing without external network calls."""

    def __init__(
        self,
        scripted_results: list[LLMResult | Exception] | None = None,
        default_model: str = "fake-gemini-model",
    ) -> None:
        self.scripted_results: list[LLMResult | Exception] = (
            list(scripted_results) if scripted_results is not None else []
        )
        self.default_model = default_model
        self.history: list[LLMRequest] = []
        self.call_count: int = 0

    async def complete(self, request: LLMRequest) -> LLMResult:
        """Record the request and return the next scripted response or generate a deterministic pick."""
        self.history.append(request)
        self.call_count += 1

        if self.scripted_results:
            next_item = self.scripted_results.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            return next_item

        # Deterministic default: pick up to 3 candidate items
        num_picks = min(3, len(request.candidate_ids))
        picks: list[LLMPick] = [
            LLMPick(
                item_id=cid,
                reason=f"Selected candidate #{idx + 1} based on user profile alignment.",
            )
            for idx, cid in enumerate(request.candidate_ids[:num_picks])
        ]

        reply = (
            "Here are recommended selections tailored to your preferences: "
            + ", ".join(f"Item {p.item_id}" for p in picks)
            + "."
        )

        raw_json = json.dumps(
            {
                "reply": reply,
                "picks": [{"item_id": p.item_id, "reason": p.reason} for p in picks],
            }
        )

        return LLMResult(
            reply=reply,
            picks=picks,
            model=self.default_model,
            latency_ms=15,
            raw_text=raw_json,
            meta={"simulated": True, "call_index": self.call_count},
        )

    def reset(self) -> None:
        """Clear recorded call history and reset state."""
        self.history.clear()
        self.scripted_results.clear()
        self.call_count = 0
