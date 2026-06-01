"""Patent/report/wiki RAG agent."""

from __future__ import annotations

from datetime import datetime

from ..rag.legacy_adapter import try_answer_with_legacy
from ..rag.pipeline import answer_question
from ..rag.sources import cards_from_web
from .state import ChatAgentState


def answer_from_patent_context(state: ChatAgentState) -> ChatAgentState:
    patent_id = state.get("resolved_patent_id") or state.get("patent_id")
    result = try_answer_with_legacy(
        state.get("query", ""),
        patent_id=patent_id,
        top_k=int(state.get("top_k") or 5),
        user_id=state.get("user_id"),
        chat_history=state.get("chat_history"),
        context_patent_id=state.get("context_patent_id"),
    )
    if not result or result.get("metrics", {}).get("fallback_required"):
        fallback = answer_question(
            state.get("query", ""),
            patent_id=patent_id,
            source_types=state.get("source_types"),
            top_k=int(state.get("top_k") or 5),
        )
        if result:
            fallback.setdefault("metrics", {})["legacy_error"] = result.get("metrics", {}).get("legacy_error")
        result = fallback

    web_context = state.get("web_context") or {}
    web_results = list(web_context.get("results") or [])
    if web_results and not any(card.get("source_type") == "WEB" for card in result.get("source_cards") or []):
        result["source_cards"] = list(result.get("source_cards") or []) + cards_from_web(
            web_results,
            start_index=len(result.get("source_cards") or []) + 1,
        )

    metrics = dict(result.get("metrics") or {})
    metrics.update(
        {
            "resolved_patent_id": patent_id,
            "intent_agent": state.get("intent") or {},
            "wiki_context_count": (state.get("wiki_context") or {}).get("hit_count", 0),
            "wiki_context_mode": (state.get("wiki_context") or {}).get("mode"),
            "web_agent_enabled": bool(web_context.get("enabled")),
            "web_context_count": len(web_results),
            "web_provider": web_context.get("provider"),
            "answer_format_plan": (state.get("intent") or {}).get("answer_format"),
            "source_plan": (state.get("intent") or {}).get("source_plan"),
        }
    )
    result["metrics"] = metrics

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "answer_from_patent_context",
            "status": "success",
            "at": datetime.now().isoformat(timespec="seconds"),
            "engine": result.get("metrics", {}).get("engine"),
            "answer_mode": result.get("metrics", {}).get("answer_mode"),
            "source_count": len(result.get("source_cards") or []),
        }
    )
    return {**state, "result": result, "trace": trace}
