"""Retrieve audited wiki/reviewed context before final answer generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..store import search_chunks
from ..vectorstore import get_patent_draft_stats
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
            draft_stats = get_patent_draft_stats(patent_id) if patent_id else {}
            pending = draft_stats.get("pending_review", 0)
            auto_approved = draft_stats.get("auto_approved", 0)
            if auto_approved > 0:
                result["fallback_reason"] = (
                    f"no high-similarity WIKI hit; {auto_approved} auto-approved draft(s) exist "
                    "but vectorstore may need refresh — web search will run"
                )
            elif pending > 0:
                result["fallback_reason"] = (
                    f"no high-similarity WIKI hit; {pending} pending draft(s) awaiting audit "
                    "— web search will run"
                )
            else:
                result["fallback_reason"] = "no high-similarity patent-local WIKI hit; web search may run next"
            result["draft_stats"] = draft_stats

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
            "draft_stats": result.get("draft_stats"),
        }
    )
    return {**state, "wiki_context": result, "trace": trace}
