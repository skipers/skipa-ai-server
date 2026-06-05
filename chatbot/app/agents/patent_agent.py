"""Patent/report/wiki RAG agent."""

from __future__ import annotations

from datetime import datetime

from ..rag.config import ANSWER_LLM_TIMEOUT, ANSWER_MODEL, ANSWER_NUM_PREDICT, ANSWER_PROVIDER
from ..rag.evaluation import answer_quality_metrics
from ..rag.llm import call_openai_prompt
from ..rag.pipeline import answer_question
from ..rag.quality import compact_text, filter_usable_hits
from ..rag.sources import cards_from_hits, cards_from_web
from ..rag.web_answers import search_web
from ..vectorstore import CORE_SEARCH_SOURCE_TYPES
from .state import ChatAgentState


LOW_EVIDENCE_MARKERS = (
    "관련 근거를 찾지 못했습니다",
    "근거를 찾지 못했습니다",
    "찾을 수 없습니다",
    "내부 승인 데이터와 원문/보고서에서 직접 답할 만한 근거가 충분하지 않습니다",
)


def _is_low_evidence_answer(result: dict) -> bool:
    answer = str(result.get("answer") or "")
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    cards = result.get("source_cards") if isinstance(result.get("source_cards"), list) else []
    if any(marker in answer for marker in LOW_EVIDENCE_MARKERS):
        return True
    if metrics.get("search_pass") is False:
        return True
    if str(metrics.get("retrieval_quality_grade") or "").upper() in {"LOW", "BAD"}:
        return True
    return len(cards) == 0 and int(metrics.get("hit_count") or metrics.get("local_context_count") or 0) == 0


def _hit_title(hit: dict) -> str:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    return str(
        metadata.get("section_title")
        or metadata.get("file_name")
        or metadata.get("title")
        or metadata.get("source_type")
        or "근거"
    )


def _format_hit_section(title: str, hits: list[dict], *, limit: int = 3) -> str:
    usable = filter_usable_hits(hits, limit=limit)
    if not usable:
        return ""
    lines = ["", f"## {title}"]
    for index, hit in enumerate(usable, 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "근거"
        lines.append(f"{index}. **{source_type} / {_hit_title(hit)}**: {compact_text(hit.get('excerpt') or hit.get('page_content'), 280)}")
    return "\n".join(lines)


def _format_web_section(results: list[dict], *, limit: int = 3) -> str:
    if not results:
        return ""
    lines = ["", "## 웹 검색 보강"]
    for index, item in enumerate(results[:limit], 1):
        lines.append(f"{index}. **{item.get('title') or 'web result'}**: {compact_text(item.get('snippet'), 280)}")
    return "\n".join(lines)


def _web_snippets_for_prompt(results: list[dict], limit: int = 3) -> str:
    lines = []
    for i, r in enumerate(results[:limit], 1):
        title = r.get("title") or "웹 결과"
        snippet = compact_text(r.get("snippet") or "", 300)
        lines.append(f"[웹{i}] {title}: {snippet}")
    return "\n\n".join(lines)


def _merge_context_sections(result: dict, state: ChatAgentState, web_context: dict) -> dict:
    answer = str(result.get("answer") or "")
    intent = state.get("intent") or {}
    web_results = list(web_context.get("results") or [])
    needs_web = bool(intent.get("needs_web"))

    # 내부 근거 없고 외부 근거만 있는 경우 안내 문구 교체
    if web_results and any(marker in answer for marker in LOW_EVIDENCE_MARKERS):
        answer = "내부 원문/보고서 근거가 충분하지 않아 웹 근거를 중심으로 답변합니다."

    # needs_web 질문에서 웹 결과가 있으면 LLM으로 내부+외부 통합 답변 생성
    if needs_web and web_results and ANSWER_PROVIDER == "openai":
        try:
            combined_prompt = (
                f"질문: {state.get('query', '')}\n\n"
                f"내부 특허 DB 기반 답변:\n{answer}\n\n"
                f"외부 웹 검색 결과:\n{_web_snippets_for_prompt(web_results)}\n\n"
                "위 두 정보를 통합해 질문에 직접 답하세요.\n"
                "- 내부 DB 정보(특허 원문·보고서)와 웹 정보를 자연스럽게 합칩니다.\n"
                "- 1-4문장으로 간결하게 씁니다.\n"
                "- '확인 필요 사항', '근거', '해석' 섹션은 추가하지 않습니다."
            )
            llm = call_openai_prompt(
                combined_prompt,
                model=ANSWER_MODEL,
                max_output_tokens=min(ANSWER_NUM_PREDICT, 600),
                timeout=ANSWER_LLM_TIMEOUT,
                temperature=0.2,
            )
            if llm.get("ok") and llm.get("text"):
                answer = str(llm["text"]).strip()
        except Exception:
            pass  # 실패 시 기존 answer 유지

    result["answer"] = answer
    return result


def _has_wiki_context(state: ChatAgentState) -> bool:
    intent = state.get("intent") or {}
    if not intent.get("needs_web"):
        return False
    wiki_hits = list((state.get("wiki_context") or {}).get("hits") or [])
    return bool(filter_usable_hits(wiki_hits, limit=1))


def _allows_web_fallback(intent: dict) -> bool:
    if intent.get("needs_clarification"):
        return False
    if intent.get("search_scope") == "internal":
        return False
    return bool(intent.get("needs_web") or "web" in set(intent.get("source_plan") or []))


def answer_from_patent_context(state: ChatAgentState) -> ChatAgentState:
    patent_id = state.get("resolved_patent_id") or state.get("patent_id")
    wiki_available = _has_wiki_context(state)
    requested_source_types = set(state.get("source_types") or CORE_SEARCH_SOURCE_TYPES)
    source_types = requested_source_types & set(CORE_SEARCH_SOURCE_TYPES) or set(CORE_SEARCH_SOURCE_TYPES)
    result = answer_question(
        state.get("query", ""),
        patent_id=patent_id,
        source_types=source_types,
        top_k=int(state.get("top_k") or 5),
        allow_web=not wiki_available,
        intent_override=state.get("intent") or None,
    )
    result.setdefault("metrics", {})["hybrid_retrieval_scope_policy"] = "try_hybrid_then_guard_source_types"
    web_context = dict(state.get("web_context") or {})
    intent = state.get("intent") or {}
    allow_web_fallback = _allows_web_fallback(intent)
    if _is_low_evidence_answer(result) and not web_context.get("results") and not wiki_available and allow_web_fallback:
        web_context = search_web(state.get("query", ""))
        web_context["enabled"] = True
        web_context["fallback_reason"] = "answer_evidence_insufficient"
    elif allow_web_fallback and not web_context.get("enabled") and not wiki_available and not web_context.get("skipped"):
        web_context = search_web(state.get("query", ""))
        web_context["enabled"] = True

    result = _merge_context_sections(result, state, web_context)
    intent_needs_web = bool((state.get("intent") or {}).get("needs_web"))
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=3) if intent_needs_web else []
    existing_snippets = {
        str(card.get("snippet") or "")[:160]
        for card in result.get("source_cards") or []
        if isinstance(card, dict)
    }
    wiki_cards = [
        card
        for card in cards_from_hits(wiki_hits, query=state.get("query", ""))
        if str(card.get("snippet") or "")[:160] not in existing_snippets
    ]
    if wiki_cards:
        result["source_cards"] = list(result.get("source_cards") or []) + wiki_cards
    web_results = list(web_context.get("results") or [])
    if web_results and not any(card.get("source_type") == "WEB" for card in result.get("source_cards") or []):
        result["source_cards"] = list(result.get("source_cards") or []) + cards_from_web(
            web_results,
            start_index=len(result.get("source_cards") or []) + 1,
            query=state.get("query", ""),
        )

    metrics = dict(result.get("metrics") or {})
    source_cards = [card for card in result.get("source_cards") or [] if isinstance(card, dict)]
    retrieval_scores = [
        (card.get("metadata") or {}).get("retrieval_score")
        for card in source_cards
        if isinstance(card.get("metadata"), dict)
    ]
    metrics.update(
        {
            "resolved_patent_id": patent_id,
            "intent_agent": state.get("intent") or {},
            "wiki_context_count": (state.get("wiki_context") or {}).get("hit_count", 0),
            "wiki_context_mode": (state.get("wiki_context") or {}).get("mode"),
            "wiki_gate_enabled": intent_needs_web,
            "wiki_gate_passed": wiki_available,
            "web_agent_enabled": bool(web_context.get("enabled")),
            "web_context_count": len(web_results),
            "web_provider": web_context.get("provider"),
            "web_fallback_reason": web_context.get("fallback_reason"),
            "web_skip_reason": web_context.get("skip_reason"),
            "answer_format_plan": (state.get("intent") or {}).get("answer_format"),
            "source_plan": (state.get("intent") or {}).get("source_plan"),
        }
    )
    metrics["answer_quality"] = answer_quality_metrics(
        query=state.get("query", ""),
        answer=str(result.get("answer") or ""),
        source_cards=source_cards,
        retrieval_scores=[score for score in retrieval_scores if isinstance(score, (int, float))],
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
