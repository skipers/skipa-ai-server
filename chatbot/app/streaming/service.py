"""Streaming chat services built on the existing RAG pipeline."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..agents.history_agent import resolve_history_context
from ..agents.merge_agent import finish_answer
from ..agents.patent_agent import (
    _has_wiki_context,
    _needs_whole_patent_detail,
    _source_types_from_intent,
)
from ..agents.pre_eval_graph import (
    _SYSTEM_PROMPT as PRE_EVAL_SYSTEM_PROMPT,
    retrieve_pre_eval_context,
)
from ..agents.router_agent import route_question
from ..agents.web_agent import retrieve_web_context
from ..agents.wiki_context_agent import retrieve_wiki_context
from ..rag.config import ANSWER_LLM_TIMEOUT, ANSWER_MODEL, ANSWER_PROVIDER
from ..rag.evaluation import answer_quality_metrics
from ..rag.pipeline import finalize_prepared_answer, prepare_answer_generation
from ..rag.quality import compact_text, filter_usable_hits
from ..rag.sources import cards_from_hits, cards_from_web
from ..vectorstore import CORE_SEARCH_SOURCE_TYPES
from .openai_stream import stream_openai_prompt
from .sse import public_source_cards, sse_event


def _base_state(
    query: str,
    *,
    selected_id: str,
    user_id: str | None,
    chat_history: list[dict[str, Any]] | None,
    top_k: int,
) -> dict[str, Any]:
    return {
        "query": query,
        "patent_id": selected_id,
        "user_id": user_id,
        "chat_history": chat_history or [],
        "context_patent_id": selected_id,
        "source_types": None,
        "top_k": top_k,
        "trace": [],
        "errors": [],
    }


def _append_context_cards(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    source_cards = list(result.get("source_cards") or [])
    intent_needs_web = bool((state.get("intent") or {}).get("needs_web"))
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=3) if intent_needs_web else []
    existing_snippets = {
        str(card.get("snippet") or "")[:160]
        for card in source_cards
        if isinstance(card, dict)
    }
    wiki_cards = [
        card
        for card in cards_from_hits(wiki_hits, query=state.get("query", ""))
        if str(card.get("snippet") or "")[:160] not in existing_snippets
    ]
    if wiki_cards:
        source_cards += wiki_cards
    result["source_cards"] = source_cards
    return result


def _stream_answer(prepared: dict[str, Any]) -> Iterator[tuple[str, str]]:
    if ANSWER_PROVIDER != "openai":
        raise RuntimeError("streaming chat currently requires ANSWER_PROVIDER=openai")
    text_parts: list[str] = []
    for delta in stream_openai_prompt(
        str(prepared.get("prompt") or ""),
        model=ANSWER_MODEL,
        timeout=ANSWER_LLM_TIMEOUT,
        temperature=0.2,
    ):
        text_parts.append(delta)
        yield delta, "".join(text_parts)


def stream_re_eval_chat_events(
    *,
    patent_id: str,
    question: str,
    user_id: str | None,
    chat_history: list[dict[str, Any]] | None,
    top_k: int = 5,
) -> Iterator[str]:
    started = time.monotonic()
    answer = ""
    try:
        state = _base_state(question, selected_id=patent_id, user_id=user_id, chat_history=chat_history, top_k=top_k)
        state = resolve_history_context(state)
        state = route_question(state)
        state = retrieve_wiki_context(state)

        resolved_patent_id = state.get("resolved_patent_id") or state.get("patent_id") or patent_id
        intent = dict(state.get("intent") or {})
        intent_type = str(intent.get("intent") or "general")
        if _needs_whole_patent_detail(question, intent_type, resolved_patent_id):
            source_types = set(CORE_SEARCH_SOURCE_TYPES) | {"SHARED_PATENT", "SHARED_REPORT"}
            intent = {
                **intent,
                "intent": "patent_original",
                "focus": "selected_patent_deep_dive",
                "answer_format": intent.get("answer_format") if intent.get("answer_format") != "text" else "bullets",
                "source_plan": ["original", "report", "reviewed_vectorstore"],
                "reason": f"{intent.get('reason', '')} / selected patent deep dive uses original + report",
            }
        else:
            source_types = _source_types_from_intent(intent, fallback_requested=set(CORE_SEARCH_SOURCE_TYPES))
        state = {**state, "intent": intent}

        prepared = prepare_answer_generation(
            question,
            retrieval_query=state.get("retrieval_query") or question,
            patent_id=resolved_patent_id,
            source_types=source_types,
            top_k=top_k,
            allow_web=not _has_wiki_context(state),
            intent_override=intent,
        )

        yield sse_event("metadata", {"query": question, "patent_id": resolved_patent_id, "stream": True})
        if prepared.get("mode") == "direct_answer":
            result = dict(prepared.get("result") or {})
            answer = str(result.get("answer") or "")
            yield sse_event("source_cards", {"source_cards": public_source_cards(list(result.get("source_cards") or []))})
            if answer:
                yield sse_event("delta", {"text": answer})
            yield sse_event("done", {**result, "stream": True})
            return

        preview = finalize_prepared_answer(prepared, {"ok": True, "text": "", "model": ANSWER_MODEL, "provider": "openai"})
        preview = _append_context_cards(preview, state)
        yield sse_event("source_cards", {"source_cards": public_source_cards(list(preview.get("source_cards") or []))})

        for delta, answer in _stream_answer(prepared):
            yield sse_event("delta", {"text": delta})

        final = finalize_prepared_answer(
            prepared,
            {"ok": bool(answer), "text": answer, "error": None if answer else "empty response", "model": ANSWER_MODEL, "provider": "openai"},
        )
        final = _append_context_cards(final, state)
        state = finish_answer({**state, "result": final})
        final = dict(state.get("result") or final)
        metrics = dict(final.get("metrics") or {})
        metrics["stream"] = True
        metrics["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        metrics["answer_char_count"] = len(str(final.get("answer") or ""))
        final["metrics"] = metrics
        final["source_cards"] = public_source_cards(list(final.get("source_cards") or []))
        yield sse_event("done", {**final, "stream": True})
    except Exception as exc:
        yield sse_event(
            "error",
            {
                "code": "AI_STREAM_ERROR",
                "message": str(exc),
                "query": question,
                "patent_id": patent_id,
                "partial_answer": answer,
            },
        )


def _prepare_pre_eval_prompt(state: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    query = str(state.get("query") or "")
    pre_eval_hits = list(state.get("pre_eval_hits") or [])
    intent = state.get("intent") or {}
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=3)
    web_context = dict(state.get("web_context") or {})
    web_results = list(web_context.get("results") or [])

    context_parts: list[str] = []
    for hit in filter_usable_hits(pre_eval_hits, limit=6):
        meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        section = meta.get("section_title") or "사전평가 보고서"
        context_parts.append(f"[{section}]\n{compact_text(hit.get('page_content'), 600)}")
    for hit in wiki_hits:
        context_parts.append(f"[Wiki 배경]\n{compact_text(hit.get('page_content'), 400)}")
    for result in web_results[:2]:
        if result.get("snippet"):
            context_parts.append(f"[웹 참고]\n{compact_text(result.get('snippet'), 300)}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "사전평가 결과 데이터가 없습니다."
    intent_info = ""
    if intent.get("answer_format") == "table":
        intent_info = "\n답변을 표 형식으로 정리하세요."
    elif intent.get("needs_diagram"):
        intent_info = "\n필요한 경우 mermaid 다이어그램을 포함하세요."
    prompt = (
        f"{PRE_EVAL_SYSTEM_PROMPT}{intent_info}\n\n"
        f"## 사전평가 보고서 근거\n\n{context_text}\n\n"
        f"## 질문\n\n{query}"
    )

    source_cards = cards_from_hits(pre_eval_hits[:5], query=query)
    if wiki_hits:
        source_cards += cards_from_hits(wiki_hits, query=query)
    if web_results:
        source_cards += cards_from_web(web_results[:2], start_index=len(source_cards) + 1, query=query)
    metrics = {
        "pre_eval_hit_count": len(pre_eval_hits),
        "wiki_hit_count": len(wiki_hits),
        "web_result_count": len(web_results),
        "intent_agent": intent,
    }
    return prompt, source_cards, metrics


def stream_pre_eval_chat_events(
    *,
    case_id: str,
    question: str,
    user_id: str | None,
    chat_history: list[dict[str, Any]] | None,
    top_k: int = 8,
) -> Iterator[str]:
    started = time.monotonic()
    answer = ""
    try:
        state = _base_state(question, selected_id=case_id, user_id=user_id, chat_history=chat_history, top_k=top_k)
        state = resolve_history_context(state)
        state = route_question(state)
        state = retrieve_pre_eval_context(state)
        state = retrieve_wiki_context(state)
        state = retrieve_web_context(state)
        prompt, source_cards, metrics = _prepare_pre_eval_prompt(state)

        yield sse_event("metadata", {"query": question, "patent_id": case_id, "case_id": case_id, "stream": True})
        yield sse_event("source_cards", {"source_cards": public_source_cards(source_cards)})

        prepared = {"prompt": prompt}
        for delta, answer in _stream_answer(prepared):
            yield sse_event("delta", {"text": delta})

        metrics.update(
            {
                "stream": True,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "answer_char_count": len(answer),
                "agent_trace": state.get("trace", []),
                "patent_id": case_id,
                "answer_quality": answer_quality_metrics(
                    query=question,
                    answer=answer,
                    source_cards=source_cards,
                    retrieval_scores=[float(hit.get("score", 0)) for hit in list(state.get("pre_eval_hits") or [])],
                ),
            }
        )
        result = {
            "query": question,
            "patent_id": case_id,
            "case_id": case_id,
            "answer": answer,
            "source_cards": source_cards,
            "metrics": metrics,
        }
        state = finish_answer({**state, "result": result})
        final = dict(state.get("result") or result)
        final["source_cards"] = public_source_cards(list(final.get("source_cards") or []))
        yield sse_event("done", {**final, "stream": True})
    except Exception as exc:
        yield sse_event(
            "error",
            {
                "code": "AI_STREAM_ERROR",
                "message": str(exc),
                "query": question,
                "patent_id": case_id,
                "case_id": case_id,
                "partial_answer": answer,
            },
        )

