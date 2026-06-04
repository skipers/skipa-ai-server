"""Policy helpers for routing chatbot questions."""

from __future__ import annotations

import json
import re
from typing import Any

from ..prompts import INTENT_PROMPT
from .config import (
    ENABLE_OLLAMA_INTENT_FALLBACK,
    INTENT_LLM_TIMEOUT,
    INTENT_MODEL,
    INTENT_NUM_PREDICT,
    INTENT_PROVIDER,
    OPENAI_INTENT_MODEL,
)
from .llm import call_ollama, call_openai_json


ALLOWED_INTENTS = {"patent_original", "patent_report", "wiki", "comparison", "general"}
ALLOWED_SOURCES = {"original", "report", "wiki", "reviewed_vectorstore", "web", "global_patents"}
ALLOWED_FORMATS = {"text", "bullets", "table", "diagram", "table_and_diagram"}
ALLOWED_SCOPES = {"internal", "mixed", "external", "clarify"}
WEB_TERMS = ("시장", "동향", "뉴스", "최근", "현재", "웹", "사업화", "경쟁", "제품", "표준", "외부", "최신", "규모", "성장률")
INTERNAL_SEARCH_TERMS = ("db", "디비", "데이터", "내부", "보유", "폴더", "목록", "찾아", "검색", "찾아줘", "알려줘")
PATENT_DISCOVERY_TERMS = ("특허", "원문", "보고서", "평가", "청구항")
AMBIGUOUS_SHORT_TERMS = ("이거", "그거", "저거", "이 특허", "앞에서", "방금", "이전", "계속")


INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {"type": "string", "enum": sorted(ALLOWED_INTENTS)},
        "needs_web": {"type": "boolean"},
        "focus": {"type": "string"},
        "source_plan": {"type": "array", "items": {"type": "string", "enum": sorted(ALLOWED_SOURCES)}},
        "answer_format": {"type": "string", "enum": sorted(ALLOWED_FORMATS)},
        "needs_diagram": {"type": "boolean"},
        "needs_table": {"type": "boolean"},
        "use_history": {"type": "boolean"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "search_scope": {"type": "string", "enum": sorted(ALLOWED_SCOPES)},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": "string"},
    },
    "required": [
        "intent",
        "needs_web",
        "focus",
        "source_plan",
        "answer_format",
        "needs_diagram",
        "needs_table",
        "use_history",
        "confidence",
        "reason",
        "search_scope",
        "needs_clarification",
        "clarification_question",
    ],
}


def _wants_internal_db_search(text: str) -> bool:
    return (
        any(term in text for term in INTERNAL_SEARCH_TERMS)
        and any(term in text for term in PATENT_DISCOVERY_TERMS)
        and not any(term in text for term in ("웹", "뉴스", "최근", "최신", "시장", "동향", "외부", "경쟁사", "제품"))
    )


def _is_too_ambiguous(text: str) -> bool:
    compact = text.strip()
    return len(compact) <= 8 and any(term in compact for term in AMBIGUOUS_SHORT_TERMS)


def _rule_intent(query: str) -> dict[str, Any]:
    text = query.lower()
    needs_clarification = _is_too_ambiguous(text)
    if _wants_internal_db_search(text):
        intent = "general"
        source_plan = ["global_patents", "reviewed_vectorstore", "original", "report"]
    elif any(term in text for term in ["보고서", "평가", "점수", "유지", "포기", "판단"]):
        intent = "patent_report"
        source_plan = ["report", "reviewed_vectorstore"]
    elif any(term in text for term in ["청구항", "원문", "요약", "발명", "pdf"]):
        intent = "patent_original"
        source_plan = ["original", "reviewed_vectorstore"]
    elif "wiki" in text or "위키" in text:
        intent = "wiki"
        source_plan = ["wiki", "reviewed_vectorstore"]
    elif any(term in text for term in ["비교", "차이", "유사"]):
        intent = "comparison"
        source_plan = ["global_patents", "report", "original"]
    else:
        intent = "general"
        source_plan = ["reviewed_vectorstore", "original", "report"]
    needs_web = any(term in text for term in WEB_TERMS) and not _wants_internal_db_search(text)
    if needs_web:
        if "wiki" not in source_plan:
            source_plan.append("wiki")
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
        "confidence": 0.7,
        "reason": "룰 기반 키워드 라우팅",
        "method": "rule",
        "search_scope": "clarify" if needs_clarification else "mixed" if needs_web else "internal",
        "needs_clarification": needs_clarification,
        "clarification_question": (
            "어떤 특허나 어떤 범위를 기준으로 찾을까요? 예: 전체 DB에서 물류 특허 검색, 현재 선택 특허의 리스크 확인"
            if needs_clarification
            else ""
        ),
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


def _repair_intent(query: str, result: dict[str, Any]) -> dict[str, Any]:
    text = query.lower()
    repaired = dict(result)
    if _is_too_ambiguous(text):
        repaired.update(
            {
                "needs_web": False,
                "search_scope": "clarify",
                "needs_clarification": True,
                "clarification_question": repaired.get("clarification_question")
                or "어떤 특허나 어떤 데이터 범위를 기준으로 답할까요?",
                "source_plan": [item for item in repaired.get("source_plan", []) if item != "web"] or ["reviewed_vectorstore"],
                "reason": f"{repaired.get('reason') or ''} / 질문 대상이 불명확해 재질문 필요",
            }
        )
    if _wants_internal_db_search(text):
        repaired.update(
            {
                "intent": "general" if repaired.get("intent") not in {"comparison", "patent_report"} else repaired.get("intent"),
                "needs_web": False,
                "source_plan": ["global_patents", "reviewed_vectorstore", "original", "report"],
                "search_scope": "internal",
                "needs_clarification": False,
                "clarification_question": "",
                "reason": f"{repaired.get('reason') or ''} / 내부 DB 검색 요청으로 웹 차단",
            }
        )
    if repaired.get("needs_clarification"):
        repaired["needs_web"] = False
        repaired["search_scope"] = "clarify"
        repaired["source_plan"] = [item for item in repaired.get("source_plan", []) if item != "web"] or ["reviewed_vectorstore"]
        if not repaired.get("clarification_question"):
            repaired["clarification_question"] = "어떤 특허나 어떤 데이터 범위를 기준으로 답할까요?"
    if repaired.get("search_scope") == "internal":
        repaired["needs_web"] = False
        repaired["source_plan"] = [item for item in repaired.get("source_plan", []) if item != "web"] or ["reviewed_vectorstore", "original", "report"]
    if repaired.get("needs_web"):
        plan = list(repaired.get("source_plan") or [])
        if "wiki" not in plan:
            web_index = plan.index("web") if "web" in plan else len(plan)
            plan.insert(web_index, "wiki")
        if "web" not in plan:
            plan.append("web")
        repaired["source_plan"] = plan
    return repaired


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
    search_scope = str(parsed.get("search_scope") or fallback.get("search_scope") or ("mixed" if needs_web else "internal")).strip()
    if search_scope not in ALLOWED_SCOPES:
        search_scope = "mixed" if needs_web else "internal"
    needs_clarification = _as_bool(parsed.get("needs_clarification"), bool(fallback.get("needs_clarification", False)))
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
        "llm_provider": llm.get("provider") or "ollama",
        "search_scope": search_scope,
        "needs_clarification": needs_clarification,
        "clarification_question": str(parsed.get("clarification_question") or fallback.get("clarification_question") or ""),
    }
    return _repair_intent(query, result)


def classify_intent(query: str) -> dict[str, Any]:
    fallback = _rule_intent(query)
    system_prompt = INTENT_PROMPT.split("사용자 질문:", 1)[0].strip()
    user_prompt = f"사용자 질문:\n{query}"
    if INTENT_PROVIDER == "openai":
        llm = call_openai_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=INTENT_SCHEMA,
            model=INTENT_MODEL or OPENAI_INTENT_MODEL,
            timeout=INTENT_LLM_TIMEOUT,
        )
    elif INTENT_PROVIDER in {"ollama", "local", "ollama_chat"}:
        llm = call_ollama(
            INTENT_PROMPT.format(query=query),
            model=INTENT_MODEL,
            num_predict=INTENT_NUM_PREDICT,
            timeout=INTENT_LLM_TIMEOUT,
        )
    else:
        llm = {"ok": False, "text": "", "error": f"unsupported INTENT_PROVIDER: {INTENT_PROVIDER}"}
    if not llm.get("ok") and ENABLE_OLLAMA_INTENT_FALLBACK and INTENT_PROVIDER != "ollama":
        llm = call_ollama(
            INTENT_PROMPT.format(query=query),
            model=INTENT_MODEL,
            num_predict=INTENT_NUM_PREDICT,
            timeout=INTENT_LLM_TIMEOUT,
        )
    if not llm.get("ok"):
        fallback["llm_error"] = llm.get("error")
        fallback["method"] = "rule_fallback"
        fallback["llm_provider"] = INTENT_PROVIDER
        return _repair_intent(query, fallback)

    if isinstance(llm.get("json"), dict):
        return _coerce_intent(query, dict(llm["json"]), fallback, llm)
    text = str(llm.get("text") or "")
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        fallback["llm_raw"] = text[:500]
        return _repair_intent(query, fallback)
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        fallback["llm_raw"] = text[:500]
        return _repair_intent(query, fallback)
    if not isinstance(parsed, dict):
        fallback["llm_raw"] = text[:500]
        return _repair_intent(query, fallback)
    return _coerce_intent(query, parsed, fallback, llm)
