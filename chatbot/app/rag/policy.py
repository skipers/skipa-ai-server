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
        source_plan = ["report", "reviewed_vectorstore", "wiki"]
    elif any(term in text for term in ["청구항", "원문", "요약", "발명", "pdf"]):
        intent = "patent_original"
        source_plan = ["original", "reviewed_vectorstore", "wiki"]
    elif "wiki" in text or "위키" in text:
        intent = "wiki"
        source_plan = ["wiki", "reviewed_vectorstore"]
    elif any(term in text for term in ["비교", "차이", "유사"]):
        intent = "comparison"
        source_plan = ["global_patents", "report", "original", "wiki"]
    else:
        intent = "general"
        source_plan = ["reviewed_vectorstore", "original", "report", "wiki"]
    needs_web = any(term in text for term in ["시장", "뉴스", "최근", "웹", "사업화", "경쟁", "제품"])
    if needs_web:
        source_plan.append("web")
    needs_diagram = any(term in text for term in ["다이어그램", "흐름", "구조", "프로세스", "그림"])
    needs_table = any(term in text for term in ["표", "비교", "점수", "유지", "매각", "제각", "판단"])
    if needs_diagram and needs_table:
        answer_format = "table_and_diagram"
    elif needs_diagram:
        answer_format = "diagram"
    elif needs_table:
        answer_format = "table"
    elif any(term in text for term in ["정리", "목록", "핵심"]):
        answer_format = "bullets"
    else:
        answer_format = "text"
    use_history = any(term in text for term in ["이거", "이 특허", "그거", "앞에서", "방금", "이전", "계속"])
    return {
        "intent": intent,
        "needs_web": needs_web,
        "focus": intent,
        "source_plan": source_plan,
        "answer_format": answer_format,
        "needs_diagram": needs_diagram,
        "needs_table": needs_table,
        "use_history": use_history,
        "method": "rule",
    }


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
        "source_plan": parsed.get("source_plan") or fallback["source_plan"],
        "answer_format": parsed.get("answer_format") or fallback["answer_format"],
        "needs_diagram": bool(parsed.get("needs_diagram", fallback["needs_diagram"])),
        "needs_table": bool(parsed.get("needs_table", fallback["needs_table"])),
        "use_history": bool(parsed.get("use_history", fallback["use_history"])),
        "method": "llm",
    }
