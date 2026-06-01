"""Policy helpers for routing chatbot questions."""

from __future__ import annotations

import json
import re
from typing import Any

from ..prompts import INTENT_PROMPT
from .config import INTENT_MODEL, INTENT_NUM_PREDICT
from .llm import call_ollama


def _rule_intent(query: str) -> dict[str, Any]:
    text = query.lower()
    if any(term in text for term in ["보고서", "평가", "점수", "유지", "포기", "판단"]):
        intent = "patent_report"
    elif any(term in text for term in ["청구항", "원문", "요약", "발명", "pdf"]):
        intent = "patent_original"
    elif "wiki" in text or "위키" in text:
        intent = "wiki"
    elif any(term in text for term in ["비교", "차이", "유사"]):
        intent = "comparison"
    else:
        intent = "general"
    needs_web = any(term in text for term in ["시장", "뉴스", "최근", "웹", "사업화", "경쟁", "제품"])
    return {"intent": intent, "needs_web": needs_web, "focus": intent, "method": "rule"}


def classify_intent(query: str) -> dict[str, Any]:
    fallback = _rule_intent(query)
    llm = call_ollama(
        INTENT_PROMPT.format(query=query),
        model=INTENT_MODEL,
        num_predict=INTENT_NUM_PREDICT,
    )
    if not llm.get("ok"):
        fallback["llm_error"] = llm.get("error")
        return fallback

    text = str(llm.get("text") or "")
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        fallback["llm_raw"] = text[:500]
        return fallback
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        fallback["llm_raw"] = text[:500]
        return fallback
    return {
        "intent": parsed.get("intent") or fallback["intent"],
        "needs_web": bool(parsed.get("needs_web", fallback["needs_web"])),
        "focus": parsed.get("focus") or fallback["focus"],
        "method": "llm",
    }
