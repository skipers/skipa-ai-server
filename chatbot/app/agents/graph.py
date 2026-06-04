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
    return """flowchart TD
  A[질문 입력] --> B[대화 이력/선택 특허 정리]
  B --> C[Ollama 경량 LLM 의도 파악]
  C --> D{외부 정보가 필요한가?}

  D -- 아니오 --> E[특허 원문/보고서 core vectorstore 검색]
  D -- 예 --> F[특허별 wiki vectorstore 유사도 확인]
  F --> G{wiki 유사도 충분?}
  G -- 예 --> H[wiki를 web 대체 근거로 사용]
  G -- 아니오 --> I[Tavily 웹검색]

  E --> J[Hybrid Retrieval 먼저 시도]
  J --> M{source guard 통과?}
  M -- 예 --> N[FAISS+BM25+RRF + OpenAI 답변]
  M -- 아니오 --> O[core vectorstore + OpenAI 답변]
  H --> J
  I --> J
  N --> K[근거 카드 + 품질 지표]
  O --> K
  K --> L[UI/Swagger 응답]
"""
