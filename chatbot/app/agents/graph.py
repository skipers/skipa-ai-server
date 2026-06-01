"""LangGraph chatbot answer workflow.

This file restores the source counterpart for the previous chatbot agent
modules. It uses LangGraph when available and falls back to a simple sequential
runner, so the app can run even in lightweight local environments.
"""

from __future__ import annotations

from typing import Any

from .history_agent import resolve_history_context
from .merge_agent import finish_answer
from .patent_agent import answer_from_patent_context
from .router_agent import route_question
from .state import ChatAgentState
from .web_agent import retrieve_web_context
from .wiki_context_agent import retrieve_wiki_context


def _sequential(state: ChatAgentState) -> ChatAgentState:
    state = resolve_history_context(state)
    state = route_question(state)
    state = retrieve_wiki_context(state)
    state = retrieve_web_context(state)
    state = answer_from_patent_context(state)
    return finish_answer(state)


def build_chat_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ChatAgentState)
        graph.add_node("resolve_history_context", resolve_history_context)
        graph.add_node("route_question", route_question)
        graph.add_node("retrieve_wiki_context", retrieve_wiki_context)
        graph.add_node("retrieve_web_context", retrieve_web_context)
        graph.add_node("answer_from_patent_context", answer_from_patent_context)
        graph.add_node("finish_answer", finish_answer)
        graph.set_entry_point("resolve_history_context")
        graph.add_edge("resolve_history_context", "route_question")
        graph.add_edge("route_question", "retrieve_wiki_context")
        graph.add_edge("retrieve_wiki_context", "retrieve_web_context")
        graph.add_edge("retrieve_web_context", "answer_from_patent_context")
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
    user_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    context_patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    state: ChatAgentState = {
        "query": query,
        "patent_id": patent_id,
        "user_id": user_id,
        "chat_history": chat_history or [],
        "context_patent_id": context_patent_id,
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


def chat_graph_mermaid() -> str:
    if CHAT_GRAPH is not None:
        try:
            return CHAT_GRAPH.get_graph().draw_mermaid()
        except Exception:
            pass
    return """flowchart TD
  A[Chat API Request] --> B[resolve_history_context]
  B --> C[route_question / lightweight LLM intent]
  C --> D[retrieve_wiki_context]
  D --> E[retrieve_web_context]
  E --> F[answer_from_patent_context]
  F --> G[finish_answer]
  G --> H[Answer + source_cards + metrics]
"""
