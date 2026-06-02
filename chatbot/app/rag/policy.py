"""Policy helpers for routing chatbot questions."""

from __future__ import annotations

import json
import re
from typing import Any

from ..prompts import INTENT_PROMPT
from .config import INTENT_LLM_TIMEOUT, INTENT_MODEL, INTENT_NUM_PREDICT
from .llm import call_ollama


ALLOWED_INTENTS = {"patent_original", "patent_report", "wiki", "comparison", "general"}
ALLOWED_SOURCES = {"original", "report", "wiki", "reviewed_vectorstore", "web", "business", "global_patents"}
ALLOWED_FORMATS = {"text", "bullets", "table", "diagram", "table_and_diagram"}
WEB_TERMS = ("시장", "동향", "뉴스", "최근", "현재", "웹", "사업화", "경쟁", "제품", "표준", "외부", "최신", "규모", "성장률")


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
    needs_web = any(term in text for term in WEB_TERMS)
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


def _as_bool(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "필요", "예"}
    return fallback


def _as_source_plan(value: Any, fallback: list[str], *, needs_web: bool) -> list[str]:
    raw = value if isinstance(value, list) else fallback
    plan = []
    for item in raw:
        name = str(item or "").strip()
        if name in ALLOWED_SOURCES and name not in plan:
            plan.append(name)
    if not plan:
        plan = list(fallback)
    if "reviewed_vectorstore" not in plan:
        plan.insert(0, "reviewed_vectorstore")
    if needs_web and "web" not in plan:
        plan.append("web")
    if needs_web and "wiki" not in plan:
        insert_at = 1 if plan and plan[0] == "reviewed_vectorstore" else 0
        plan.insert(insert_at, "wiki")
    return plan


def _coerce_intent(query: str, parsed: dict[str, Any], fallback: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
    intent = str(parsed.get("intent") or fallback["intent"]).strip()
    if intent not in ALLOWED_INTENTS:
        intent = fallback["intent"]
    explicit_web = any(term in query.lower() for term in WEB_TERMS)
    needs_web = _as_bool(parsed.get("needs_web"), bool(fallback["needs_web"]))
    if needs_web and not explicit_web and not fallback["needs_web"]:
        needs_web = False
    needs_diagram = _as_bool(parsed.get("needs_diagram"), bool(fallback["needs_diagram"]))
    needs_table = _as_bool(parsed.get("needs_table"), bool(fallback["needs_table"]))
    answer_format = str(parsed.get("answer_format") or fallback["answer_format"]).strip()
    if answer_format not in ALLOWED_FORMATS:
        answer_format = fallback["answer_format"]
    if needs_diagram and needs_table:
        answer_format = "table_and_diagram"
    elif needs_diagram and answer_format == "text":
        answer_format = "diagram"
    elif needs_table and answer_format in {"text", "bullets"}:
        answer_format = "table"
    source_plan = _as_source_plan(parsed.get("source_plan"), list(fallback["source_plan"]), needs_web=needs_web)
    if not needs_web and not explicit_web:
        source_plan = [item for item in source_plan if item != "web"]
    result = {
        "intent": intent,
        "needs_web": needs_web,
        "focus": parsed.get("focus") or fallback["focus"],
        "source_plan": source_plan,
        "answer_format": answer_format,
        "needs_diagram": needs_diagram,
        "needs_table": needs_table,
        "use_history": _as_bool(parsed.get("use_history"), bool(fallback["use_history"])),
        "confidence": parsed.get("confidence"),
        "reason": parsed.get("reason"),
        "method": "llm",
        "llm_model": llm.get("model"),
    }
    return result


def classify_intent(query: str) -> dict[str, Any]:
    fallback = _rule_intent(query)
    llm = call_ollama(
        INTENT_PROMPT.format(query=query),
        model=INTENT_MODEL,
        num_predict=INTENT_NUM_PREDICT,
        timeout=INTENT_LLM_TIMEOUT,
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
    if not isinstance(parsed, dict):
        fallback["llm_raw"] = text[:500]
        return fallback
    return _coerce_intent(query, parsed, fallback, llm)
