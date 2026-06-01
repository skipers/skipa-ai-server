"""Patent/report/wiki RAG agent."""

from __future__ import annotations

from datetime import datetime

from ..rag.pipeline import answer_question
from .state import ChatAgentState


def answer_from_patent_context(state: ChatAgentState) -> ChatAgentState:
    result = answer_question(
        state.get("query", ""),
        patent_id=state.get("patent_id"),
        source_types=state.get("source_types"),
        top_k=int(state.get("top_k") or 5),
    )
    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "answer_from_patent_context",
            "status": "success",
            "at": datetime.now().isoformat(timespec="seconds"),
            "hit_count": result.get("metrics", {}).get("hit_count"),
            "llm_used": result.get("metrics", {}).get("llm_used"),
        }
    )
    return {**state, "result": result, "trace": trace}
