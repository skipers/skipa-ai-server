"""Intent router agent."""

from __future__ import annotations

from datetime import datetime

from ..rag.policy import classify_intent
from .state import ChatAgentState


def route_question(state: ChatAgentState) -> ChatAgentState:
    intent = classify_intent(
        state.get("query", ""),
        chat_history=list(state.get("chat_history") or []),
        selected_patent_id=state.get("resolved_patent_id") or state.get("patent_id") or state.get("context_patent_id"),
    )
    trace = list(state.get("trace", []))
    trace.append({"node": "route_question", "status": "success", "at": datetime.now().isoformat(timespec="seconds"), "intent": intent})
    return {**state, "intent": intent, "trace": trace}
