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
from .llm import call_ollama, call_openai_json, call_opensource_json


ALLOWED_INTENTS = {"patent_original", "patent_report", "wiki", "comparison", "general"}
ALLOWED_SOURCES = {"original", "report", "wiki", "reviewed_vectorstore", "web", "global_patents"}
ALLOWED_FORMATS = {"text", "bullets", "table", "diagram", "table_and_diagram", "chart", "visual_summary"}
ALLOWED_SCOPES = {"internal", "mixed", "external", "clarify"}
WEB_TERMS = ("시장", "동향", "뉴스", "최근", "현재", "웹", "사업화", "경쟁", "제품", "표준", "외부", "최신", "규모", "성장률")
# 내부 DB 검색 신호 - "찾아줘", "검색해줘" 등 + 특허 관련 명사
INTERNAL_SEARCH_TERMS = ("db", "디비", "데이터", "내부", "보유", "폴더", "목록", "찾아", "검색")
PATENT_DISCOVERY_TERMS = ("특허", "원문", "보고서", "평가", "청구항")
REPORT_TERM_TERMS = (
    "무효",
    "무효 가능성",
    "권리범위",
    "권리범위 적절성",
    "권리성",
    "신규성",
    "진보성",
    "기재불비",
    "침해",
    "권리의 구성요소",
    "권리의 추상성",
    "검증 등급",
    "신뢰도",
    "evidence coverage",
)
# 지시 대상이 불분명한 대명사/부사만 포함 (동사/형용사 제외)
AMBIGUOUS_SHORT_TERMS = ("이거", "그거", "저거", "이 특허", "앞에서", "방금", "이전")
# 연속 질문 패턴 - 이전 답변 기반으로 이어가야 하는 질문
CONTINUATION_TERMS = (
    "더 자세하게", "자세히 알려줘", "더 알려줘", "이어서", "계속해서", "좀 더", "추가로 알려줘",
    "위에서 말한", "위에 말한", "방금 말한", "그 특허에 대해서", "그거 자세히",
    "아니 그", "아니 위에", "아니 내가",  # 사용자 정정/재요청 패턴
)

# 복합 의도 감지 카테고리
_MULTI_INTENT_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("특허 원문 · 청구항", ("원문", "청구항", "청구범위", "pdf", "발명", "상세한 설명", "대표도")),
    ("AI 평가보고서 · 유지판단", ("보고서", "평가", "점수", "유지", "판단", "제각", "매각", "리스크", "검증 등급")),
    ("시장 동향 · 외부 정보", ("시장", "동향", "최근", "최신", "경쟁", "뉴스", "외부", "성장률", "사업화")),
    ("유사 특허 · 비교", ("비교", "차이", "유사", "다른 특허", "선행")),
]


def _detect_multi_intent(text: str) -> list[str]:
    """두 개 이상의 의도 카테고리가 감지되면 카테고리 레이블 목록을 반환."""
    norm = _normalize_compound(text.lower())
    return [label for label, terms in _MULTI_INTENT_CATEGORIES if any(t in norm for t in terms)]


def _build_multi_intent_options(categories: list[str], *, query: str = "") -> str:
    lines = ["질문이 여러 영역에 걸쳐 있습니다. 어떤 내용을 먼저 드릴까요?", ""]
    for i, cat in enumerate(categories, 1):
        lines.append(f"{i}. {cat}")
    lines.append(f"{len(categories) + 1}. 위 항목 모두 순서대로")
    lines.append("")
    lines.append("번호를 입력하거나, 더 구체적인 질문을 해주세요.")
    return "\n".join(lines)


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


def _normalize_compound(text: str) -> str:
    """'물류특허'→'물류 특허' 처럼 한국어 복합명사 앞에 공백 삽입."""
    for noun in ("특허", "보고서", "원문", "청구항", "평가"):
        text = re.sub(rf"([가-힣a-zA-Z0-9])({noun})", rf"\1 \2", text)
    return text


def _wants_internal_db_search(text: str) -> bool:
    norm = _normalize_compound(text)
    return (
        any(term in norm for term in INTERNAL_SEARCH_TERMS)
        and any(term in norm for term in PATENT_DISCOVERY_TERMS)
        and not any(term in norm for term in ("웹", "뉴스", "최근", "최신", "시장", "동향", "외부", "경쟁사", "제품"))
    )


def _is_continuation(text: str) -> bool:
    """'더 자세하게', '이어서' 등 이전 답변을 이어가는 질문."""
    return any(term in text for term in CONTINUATION_TERMS)


def _is_too_ambiguous(text: str) -> bool:
    # 연속 질문은 모호하지 않음 - 이전 컨텍스트 사용
    if _is_continuation(text):
        return False
    compact = text.strip()
    if len(compact) <= 8 and any(term in compact for term in AMBIGUOUS_SHORT_TERMS):
        return True
    has_ambiguous = any(term in compact for term in AMBIGUOUS_SHORT_TERMS)
    has_hint = any(term in compact for term in ("특허", "보고서", "평가", "원문", "청구항", "물류", "반도체", "nf3", "cmp"))
    if has_ambiguous and not has_hint:
        return True
    return False


def _rule_intent(query: str) -> dict[str, Any]:
    text = _normalize_compound(query.lower())
    needs_clarification = _is_too_ambiguous(text)
    is_continuation = _is_continuation(text)
    multi_intent_categories: list[str] = []

    # 연속 질문이 아니고 짧거나 중간 길이 쿼리에서 복합 의도 감지
    if not is_continuation and not needs_clarification:
        multi_intent_categories = _detect_multi_intent(text)
        # 2개 이상 카테고리 + 쿼리가 하나의 카테고리 단독으로 답하기 애매한 경우 → 보기 제시
        if len(multi_intent_categories) >= 2 and len(query.strip()) <= 40:
            needs_clarification = True

    report_term_question = any(term in text for term in REPORT_TERM_TERMS) and any(
        term in text for term in ["뭐야", "무슨 뜻", "뜻", "의미", "이란", "설명", "왜", "주의", "보고서"]
    )

    if _wants_internal_db_search(text):
        intent = "general"
        source_plan = ["global_patents", "reviewed_vectorstore", "original", "report"]
    elif report_term_question:
        intent = "patent_report"
        source_plan = ["report", "reviewed_vectorstore", "original"]
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

    # 연속 질문: 이전 컨텍스트 사용, 명확화 불필요
    if is_continuation:
        needs_clarification = False

    # 일반 개념 정의 질문: "뭐야/이란" 패턴만, "알려줘" 같은 일반 동사 제외
    DEFINITION_QUESTION_TERMS = ("뭐야", "뭐예요", "뭐임", "뭔가요", "이란", "무엇인가", "무엇인지", "뭔지")
    PATENT_CONTEXT_TERMS = (
        "특허",
        "보고서",
        "평가",
        "원문",
        "청구항",
        "물류",
        "반도체",
        "nf3",
        "cmp",
        *REPORT_TERM_TERMS,
    )
    is_definition_q = any(t in text for t in DEFINITION_QUESTION_TERMS)
    has_patent_context = any(t in text for t in PATENT_CONTEXT_TERMS)
    is_general_knowledge = is_definition_q and not has_patent_context and not needs_clarification and not is_continuation

    needs_web = (
        (any(term in text for term in WEB_TERMS) and not _wants_internal_db_search(text))
        or (is_general_knowledge and not report_term_question)
    )
    if needs_web:
        if "wiki" not in source_plan:
            source_plan.append("wiki")
        source_plan.append("web")
    needs_diagram = any(term in text for term in ["다이어그램", "흐름", "구조", "프로세스", "그림", "시각화", "워크플로우"])
    needs_table = any(term in text for term in ["표", "비교", "점수", "유지", "매각", "제각", "판단", "정리해줘", "정리해", "리스크"])
    needs_chart = any(term in text for term in ["그래프", "차트", "도표", "추이", "비율", "분포", "성장률", "연도별"])
    wants_visual = any(term in text for term in ["보기 쉽게", "한눈에", "시각", "시각화", "도식", "도표"])
    if needs_chart and (needs_table or needs_diagram or wants_visual):
        answer_format = "visual_summary"
    elif needs_chart:
        answer_format = "chart"
    elif needs_diagram and needs_table:
        answer_format = "table_and_diagram"
    elif needs_diagram:
        answer_format = "diagram"
    elif needs_table:
        answer_format = "table"
    elif any(term in text for term in ["목록", "핵심", "청구항", "항목"]):
        answer_format = "bullets"
    elif wants_visual and intent in {"patent_report", "comparison"}:
        answer_format = "visual_summary"
    elif any(term in text for term in ["자세하게", "자세히", "상세하게", "설명해줘", "알려줘"]) and intent in ("patent_original", "patent_report"):
        # 특허 상세/설명 질문 → 구조화된 불릿
        answer_format = "bullets"
    elif any(term in text for term in ["정리", "요약", "리스트"]):
        answer_format = "bullets"
    else:
        answer_format = "text"
    use_history = is_continuation or any(term in text for term in [
        "이거", "이 특허", "그거", "앞에서", "방금", "이전", "계속",
        "위에서", "위에 말한", "그 특허", "아니 ",
    ])
    if needs_clarification and multi_intent_categories:
        clarification_question = _build_multi_intent_options(multi_intent_categories, query=query)
    elif needs_clarification:
        clarification_question = (
            "어떤 특허나 어떤 범위를 기준으로 답할까요?\n\n"
            "1. 특허 원문 / 청구항 내용\n"
            "2. AI 평가보고서 / 유지·매각·제각 판단\n"
            "3. 시장 동향 / 외부 정보 웹 검색\n"
            "4. 유사 특허 비교 분석\n\n"
            "번호를 입력하거나, 더 구체적인 질문을 해주세요."
        )
    else:
        clarification_question = ""

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
        "clarification_question": clarification_question,
        "multi_intent_categories": multi_intent_categories,
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
    report_term_question = any(term in text for term in REPORT_TERM_TERMS) and any(
        term in text for term in ["뭐야", "무슨 뜻", "뜻", "의미", "이란", "설명", "왜", "주의", "보고서"]
    )
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
    if report_term_question:
        repaired.update(
            {
                "intent": "patent_report",
                "needs_web": False,
                "source_plan": ["report", "reviewed_vectorstore", "original"],
                "search_scope": "internal",
                "needs_clarification": False,
                "clarification_question": "",
                "reason": f"{repaired.get('reason') or ''} / 보고서 용어 설명 요청으로 내부 보고서 근거 우선",
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
        "llm_provider": llm.get("provider") or INTENT_PROVIDER,
        "search_scope": search_scope,
        "needs_clarification": needs_clarification,
        "clarification_question": str(parsed.get("clarification_question") or fallback.get("clarification_question") or ""),
    }
    return _repair_intent(query, result)


def classify_intent(
    query: str,
    *,
    chat_history: list[dict[str, Any]] | None = None,
    selected_patent_id: str | None = None,
) -> dict[str, Any]:
    fallback = _rule_intent(query)
    system_prompt = INTENT_PROMPT.split("사용자 질문:", 1)[0].strip()

    # 연속 질문일 때 이전 Q&A를 컨텍스트로 주입
    context_prefix = ""
    if chat_history and _is_continuation(query.lower()):
        lines: list[str] = []
        for item in list(chat_history)[-2:]:
            if not isinstance(item, dict):
                continue
            prev_q = str(item.get("question") or item.get("query") or "").strip()
            prev_a = str(item.get("answer") or "").strip()[:200]
            if prev_q:
                lines.append(f"이전 질문: {prev_q}")
            if prev_a:
                lines.append(f"이전 답변 요약: {prev_a}")
        if lines:
            context_prefix = "[대화 이력]\n" + "\n".join(lines) + "\n\n"

    selected_context = ""
    if selected_patent_id:
        selected_context = f"[현재 재평가 특허]\npatent_id: {selected_patent_id}\n\n"

    user_prompt = f"{selected_context}{context_prefix}사용자 질문:\n{query}"
    if INTENT_PROVIDER == "openai":
        llm = call_openai_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=INTENT_SCHEMA,
            model=INTENT_MODEL or OPENAI_INTENT_MODEL,
            timeout=INTENT_LLM_TIMEOUT,
        )
    elif INTENT_PROVIDER == "opensource":
        llm = call_opensource_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=INTENT_MODEL,
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
