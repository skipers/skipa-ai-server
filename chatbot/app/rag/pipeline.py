"""Patent chatbot RAG pipeline with intent, retrieval, web evidence, and LLM generation."""

from __future__ import annotations

from typing import Any

from ..prompts import ANSWER_PROMPT
from .answer_utils import build_metrics, fallback_answer
from .config import ANSWER_LLM_TIMEOUT, ANSWER_MODEL, ANSWER_NUM_PREDICT
from .llm import call_ollama
from .policy import classify_intent
from .quality import filter_usable_hits
from .retrieval import retrieve_local
from .sources import cards_from_hits, cards_from_web
from .text import format_hits_for_prompt
from .web_answers import search_web


def _format_web_for_prompt(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No web evidence."
    lines = []
    for index, item in enumerate(results[:4], 1):
        lines.append(f"[W{index}] {item.get('title')}\n{item.get('snippet')}\n{item.get('url') or ''}")
    return "\n\n".join(lines)


def _source_type(card: dict[str, Any]) -> str:
    metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
    return str(card.get("source_type") or metadata.get("source_type") or "").upper()


def _hybrid_result_allowed(
    result: dict[str, Any],
    *,
    source_types: set[str] | None,
    allow_web: bool,
    intent: dict[str, Any],
) -> tuple[bool, str | None]:
    if not source_types:
        return True, None
    allowed = {item.upper() for item in source_types}
    if allow_web and intent.get("needs_web"):
        allowed.add("WEB")
    cards = [card for card in result.get("source_cards") or [] if isinstance(card, dict)]
    if not cards:
        return False, "no_source_cards"
    blocked = sorted({_source_type(card) or "UNKNOWN" for card in cards if (_source_type(card) or "UNKNOWN") not in allowed})
    if blocked:
        return False, f"blocked_source_types={','.join(blocked)}"
    return True, None


def answer_question(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
    allow_web: bool = True,
    intent_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hybrid_retrieval_error: str | None = None
    hybrid_retrieval_rejected: str | None = None
    intent = intent_override or classify_intent(query)
    if allow_web or source_types:
        from .legacy_adapter import try_answer_with_legacy

        legacy_result = try_answer_with_legacy(query, patent_id=patent_id, top_k=top_k)
        if legacy_result and not legacy_result.get("metrics", {}).get("fallback_required"):
            allowed, rejected_reason = _hybrid_result_allowed(
                legacy_result,
                source_types=source_types,
                allow_web=allow_web,
                intent=intent,
            )
            if allowed:
                legacy_result.setdefault("metrics", {})["workflow"] = "unified_patent_chat"
                return legacy_result
            hybrid_retrieval_rejected = rejected_reason
        if legacy_result:
            hybrid_retrieval_error = legacy_result.get("metrics", {}).get("hybrid_retrieval_error")

    local_result = retrieve_local(query, patent_id=patent_id, source_types=source_types, top_k=top_k)
    raw_local_hits = list(local_result.get("hits") or [])
    local_hits = filter_usable_hits(raw_local_hits, limit=top_k)
    local_result = {**local_result, "hits": local_hits, "raw_hit_count": len(raw_local_hits), "hit_count": len(local_hits)}

    needs_web = allow_web and bool(intent.get("needs_web") or len(local_hits) < 2)
    web_result = search_web(query) if needs_web else {"enabled": False, "provider": None, "results": [], "error": None}
    if not allow_web:
        web_result["skipped"] = True
        web_result["skip_reason"] = "disabled_by_agent_policy"
    elif len(local_hits) < 2 and not intent.get("needs_web"):
        web_result["fallback_reason"] = "local_evidence_insufficient"
    web_results = list(web_result.get("results") or [])

    prompt = ANSWER_PROMPT.format(
        query=query,
        intent=intent,
        local_context=format_hits_for_prompt(local_hits, limit=top_k),
        web_context=_format_web_for_prompt(web_results),
    )
    llm_result = call_ollama(prompt, model=ANSWER_MODEL, num_predict=ANSWER_NUM_PREDICT, timeout=ANSWER_LLM_TIMEOUT)
    answer = (
        llm_result["text"]
        if llm_result.get("ok")
        else fallback_answer(query, local_hits=local_hits, web_results=web_results, llm_error=llm_result.get("error"))
    )
    source_cards = [
        *cards_from_hits(local_hits, query=query),
        *cards_from_web(web_results, start_index=len(local_hits) + 1, query=query),
    ]

    metrics = build_metrics(intent=intent, local_result=local_result, web_result=web_result, llm_result=llm_result)
    metrics["engine"] = "langgraph_lightweight_fallback"
    if hybrid_retrieval_error:
        metrics["hybrid_retrieval_error"] = hybrid_retrieval_error
    if hybrid_retrieval_rejected:
        metrics["hybrid_retrieval_rejected_reason"] = hybrid_retrieval_rejected

    return {
        "query": query,
        "patent_id": patent_id,
        "answer": answer,
        "source_cards": source_cards,
        "metrics": metrics,
    }
