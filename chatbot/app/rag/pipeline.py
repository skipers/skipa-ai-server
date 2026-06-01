"""Patent chatbot RAG pipeline with intent, retrieval, web evidence, and LLM generation."""

from __future__ import annotations

from typing import Any

from ..prompts import ANSWER_PROMPT
from .answer_utils import build_metrics, fallback_answer
from .config import ANSWER_MODEL, ANSWER_NUM_PREDICT
from .llm import call_ollama
from .policy import classify_intent
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


def answer_question(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    intent = classify_intent(query)
    local_result = retrieve_local(query, patent_id=patent_id, source_types=source_types, top_k=top_k)
    local_hits = list(local_result.get("hits") or [])

    web_result = search_web(query) if intent.get("needs_web") else {"enabled": False, "provider": None, "results": [], "error": None}
    web_results = list(web_result.get("results") or [])

    prompt = ANSWER_PROMPT.format(
        query=query,
        intent=intent,
        local_context=format_hits_for_prompt(local_hits, limit=top_k),
        web_context=_format_web_for_prompt(web_results),
    )
    llm_result = call_ollama(prompt, model=ANSWER_MODEL, num_predict=ANSWER_NUM_PREDICT)
    answer = (
        llm_result["text"]
        if llm_result.get("ok")
        else fallback_answer(query, local_hits=local_hits, web_results=web_results, llm_error=llm_result.get("error"))
    )
    source_cards = [*cards_from_hits(local_hits), *cards_from_web(web_results, start_index=len(local_hits) + 1)]

    return {
        "query": query,
        "patent_id": patent_id,
        "answer": answer,
        "source_cards": source_cards,
        "metrics": build_metrics(intent=intent, local_result=local_result, web_result=web_result, llm_result=llm_result),
    }
