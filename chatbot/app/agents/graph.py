"""LangGraph chatbot answer workflow.

This file restores the source counterpart for the previous chatbot agent
modules. It uses LangGraph when available and falls back to a simple sequential
runner, so the app can run even in lightweight local environments.
"""

from __future__ import annotations

from typing import Any

from .merge_agent import finish_answer
from .patent_agent import answer_from_patent_context
from .router_agent import route_question
from .state import ChatAgentState


def _sequential(state: ChatAgentState) -> ChatAgentState:
    state = route_question(state)
    state = answer_from_patent_context(state)
    return finish_answer(state)


def build_chat_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ChatAgentState)
        graph.add_node("route_question", route_question)
        graph.add_node("answer_from_patent_context", answer_from_patent_context)
        graph.add_node("finish_answer", finish_answer)
        graph.set_entry_point("route_question")
        graph.add_edge("route_question", "answer_from_patent_context")
        graph.add_edge("answer_from_patent_context", "finish_answer")
        graph.add_edge("finish_answer", END)
        return graph.compile()
    except Exception:
        return None


CHAT_GRAPH = build_chat_graph()


def run_chat_agent(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    state: ChatAgentState = {
        "query": query,
        "patent_id": patent_id,
        "source_types": source_types,
        "top_k": top_k,
        "trace": [],
        "errors": [],
    }
    final_state = CHAT_GRAPH.invoke(state) if CHAT_GRAPH is not None else _sequential(state)
    result = dict(final_state.get("result") or {})
    metrics = dict(result.get("metrics") or {})
    metrics["agent_trace"] = final_state.get("trace", [])
    result["metrics"] = metrics
    return result
