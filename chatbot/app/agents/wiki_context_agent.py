"""Retrieve audited wiki/reviewed context before final answer generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..store import search_chunks
from .state import ChatAgentState


MIN_WIKI_GATE_SCORE = 0.32


def retrieve_wiki_context(state: ChatAgentState) -> ChatAgentState:
    intent = state.get("intent") or {}
    should_search = bool(intent.get("needs_web"))
    result: dict[str, Any] = {"enabled": should_search, "hit_count": 0, "hits": []}
    if should_search:
        patent_id = state.get("resolved_patent_id") or state.get("patent_id")
        result = search_chunks(
            state.get("query", ""),
            patent_id=patent_id,
            source_types={"WIKI"},
            top_k=min(int(state.get("top_k") or 5), 5),
        )
        hits = [
            hit
            for hit in result.get("hits", [])
            if isinstance(hit, dict) and float(hit.get("score") or 0.0) >= MIN_WIKI_GATE_SCORE
        ]
        result["raw_hit_count"] = result.get("hit_count", 0)
        result["min_gate_score"] = MIN_WIKI_GATE_SCORE
        result["hits"] = hits
        result["hit_count"] = len(hits)
        result["gate_passed"] = bool(hits)
        if not hits:
            result["fallback_reason"] = "no high-similarity patent-local WIKI hit; web search may run next"

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "retrieve_wiki_context",
            "status": "success",
            "at": datetime.now().isoformat(timespec="seconds"),
            "enabled": should_search,
            "hit_count": result.get("hit_count", 0),
            "raw_hit_count": result.get("raw_hit_count"),
            "min_gate_score": result.get("min_gate_score"),
            "gate_passed": result.get("gate_passed"),
            "mode": result.get("mode"),
            "fallback_reason": result.get("fallback_reason"),
        }
    )
    return {**state, "wiki_context": result, "trace": trace}
