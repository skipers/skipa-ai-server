"""Retrieve audited wiki/reviewed context before final answer generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..store import search_chunks
from .state import ChatAgentState


def retrieve_wiki_context(state: ChatAgentState) -> ChatAgentState:
    intent = state.get("intent") or {}
    source_plan = set(intent.get("source_plan") or [])
    should_search = "wiki" in source_plan or "reviewed_vectorstore" in source_plan or intent.get("intent") == "wiki"
    result: dict[str, Any] = {"enabled": should_search, "hit_count": 0, "hits": []}
    if should_search:
        result = search_chunks(
            state.get("query", ""),
            patent_id=state.get("resolved_patent_id") or state.get("patent_id"),
            source_types={"WIKI"},
            top_k=min(int(state.get("top_k") or 5), 5),
        )
        if result.get("hit_count", 0) == 0:
            result = search_chunks(
                state.get("query", ""),
                patent_id=state.get("resolved_patent_id") or state.get("patent_id"),
                source_types=None,
                top_k=min(int(state.get("top_k") or 5), 5),
            )
            result["fallback_reason"] = "no WIKI source hits; searched human-reviewed vectorstore"

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "retrieve_wiki_context",
            "status": "success",
            "at": datetime.now().isoformat(timespec="seconds"),
            "enabled": should_search,
            "hit_count": result.get("hit_count", 0),
            "mode": result.get("mode"),
            "fallback_reason": result.get("fallback_reason"),
        }
    )
    return {**state, "wiki_context": result, "trace": trace}
