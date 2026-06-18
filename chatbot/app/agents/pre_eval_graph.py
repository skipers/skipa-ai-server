"""LangGraph chatbot for pre-application evaluation cases.

Reuses the existing chat graph nodes (history, router, wiki, web, merge)
and adds a pre-eval-specific context retrieval node that searches the
case's own vectorstore.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..rag.llm import call_openai_prompt, call_opensource_prompt
from ..rag.config import ANSWER_LLM_TIMEOUT, ANSWER_MODEL, ANSWER_PROVIDER
from ..rag.evaluation import answer_quality_metrics
from ..rag.quality import compact_text, filter_usable_hits
from ..rag.sources import cards_from_hits, cards_from_web
from ..rag.web_answers import search_web
from typing import Any, TypedDict

from .history_agent import resolve_history_context
from .merge_agent import finish_answer
from .router_agent import route_question
from .state import ChatAgentState
from .web_agent import retrieve_web_context
from .wiki_context_agent import retrieve_wiki_context


class PreEvalAgentState(ChatAgentState, total=False):
    pre_eval_hits: list[dict[str, Any]]
    pre_eval_search: dict[str, Any]


# ---------------------------------------------------------------------------
# Pre-eval context retrieval node
# ---------------------------------------------------------------------------

def retrieve_pre_eval_context(state: ChatAgentState) -> ChatAgentState:
    """Search the backend case-id vectorstore and fall back to legacy cases."""
    from ..pre_eval_data import search_pre_application_vectorstore, search_pre_eval_vectorstore

    case_id = str(state.get("patent_id") or "")
    if not case_id:
        return state

    top_k = int(state.get("top_k") or 8)
    query = state.get("retrieval_query") or state.get("query") or ""
    result = search_pre_application_vectorstore(case_id, query, top_k=top_k)
    fallback_used = False
    if int(result.get("hit_count") or 0) == 0:
        legacy_result = search_pre_eval_vectorstore(case_id, query, top_k=top_k)
        if int(legacy_result.get("hit_count") or 0) > 0:
            result = legacy_result
            fallback_used = True

    trace = list(state.get("trace") or [])
    trace.append({
        "node": "retrieve_pre_eval_context",
        "status": "success",
        "at": datetime.now().isoformat(timespec="seconds"),
        "case_id": case_id,
        "hit_count": result.get("hit_count", 0),
        "collection": result.get("collection"),
        "mode": result.get("mode"),
        "fallback_used": fallback_used,
    })
    return {**state, "pre_eval_hits": result.get("hits", []), "pre_eval_search": result, "trace": trace}


# ---------------------------------------------------------------------------
# Pre-eval answer generation node
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """당신은 출원 전 특허 사전평가 결과를 설명하는 전문 AI 어시스턴트입니다.
제공된 사전평가 보고서 근거를 바탕으로 정확하고 실용적으로 답변하세요.
- 등급, 점수, 영역별 분석, 개선 권고사항을 구체적으로 설명하세요.
- 특허 출원 전 개선할 수 있는 실질적인 조언을 제공하세요.
- 상세 질문이면 요약으로 끝내지 말고 평가 근거, 약점, 보완 액션, 우선순위를 단계별로 설명하세요.
- 근거 없는 추측은 하지 마세요."""


def answer_pre_eval_question(state: ChatAgentState) -> ChatAgentState:
    """Generate answer from pre-eval case vectorstore hits + wiki/web context."""
    query = state.get("query") or ""
    pre_eval_hits = list(state.get("pre_eval_hits") or [])
    intent = state.get("intent") or {}
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=3)
    web_context = dict(state.get("web_context") or {})
    web_results = list(web_context.get("results") or [])

    # Build context from pre-eval hits
    context_parts: list[str] = []
    for hit in filter_usable_hits(pre_eval_hits, limit=6):
        meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        section = meta.get("section_title") or "사전평가 보고서"
        context_parts.append(f"[{section}]\n{compact_text(hit.get('page_content'), 600)}")

    for hit in wiki_hits:
        context_parts.append(f"[Wiki 배경]\n{compact_text(hit.get('page_content'), 400)}")

    for r in web_results[:2]:
        if r.get("snippet"):
            context_parts.append(f"[웹 참고]\n{compact_text(r.get('snippet'), 300)}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "사전평가 결과 데이터가 없습니다."

    intent_info = ""
    if intent.get("answer_format") == "table":
        intent_info = "\n답변을 표 형식으로 정리하세요."
    elif intent.get("needs_diagram"):
        intent_info = "\n필요한 경우 mermaid 다이어그램을 포함하세요."

    prompt = (
        f"{_SYSTEM_PROMPT}{intent_info}\n\n"
        f"## 사전평가 보고서 근거\n\n{context_text}\n\n"
        f"## 질문\n\n{query}"
    )

    try:
        call_fn = call_opensource_prompt if ANSWER_PROVIDER == "opensource" else call_openai_prompt
        llm_result = call_fn(
            prompt,
            model=ANSWER_MODEL,
            timeout=ANSWER_LLM_TIMEOUT,
        )
        answer = str(llm_result.get("text") or "") if isinstance(llm_result, dict) else str(llm_result)
        if not answer:
            answer = "답변을 생성하지 못했습니다. 사전평가 보고서를 확인해 주세요."
    except Exception as exc:
        answer = f"답변 생성 실패: {exc}"

    # Source cards
    source_cards = cards_from_hits(pre_eval_hits[:5], query=query)
    if wiki_hits:
        source_cards += cards_from_hits(wiki_hits, query=query)
    if web_results:
        source_cards += cards_from_web(web_results[:2], start_index=len(source_cards) + 1, query=query)

    metrics = {
        "pre_eval_hit_count": len(pre_eval_hits),
        "pre_eval_collection": (state.get("pre_eval_search") or {}).get("collection"),
        "pre_eval_search_mode": (state.get("pre_eval_search") or {}).get("mode"),
        "wiki_hit_count": len(wiki_hits),
        "web_result_count": len(web_results),
        "intent_agent": intent,
        "answer_quality": answer_quality_metrics(
            query=query,
            answer=answer,
            source_cards=source_cards,
            retrieval_scores=[float(h.get("score", 0)) for h in pre_eval_hits],
        ),
    }

    trace = list(state.get("trace") or [])
    trace.append({
        "node": "answer_pre_eval_question",
        "status": "success",
        "at": datetime.now().isoformat(timespec="seconds"),
        "pre_eval_hits": len(pre_eval_hits),
    })

    result = {
        "query": query,
        "answer": answer,
        "source_cards": source_cards,
        "metrics": metrics,
    }
    return {**state, "result": result, "trace": trace}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _sequential_pre_eval(state: ChatAgentState) -> ChatAgentState:
    state = resolve_history_context(state)
    state = route_question(state)
    state = retrieve_pre_eval_context(state)
    state = retrieve_wiki_context(state)
    state = retrieve_web_context(state)
    state = answer_pre_eval_question(state)
    return finish_answer(state)


def build_pre_eval_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(PreEvalAgentState)
        graph.add_node("resolve_history_context", resolve_history_context)
        graph.add_node("route_question", route_question)
        graph.add_node("retrieve_pre_eval_context", retrieve_pre_eval_context)
        graph.add_node("retrieve_wiki_context", retrieve_wiki_context)
        graph.add_node("retrieve_web_context", retrieve_web_context)
        graph.add_node("answer_pre_eval_question", answer_pre_eval_question)
        graph.add_node("finish_answer", finish_answer)
        graph.set_entry_point("resolve_history_context")
        graph.add_edge("resolve_history_context", "route_question")
        graph.add_edge("route_question", "retrieve_pre_eval_context")
        graph.add_edge("retrieve_pre_eval_context", "retrieve_wiki_context")
        graph.add_edge("retrieve_wiki_context", "retrieve_web_context")
        graph.add_edge("retrieve_web_context", "answer_pre_eval_question")
        graph.add_edge("answer_pre_eval_question", "finish_answer")
        graph.add_edge("finish_answer", END)
        return graph.compile()
    except Exception:
        return None


PRE_EVAL_GRAPH = build_pre_eval_graph()


def run_pre_eval_chat_agent(
    query: str,
    *,
    case_id: str,
    user_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    """Run the pre-eval chat agent for a specific evaluation case."""
    state: PreEvalAgentState = {
        "query": query,
        "patent_id": case_id,          # reuse patent_id slot for case routing
        "user_id": user_id,
        "chat_history": chat_history or [],
        "context_patent_id": case_id,
        "source_types": None,
        "top_k": top_k,
        "trace": [],
        "errors": [],
    }
    # LangGraph 1.2.0에서 모듈 import 시점 컴파일 그래프의 state 전파 버그 우회
    final_state = _sequential_pre_eval(state)
    result = dict(final_state.get("result") or {})
    metrics = dict(result.get("metrics") or {})
    metrics["agent_trace"] = final_state.get("trace", [])
    metrics["patent_id"] = case_id
    result["metrics"] = metrics
    return {
        "query": query,
        "patent_id": case_id,
        "case_id": case_id,
        "answer": result.get("answer") or "",
        "source_cards": result.get("source_cards") or [],
        "metrics": metrics,
    }


def pre_eval_graph_mermaid() -> str:
    return """graph TD
    resolve_history_context --> route_question
    route_question --> retrieve_pre_eval_context
    retrieve_pre_eval_context --> retrieve_wiki_context
    retrieve_wiki_context --> retrieve_web_context
    retrieve_web_context --> answer_pre_eval_question
    answer_pre_eval_question --> finish_answer
    finish_answer --> END"""
