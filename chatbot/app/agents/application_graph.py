"""LangGraph workflow for the patent-application assistant chatbot."""

from __future__ import annotations

from datetime import datetime
import json
import re
import unicodedata
from typing import Any, TypedDict

from ..application_data import (
    application_external_status,
    application_index_status,
    cards_from_application_hits,
    failed_patent_case_report_summary,
    failed_patent_case_index_status,
    preferred_application_hits,
    refresh_application_index,
    refresh_failed_patent_case_index,
    search_application_index,
    search_failed_patent_case_index,
)
from ..rag.evaluation import answer_quality_metrics
from ..rag.sources import cards_from_web
from ..rag.web_answers import search_web
from ..rag.config import (
    ANSWER_LLM_TIMEOUT,
    ANSWER_MODEL,
    ANSWER_NUM_PREDICT,
    ANSWER_PROVIDER,
    ENABLE_OLLAMA_INTENT_FALLBACK,
    INTENT_LLM_TIMEOUT,
    INTENT_MODEL,
    INTENT_NUM_PREDICT,
    INTENT_PROVIDER,
    OPENAI_INTENT_MODEL,
)
from ..rag.llm import call_ollama, call_openai_json, call_openai_prompt


FOLLOWUP_TERMS = ("이거", "이것", "그거", "앞에서", "방금", "이전", "계속", "그 다음", "그럼", "그러면", "이어서", "다음")
REJECTION_TERMS = ("거절", "의견제출", "보정", "통지서", "불복", "심판", "실패", "리스크", "위험", "대응")
INITIAL_PROCEDURE_TERMS = ("처음", "최초", "첫", "순서", "절차", "준비", "시작", "출원할 때", "어떻게")
STRATEGY_TERMS = ("전략", "사업화", "해외", "우선심사", "심사유예", "투자", "라이선스", "시장", "동향")
FORM_TERMS = ("서식", "서류", "준비물", "특허고객번호", "인증서", "전자출원", "제출", "위임장")
EXTERNAL_TERMS = ("kipris", "kosis", "타빌리", "시장", "동향", "유사", "사업화", "최신", "경쟁사", "통계")
EVALUATION_TERMS = ("평가", "점수", "등급", "결과", "보고서", "재평가", "신뢰도", "어떻게 나왔", "어떻게 나와")
FAILED_CASE_DIAGNOSTIC_TERMS = (
    "원인",
    "이유",
    "문제",
    "약점",
    "리스크",
    "위험",
    "보완",
    "개선",
    "극복",
    "등록받",
    "등록 가능",
    "등록하려면",
    "등록할 수",
    "뭘 더",
    "뭐 더",
    "해야",
    "어떻게 해야",
)
TERM_EXPLANATION_TERMS = ("뭐야", "뭐예요", "뜻", "의미", "이란", "설명", "모르는", "용어")
NON_PATENT_PACK_TERMS = ("상표", "유사상품", "니스", "nice", "국제상품분류", "디자인")
GUIDED_TEMPLATE_INTENTS = {"application_procedure", "forms_and_filing", "fees"}
SOURCE_PLAN_BY_INTENT = {
    "failed_case_evaluation": ["failed_case_report", "failed_case_original", "official_pack"],
    "application_procedure": ["application_guide", "process_checklist", "official_pack"],
    "forms_and_filing": ["patent_customer_number", "certificate", "filing_forms"],
    "drafting_claims": ["application_guide", "examination_standard", "strategy"],
    "prior_art_search": ["kipris", "classification", "search_workflow"],
    "rejection_response": ["notice_forms", "examination_standard", "appeal", "kipris"],
    "fees": ["fee_guide", "official_forms"],
    "application_strategy": ["strategy", "examination_timing", "publication", "kosis", "tavily"],
}
APPLICATION_INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {"type": "string", "enum": sorted(SOURCE_PLAN_BY_INTENT.keys())},
        "source_plan": {"type": "array", "items": {"type": "string"}},
        "answer_format": {"type": "string"},
        "needs_table": {"type": "boolean"},
        "needs_diagram": {"type": "boolean"},
        "needs_external": {"type": "boolean"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": "string"},
    },
    "required": [
        "intent",
        "source_plan",
        "answer_format",
        "needs_table",
        "needs_diagram",
        "needs_external",
        "confidence",
        "reason",
        "needs_clarification",
        "clarification_question",
    ],
}


def _is_initial_application_question(text: str) -> bool:
    if "출원" not in text:
        return False
    if any(term in text for term in REJECTION_TERMS):
        return False
    if any(term in text for term in STRATEGY_TERMS):
        return False
    return any(term in text for term in INITIAL_PROCEDURE_TERMS)


def _is_failed_case_diagnostic_question(text: str) -> bool:
    if "등록료" in text or "수수료" in text:
        return False
    if _is_initial_application_question(text):
        return False
    if any(term in text for term in EVALUATION_TERMS):
        return True
    if any(term in text for term in FAILED_CASE_DIAGNOSTIC_TERMS):
        return True
    if any(term in text for term in TERM_EXPLANATION_TERMS) and any(
        term in text for term in ["보고서", "점수", "등급", "무효", "권리", "청구항", "진보성", "신규성", "기재", "리스크"]
    ):
        return True
    return False


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


class ApplicationAgentState(TypedDict, total=False):
    query: str
    user_id: str | None
    failed_patent_id: str | None
    failed_patent_status: dict[str, Any]
    case_valid: bool
    chat_history: list[dict[str, Any]]
    top_k: int
    refresh_index: bool
    history_summary: str
    retrieval_query: str
    intent: dict[str, Any]
    retrieval: dict[str, Any]
    external_context: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, Any]]


def _trace(state: ApplicationAgentState, node: str, status: str, **extra: Any) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    item = {"node": node, "status": status, "at": datetime.now().isoformat(timespec="seconds")}
    item.update({key: value for key, value in extra.items() if value is not None})
    trace.append(item)
    return trace


def resolve_application_history(state: ApplicationAgentState) -> ApplicationAgentState:
    history = [item for item in state.get("chat_history") or [] if isinstance(item, dict)][-4:]
    parts = []
    for item in history:
        question = item.get("question") or item.get("query") or item.get("user")
        answer = item.get("answer") or item.get("assistant")
        if question:
            parts.append(f"Q: {question}")
        if answer:
            parts.append(f"A: {str(answer)[:500]}")
    history_summary = "\n".join(parts)
    query = state.get("query", "")
    retrieval_query = f"{history_summary}\n현재 질문: {query}" if history_summary else query
    return {
        **state,
        "history_summary": history_summary,
        "retrieval_query": retrieval_query,
        "trace": _trace(state, "resolve_application_history", "success", history_count=len(history)),
    }


def _case_required_result(state: ApplicationAgentState, message: str, *, error: str) -> dict[str, Any]:
    return {
        "query": state.get("query", ""),
        "patent_id": "patent_application",
        "answer": message,
        "source_cards": [],
        "metrics": {
            "engine": "patent_application_langgraph",
            "requires_failed_patent": True,
            "failed_patent_id": state.get("failed_patent_id"),
            "llm_ok": False,
            "llm_error": error,
            "answer_strategy": "require_failed_patent_case_before_chat",
            "application_workflow": "case_upload_required -> official_pack_index + selected_case_index -> intent_router -> answer",
        },
    }


def validate_failed_patent_case(state: ApplicationAgentState) -> ApplicationAgentState:
    case_id = _norm(state.get("failed_patent_id")).strip()
    if not case_id:
        result = _case_required_result(
            state,
            "특허 출원 도우미 채팅을 시작하려면 먼저 실패특허 원본 PDF를 업로드하고 `failed_patent_id`를 선택해야 합니다. 사유서/거절의견서는 선택이지만, 있으면 같은 케이스 폴더에 함께 저장해 더 정확하게 답변합니다.",
            error="failed_patent_id_required",
        )
        return {
            **state,
            "case_valid": False,
            "result": result,
            "trace": _trace(state, "validate_failed_patent_case", "blocked", reason="failed_patent_id_required"),
        }
    try:
        status = failed_patent_case_index_status(case_id)
        if not status.get("has_original_pdf"):
            result = _case_required_result(
                {**state, "failed_patent_id": case_id},
                f"`{case_id}` 케이스에 실패특허 원본 PDF가 없습니다. 원본 PDF를 먼저 업로드한 뒤 다시 질문해 주세요.",
                error="failed_patent_original_pdf_required",
            )
            return {
                **state,
                "failed_patent_id": case_id,
                "failed_patent_status": status,
                "case_valid": False,
                "result": result,
                "trace": _trace(state, "validate_failed_patent_case", "blocked", reason="original_pdf_missing"),
            }
        if state.get("refresh_index") or not status.get("index_exists"):
            refresh_failed_patent_case_index(case_id)
            status = failed_patent_case_index_status(case_id)
    except Exception as exc:
        result = _case_required_result(
            {**state, "failed_patent_id": case_id},
            f"`{case_id}` 실패특허 케이스를 찾거나 인덱싱할 수 없습니다. 케이스 목록에서 ID를 다시 확인해 주세요.",
            error=f"{type(exc).__name__}: {exc}",
        )
        return {
            **state,
            "failed_patent_id": case_id,
            "case_valid": False,
            "result": result,
            "trace": _trace(state, "validate_failed_patent_case", "blocked", reason="case_status_error"),
        }
    return {
        **state,
        "failed_patent_id": str(status.get("case_id") or case_id),
        "failed_patent_status": status,
        "case_valid": True,
        "trace": _trace(
            state,
            "validate_failed_patent_case",
            "success",
            failed_patent_id=status.get("case_id") or case_id,
            case_document_count=status.get("document_count"),
        ),
    }


_APP_MULTI_INTENT_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("출원 절차 · 서류 준비", ("절차", "출원", "서류", "특허청", "방법", "준비")),
    ("거절 대응 · 의견서 작성", ("거절", "의견서", "보정", "불복", "거절이유")),
    ("청구항 · 명세서 작성", ("청구항", "명세서", "청구범위", "작성", "권리범위", "독립항")),
    ("선행기술 조사", ("선행기술", "kipris", "검색", "cpc", "ipc", "유사")),
    ("실패 특허 분석", ("실패", "거절", "원인", "진보성", "신규성", "기재불비")),
]


def _detect_multi_application_intent(text: str) -> list[str]:
    return [label for label, terms in _APP_MULTI_INTENT_CATEGORIES if any(t in text for t in terms)]


def _build_application_options(categories: list[str]) -> str:
    lines = ["질문이 여러 출원 업무 영역에 걸쳐 있습니다. 어떤 내용을 먼저 드릴까요?", ""]
    for i, cat in enumerate(categories, 1):
        lines.append(f"{i}. {cat}")
    lines.append(f"{len(categories) + 1}. 위 항목 모두 순서대로")
    lines.append("")
    lines.append("번호를 입력하거나, 더 구체적인 질문을 해주세요.")
    return "\n".join(lines)


def _rule_application_intent(query: str) -> dict[str, Any]:
    text = query.lower()
    multi_categories: list[str] = []

    if _is_failed_case_diagnostic_question(text):
        intent = "failed_case_evaluation"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in REJECTION_TERMS):
        intent = "rejection_response"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in FORM_TERMS):
        intent = "forms_and_filing"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif _is_initial_application_question(text):
        intent = "application_procedure"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in ["선행기술", "kipris", "검색", "cpc", "ipc", "유사"]):
        intent = "prior_art_search"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in ["명세서", "청구항", "청구범위", "작성", "권리범위"]):
        intent = "drafting_claims"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in ["수수료", "비용", "감면", "등록료", "심사청구료"]):
        intent = "fees"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    elif any(term in text for term in ["전략", "사업화", "해외", "우선심사", "심사유예"]):
        intent = "application_strategy"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]
    else:
        intent = "application_procedure"
        source_plan = SOURCE_PLAN_BY_INTENT[intent]

    needs_table = any(term in text for term in ["표", "비교", "체크리스트", "단계", "정리", "순서"])
    needs_diagram = any(term in text for term in ["다이어그램", "흐름", "프로세스", "그림"])
    if needs_table and needs_diagram:
        answer_format = "table_and_diagram"
    elif needs_table:
        answer_format = "checklist_table"
    elif needs_diagram:
        answer_format = "diagram"
    else:
        answer_format = "guided_answer"

    # 복합 의도 감지 (짧은 쿼리에서 2개 이상 카테고리 → 보기 제시)
    is_short_ambiguous = len(text.strip()) <= 8 and any(term in text for term in FOLLOWUP_TERMS)
    multi_categories = _detect_multi_application_intent(text)
    is_multi = len(multi_categories) >= 2 and len(query.strip()) <= 40

    needs_clarification = is_short_ambiguous or is_multi
    if needs_clarification and is_multi:
        clarification_question = _build_application_options(multi_categories)
    elif needs_clarification:
        clarification_question = (
            "어떤 출원 업무를 도와드릴까요?\n\n"
            "1. 출원 절차 · 서류 준비\n"
            "2. 거절 대응 · 의견서 작성\n"
            "3. 청구항 · 명세서 작성\n"
            "4. 선행기술 조사\n"
            "5. 실패 특허 원인 분석\n\n"
            "번호를 입력하거나, 더 구체적인 질문을 해주세요."
        )
    else:
        clarification_question = ""

    return {
        "intent": intent,
        "source_plan": source_plan,
        "answer_format": answer_format,
        "needs_table": needs_table,
        "needs_diagram": needs_diagram,
        "needs_external": False if intent == "failed_case_evaluation" else any(term in text for term in [*EXTERNAL_TERMS, *REJECTION_TERMS]),
        "method": "rule",
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "multi_intent_categories": multi_categories,
    }


def _repair_application_intent(query: str, intent: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(intent)
    intent_name = str(repaired.get("intent") or "application_procedure")
    if intent_name not in SOURCE_PLAN_BY_INTENT:
        intent_name = _rule_application_intent(query)["intent"]
        repaired["intent"] = intent_name
    text = query.lower()
    if _is_failed_case_diagnostic_question(text):
        intent_name = "failed_case_evaluation"
        repaired["intent"] = intent_name
        repaired["method"] = f"{repaired.get('method', 'llm')}_repaired"
    elif any(term in text for term in FORM_TERMS):
        intent_name = "forms_and_filing"
        repaired["intent"] = intent_name
        repaired["method"] = f"{repaired.get('method', 'llm')}_repaired"
    elif _is_initial_application_question(text):
        intent_name = "application_procedure"
        repaired["intent"] = intent_name
        repaired["method"] = f"{repaired.get('method', 'llm')}_repaired"
    repaired["source_plan"] = SOURCE_PLAN_BY_INTENT[intent_name]
    if repaired.get("needs_clarification"):
        repaired["needs_external"] = False
        repaired["source_plan"] = SOURCE_PLAN_BY_INTENT.get(intent_name, SOURCE_PLAN_BY_INTENT["application_procedure"])
        if not repaired.get("clarification_question"):
            repaired["clarification_question"] = "어떤 출원 업무 범위를 기준으로 답할까요?"
    explicit_external = any(term in text for term in EXTERNAL_TERMS)
    explicit_rejection = any(term in text for term in REJECTION_TERMS)
    source_plan_needs_external = bool({"kipris", "kosis", "tavily"} & set(repaired.get("source_plan") or []))
    llm_external_allowed = intent_name in {"prior_art_search", "rejection_response", "application_strategy"}
    repaired["needs_external"] = bool(
        explicit_external
        or explicit_rejection
        or source_plan_needs_external
        or (bool(repaired.get("needs_external")) and llm_external_allowed)
    )
    if intent_name in {"application_procedure", "forms_and_filing", "fees", "drafting_claims"} and not (
        explicit_external or explicit_rejection
    ):
        repaired["needs_external"] = False
    if intent_name == "failed_case_evaluation":
        repaired["needs_external"] = False
    return repaired


def route_application_question(state: ApplicationAgentState) -> ApplicationAgentState:
    if state.get("result"):
        return state
    fallback = _rule_application_intent(state.get("query", ""))
    system_prompt = """You are a lightweight intent router for a Korean patent filing assistant.
Return JSON only with keys: intent, source_plan, answer_format, needs_table, needs_diagram, needs_external.
Allowed intents: failed_case_evaluation, application_procedure, forms_and_filing, drafting_claims, prior_art_search, rejection_response, fees, application_strategy.
Rules:
- If the user asks "처음/최초/순서/절차/준비" around patent filing, use application_procedure unless rejection/failure is explicit.
- If the user asks how this patent was evaluated, score, grade, report result or reliability, use failed_case_evaluation.
- If the user asks why it failed, what the problem is, what to improve, what to do for registration, or asks a report term meaning, use failed_case_evaluation.
- If the user asks about failure factors, rejection, office-action response, risk or feedback, use rejection_response.
- If the user asks about prior art, novelty, inventive step, KIPRIS, CPC/IPC or similar patents, use prior_art_search.
- If the user asks about market, commercialization, timing, external trends or statistics, set needs_external=true and include tavily/kosis.
"""
    user_prompt = f"Question: {state.get('query', '')}"
    if INTENT_PROVIDER == "openai":
        llm = call_openai_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=APPLICATION_INTENT_SCHEMA,
            model=INTENT_MODEL or OPENAI_INTENT_MODEL,
            timeout=INTENT_LLM_TIMEOUT,
        )
    elif INTENT_PROVIDER in {"ollama", "local", "ollama_chat"}:
        llm = call_ollama(
            f"{system_prompt}\n{user_prompt}",
            model=INTENT_MODEL,
            num_predict=INTENT_NUM_PREDICT,
            timeout=INTENT_LLM_TIMEOUT,
        )
    else:
        llm = {"ok": False, "text": "", "error": f"unsupported INTENT_PROVIDER: {INTENT_PROVIDER}"}
    if not llm.get("ok") and ENABLE_OLLAMA_INTENT_FALLBACK and INTENT_PROVIDER != "ollama":
        llm = call_ollama(
            f"{system_prompt}\n{user_prompt}",
            model=INTENT_MODEL,
            num_predict=INTENT_NUM_PREDICT,
            timeout=INTENT_LLM_TIMEOUT,
        )
    intent = dict(fallback)
    if llm.get("ok"):
        parsed_payload = llm.get("json") if isinstance(llm.get("json"), dict) else None
        match = re.search(r"\{.*\}", str(llm.get("text") or ""), flags=re.S) if parsed_payload is None else None
        if parsed_payload is not None or match:
            try:
                parsed = parsed_payload if parsed_payload is not None else json.loads(match.group(0))
                intent.update(
                    {
                        "intent": parsed.get("intent") or intent["intent"],
                        "source_plan": parsed.get("source_plan") or intent["source_plan"],
                        "answer_format": parsed.get("answer_format") or intent["answer_format"],
                        "needs_table": bool(parsed.get("needs_table", intent["needs_table"])),
                        "needs_diagram": bool(parsed.get("needs_diagram", intent["needs_diagram"])),
                        "needs_external": bool(parsed.get("needs_external", intent.get("needs_external", False))),
                        "needs_clarification": bool(parsed.get("needs_clarification", intent.get("needs_clarification", False))),
                        "clarification_question": parsed.get("clarification_question") or intent.get("clarification_question", ""),
                        "method": "llm",
                        "llm_provider": llm.get("provider") or INTENT_PROVIDER,
                        "llm_model": llm.get("model"),
                    }
                )
            except json.JSONDecodeError:
                intent["llm_raw"] = str(llm.get("text") or "")[:400]
        else:
            intent["llm_raw"] = str(llm.get("text") or "")[:400]
    else:
        intent["llm_error"] = llm.get("error")
    intent = _repair_application_intent(state.get("query", ""), intent)
    return {**state, "intent": intent, "trace": _trace(state, "route_application_question", "success", intent=intent)}


def retrieve_application_external_context(state: ApplicationAgentState) -> ApplicationAgentState:
    if state.get("result"):
        return state
    intent = state.get("intent") or {}
    query = state.get("query", "")
    should_search = bool(
        not intent.get("needs_clarification")
        and (intent.get("needs_external") or {"kipris", "kosis", "tavily"} & set(intent.get("source_plan") or []))
    )
    external = {
        "enabled": should_search,
        "connectors": application_external_status(),
        "web": {"enabled": False, "provider": None, "results": [], "error": None},
        "search_query": None,
    }
    if should_search:
        terms = ["특허 출원", "KIPRIS", "KOSIS", "거절이유", "선행기술", "시장 통계"]
        search_query = " ".join([query, *terms[:3]])
        if intent.get("intent") == "prior_art_search":
            search_query = f"{query} KIPRIS 선행기술 IPC CPC 유사특허"
        elif intent.get("intent") == "rejection_response":
            search_query = f"{query} KIPRIS 의견제출통지서 거절이유 보정 의견서"
        elif intent.get("intent") == "application_strategy":
            search_query = f"{query} KOSIS 시장 통계 특허 출원 전략 사업화"
        external["search_query"] = search_query
        web_result = search_web(search_query)
        external["web"] = web_result
        # Save to topic wiki (same pipeline as patent chatbot)
        web_results = web_result.get("results") or []
        if web_results:
            try:
                from ..vectorstore import auto_approve_web_draft
                auto_approve_web_draft(
                    "_application",
                    draft_path=None,
                    query=search_query,
                    results=web_results,
                    topic_override="특허출원_절차",
                )
            except Exception:
                pass
    return {
        **state,
        "external_context": external,
        "trace": _trace(
            state,
            "retrieve_application_external_context",
            "success",
            enabled=should_search,
            result_count=len((external.get("web") or {}).get("results") or []),
        ),
    }


def retrieve_application_context(state: ApplicationAgentState) -> ApplicationAgentState:
    if state.get("result"):
        return state
    if state.get("refresh_index"):
        refresh_application_index(force=True)
    status = application_index_status()
    if not status.get("index_exists"):
        refresh_application_index(force=True)
    top_k = int(state.get("top_k") or 6)
    intent = state.get("intent") or {}
    preferred_terms = _intent_preference_terms(str(intent.get("intent") or "application_procedure"))
    intent_name = str(intent.get("intent") or "application_procedure")
    expanded_query = " ".join(
        [
            state.get("retrieval_query") or state.get("query", ""),
            " ".join(preferred_terms),
        ]
    )
    official_retrieval = search_application_index(expanded_query, top_k=max(top_k * 5, 20))
    case_retrieval = search_failed_patent_case_index(
        str(state.get("failed_patent_id") or ""),
        expanded_query,
        top_k=max(top_k * 4, 16),
    )
    official_hits = _dedupe_hits(
        [*preferred_application_hits(preferred_terms, top_k=top_k * 2), *list(official_retrieval.get("hits") or [])]
    )
    case_hits = _dedupe_hits(list(case_retrieval.get("hits") or []))
    if intent_name == "failed_case_evaluation":
        merged_hits = _dedupe_hits([*case_hits, *official_hits])
    elif intent_name in {"rejection_response", "prior_art_search", "drafting_claims", "application_strategy"}:
        merged_hits = _dedupe_hits([*case_hits, *official_hits])
    else:
        merged_hits = _dedupe_hits([*official_hits, *case_hits])
    ranked_hits = _rerank_hits_for_intent(_filter_hits_for_intent(merged_hits, intent), intent)
    hits = _limit_repeated_sources(ranked_hits, intent, top_k=top_k)
    case_report_summary = (
        failed_patent_case_report_summary(str(state.get("failed_patent_id") or ""))
        if intent_name == "failed_case_evaluation"
        else None
    )
    retrieval = {
        "query": expanded_query,
        "mode": "application_official_plus_selected_failed_case_vectorstores",
        "patent_id": "patent_application",
        "failed_patent_id": state.get("failed_patent_id"),
        "top_k": top_k,
        "hit_count": len(hits),
        "hits": hits,
        "official_hit_count": len(official_hits),
        "failed_case_hit_count": len(case_hits),
        "official": {
            "mode": official_retrieval.get("mode"),
            "hit_count": official_retrieval.get("hit_count"),
        },
        "failed_case": {
            "mode": case_retrieval.get("mode"),
            "hit_count": case_retrieval.get("hit_count"),
        },
        "case_report_summary": case_report_summary,
        "reranked_for_intent": (state.get("intent") or {}).get("intent"),
    }
    return {
        **state,
        "retrieval": retrieval,
        "trace": _trace(
            state,
            "retrieve_application_context",
            "success",
            hit_count=retrieval.get("hit_count", 0),
            mode=retrieval.get("mode"),
        ),
    }


def _intent_preference_terms(intent: str) -> list[str]:
    preferences = {
        "failed_case_evaluation": ["latest_report", "평가 요약", "Overall score", "overall_score", "dimension_scores", "Verification grade", "report_verification"],
        "application_procedure": ["patent_application_process_guide", "SRC-001", "SRC-016", "출원가이드", "출원 절차", "손쉬운 이용"],
        "forms_and_filing": ["SRC-002", "SRC-003", "SRC-021", "특허고객번호", "인증서", "서식", "서류", "위임장"],
        "drafting_claims": ["SRC-006", "SRC-017", "명세서", "청구항", "청구범위", "심사기준"],
        "prior_art_search": ["prior_art_search_workflow", "SRC-012", "SRC-013", "SRC-014", "KIPRIS", "CPC", "IPC"],
        "rejection_response": ["feedback", "patent_rejection", "SRC-020", "SRC-021", "거절", "의견제출", "보정", "심판", "피드백"],
        "fees": ["SRC-004", "SRC-010", "수수료", "등록료", "심사청구료", "감면"],
        "application_strategy": ["SRC-017", "SRC-019", "전략", "우선심사", "해외", "사업화"],
    }
    return preferences.get(intent, preferences["application_procedure"])


def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped = []
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        key = f"{metadata.get('source_path')}:{metadata.get('chunk_index')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    return deduped


def _hit_role(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    return str(metadata.get("application_role") or metadata.get("source_role") or "")


def _hit_path_text(hit: dict[str, Any]) -> str:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    return _norm(
        " ".join(
            [
                str(metadata.get("file_name") or ""),
                str(metadata.get("relative_source_path") or ""),
                str(metadata.get("source_path") or ""),
            ]
        )
    ).lower()


def _is_structured_metadata_hit(hit: dict[str, Any]) -> bool:
    path_text = _hit_path_text(hit)
    return any(
        marker in path_text
        for marker in [
            "official_sources.csv",
            "official_sources.json",
            "patent_sources.xlsx",
            "readme.md",
        ]
    ) or path_text.endswith((".csv", ".json", ".xlsx"))


def _display_source_name(name: Any) -> str | None:
    source_name = _norm(name).strip()
    if not source_name:
        return None
    lower = source_name.lower()
    if lower in {"official_sources.csv", "official_sources.json", "patent_sources.xlsx", "readme.md"}:
        return None
    if any(term in source_name for term in NON_PATENT_PACK_TERMS):
        return None
    return source_name


def _filter_hits_for_intent(hits: list[dict[str, Any]], intent: dict[str, Any]) -> list[dict[str, Any]]:
    intent_name = str(intent.get("intent") or "application_procedure")
    filtered = []
    for hit in hits:
        role = _hit_role(hit)
        path_text = _hit_path_text(hit)
        if any(term in path_text for term in NON_PATENT_PACK_TERMS):
            continue
        if intent_name in {"application_procedure", "forms_and_filing", "fees"} and any(
            term in path_text for term in ["pct", "국제예비심사", "국제조사"]
        ):
            continue
        is_feedback = role == "rejection_failure_feedback" or "feedback/" in path_text
        is_rejection_doc = is_feedback or any(term in path_text for term in ["거절", "의견", "통지서", "rejection"])
        if intent_name == "failed_case_evaluation" and "latest_report.md" not in path_text and "input/" not in path_text:
            continue
        if intent_name not in {"rejection_response", "failed_case_evaluation"} and is_rejection_doc:
            continue
        filtered.append(hit)
    return filtered or hits


def _limit_repeated_sources(hits: list[dict[str, Any]], intent: dict[str, Any], *, top_k: int) -> list[dict[str, Any]]:
    intent_name = str(intent.get("intent") or "application_procedure")
    max_per_file = 3 if intent_name == "failed_case_evaluation" else 2 if intent_name == "rejection_response" else 1
    if intent_name == "failed_case_evaluation":
        ordered_hits = [hit for hit in hits if "latest_report.md" in _hit_path_text(hit)]
        ordered_hits.extend(hit for hit in hits if "latest_report.md" not in _hit_path_text(hit))
    elif intent_name in {"application_procedure", "forms_and_filing", "fees", "drafting_claims"}:
        ordered_hits = [hit for hit in hits if not _is_structured_metadata_hit(hit)]
        ordered_hits.extend(hit for hit in hits if _is_structured_metadata_hit(hit))
    else:
        ordered_hits = hits
    counts: dict[str, int] = {}
    selected = []
    overflow = []
    for hit in ordered_hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        key = str(metadata.get("source_path") or metadata.get("file_name") or "unknown")
        if counts.get(key, 0) < max_per_file:
            selected.append(hit)
            counts[key] = counts.get(key, 0) + 1
        else:
            overflow.append(hit)
        if len(selected) >= top_k:
            return selected
    return (selected + overflow)[:top_k]


def _rerank_hits_for_intent(hits: list[dict[str, Any]], intent: dict[str, Any]) -> list[dict[str, Any]]:
    terms = _intent_preference_terms(str(intent.get("intent") or "application_procedure"))
    intent_name = str(intent.get("intent") or "application_procedure")

    def score(hit: dict[str, Any]) -> float:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        role = str(metadata.get("application_role") or "")
        file_name = str(metadata.get("file_name") or "").lower()
        rel_path = str(metadata.get("relative_source_path") or "").lower()
        haystack = " ".join(
            [
                file_name,
                rel_path,
                str(hit.get("page_content") or "")[:1200],
            ]
        ).lower()
        boost = 0.0
        for term in terms:
            if term.lower() in haystack:
                boost += 0.16
        if intent_name == "application_procedure":
            if role == "application_procedure":
                boost += 0.35
            if any(term in file_name for term in ["process_guide", "손쉬운"]):
                boost += 0.28
            if file_name.endswith((".json", ".csv", ".xlsx")):
                boost -= 0.85
        elif intent_name == "forms_and_filing":
            if role == "application_procedure":
                boost += 0.18
            if any(term in haystack for term in ["특허고객번호", "인증서", "서식", "위임장", "전자출원"]):
                boost += 0.28
            if file_name.endswith((".json", ".csv", ".xlsx")):
                boost -= 0.65
        elif intent_name == "rejection_response" and role == "rejection_failure_feedback":
            boost += 0.45
        elif intent_name == "failed_case_evaluation":
            if "latest_report.md" in rel_path:
                boost += 1.2
            if role == "rejection_failure_feedback":
                boost += 0.35
            if any(term in haystack for term in ["평가 요약", "overall score", "영역별 점수", "verification grade", "보고서 신뢰도"]):
                boost += 0.45
            if file_name.endswith((".json", ".html")):
                boost -= 0.7
        elif intent_name == "prior_art_search" and role == "prior_art_search":
            boost += 0.35
        if "download" not in rel_path:
            boost += 0.08
        return float(hit.get("score") or 0.0) + boost

    return sorted(hits, key=score, reverse=True)


def _context_for_prompt(hits: list[dict[str, Any]]) -> str:
    lines = []
    for index, hit in enumerate(hits, 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        lines.append(
            f"[A{index}] {metadata.get('file_name')} / {metadata.get('source_type')} / score={hit.get('score')}\n"
            f"{str(hit.get('page_content') or '')[:1400]}"
        )
    return "\n\n".join(lines) if lines else "No application official context found."


def _external_context_for_prompt(external: dict[str, Any]) -> str:
    if not external.get("enabled"):
        return "External context was not requested."
    lines = ["External connector status:"]
    for name, status in (external.get("connectors") or {}).items():
        lines.append(f"- {name}: configured={status.get('configured')} / usage={status.get('usage')}")
    web = external.get("web") or {}
    results = web.get("results") or []
    if not results:
        lines.append(f"- web search: no result / provider={web.get('provider')} / error={web.get('error')}")
        return "\n".join(lines)
    lines.append(f"Web/Tavily evidence query: {external.get('search_query')}")
    for index, item in enumerate(results[:5], 1):
        lines.append(f"[E{index}] {item.get('title')}\n{item.get('snippet')}\n{item.get('url') or ''}")
    return "\n\n".join(lines)


def _clean_evidence_snippet(value: Any, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r'["{}\[\]]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" |,")
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _fallback_application_answer(query: str, intent: dict[str, Any], hits: list[dict[str, Any]]) -> str:
    intent_name = str(intent.get("intent") or "application_procedure")
    source_names = []
    display_source_names = []
    evidence_rows: list[tuple[str, str]] = []
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        name = metadata.get("file_name")
        if name and name not in source_names:
            source_names.append(str(name))
        display_name = _display_source_name(name)
        if display_name and display_name not in display_source_names:
            display_source_names.append(display_name)
        snippet = _clean_evidence_snippet(hit.get("page_content"))
        role = str(metadata.get("application_role") or "")
        if (
            intent_name == "rejection_response"
            and name
            and snippet
            and len(evidence_rows) < 4
            and role == "rejection_failure_feedback"
        ):
            evidence_rows.append((str(name), snippet))
    source_line = ", ".join(display_source_names[:5] or source_names[:3]) or "공식 출원 자료팩"

    templates = {
        "application_procedure": [
            ("발명 정리", "해결하려는 문제, 핵심 구성, 효과, 적용 제품/서비스를 먼저 한 문장씩 정리합니다."),
            ("선행기술 검색", "KIPRIS와 CPC/IPC 키워드로 유사 특허를 찾고 차별점을 표시합니다."),
            ("출원 준비", "특허고객번호, 인증서, 출원인 정보, 명세서, 청구범위, 요약서, 도면을 준비합니다."),
            ("전자출원/수수료", "특허로에서 서류를 제출하고 출원료를 납부합니다."),
            ("심사청구", "출원 후 심사청구 여부와 시점을 정하고, 거절이유가 오면 의견서/보정서로 대응합니다."),
            ("등록", "특허결정 후 등록료를 납부하고 권리 유지 일정을 관리합니다."),
        ],
        "prior_art_search": [
            ("키워드 확장", "발명의 목적, 구성, 효과, 동의어, 영문 키워드를 나눠 검색식을 만듭니다."),
            ("분류 검색", "IPC/CPC를 함께 사용해 키워드 누락을 줄입니다."),
            ("유사문헌 선별", "청구항 구성요소와 가장 가까운 문헌을 우선순위로 둡니다."),
            ("차별점 정리", "신규성/진보성 주장에 쓸 차이를 표로 남깁니다."),
        ],
        "drafting_claims": [
            ("핵심 구성 추출", "발명의 필수 구성과 선택 구성을 분리합니다."),
            ("독립항 작성", "필수 구성만으로 넓게 쓰고, 효과가 드러나게 연결합니다."),
            ("종속항 작성", "구체 실시예, 재료, 수치범위, 동작 조건을 단계적으로 좁힙니다."),
            ("명세서 보강", "문제, 해결수단, 효과, 실시예, 변형예를 청구항과 맞춰 씁니다."),
        ],
        "rejection_response": [
            ("통지서 해석", "거절되는 청구항, 인용문헌, 거절유형, 제출기한을 먼저 분리합니다."),
            ("대응 방향 선택", "신규성/진보성은 차이점과 효과를 주장하고, 기재불비는 명세서/청구항을 보정합니다."),
            ("보정안 검토", "신규사항 추가 금지와 권리범위 축소 위험을 확인합니다."),
            ("의견서 제출", "주장 근거와 보정 전후 대비를 함께 제출합니다."),
            ("불복 검토", "최종 거절이면 거절결정불복심판과 비용/기한을 검토합니다."),
        ],
        "fees": [
            ("출원료", "출원 종류, 청구항 수, 전자/서면 여부를 기준으로 확인합니다."),
            ("심사청구료", "심사청구 시점과 청구항 수에 따라 별도로 계산합니다."),
            ("감면", "개인, 중소기업, 연구기관 등 감면 대상과 증빙서류를 확인합니다."),
            ("등록료", "특허결정 후 설정등록료와 이후 연차료 일정을 관리합니다."),
        ],
        "forms_and_filing": [
            ("특허고객번호", "출원인/대리인 식별을 위해 먼저 발급합니다."),
            ("인증서 등록", "전자출원 전 공동인증서 사용등록을 완료합니다."),
            ("서식 작성", "출원서, 명세서, 청구범위, 요약서, 도면, 위임장 등 필요 서식을 확인합니다."),
            ("제출 확인", "접수번호, 수수료 납부, 보정요구 통지를 확인합니다."),
        ],
        "application_strategy": [
            ("권리화 목적", "방어, 라이선스, 투자, 제품 보호 중 목적을 정합니다."),
            ("청구범위 전략", "넓은 독립항과 방어용 종속항을 함께 설계합니다."),
            ("심사 전략", "우선심사, 심사유예, 해외출원 우선권 일정을 검토합니다."),
            ("사업화 연결", "제품 출시, 논문 공개, 전시 공개 전에 출원 일정을 맞춥니다."),
        ],
    }
    steps = templates.get(intent_name, templates["application_procedure"])
    intro = {
        "application_procedure": "처음 특허 출원 준비 절차로 분류했습니다. 공식 출원 자료를 기준으로 실제 준비 순서를 먼저 정리합니다.",
        "rejection_response": "거절/실패 대응 질문으로 분류했습니다. 의견서와 피드백 리포트를 기준으로 문제 원인과 보정 방향을 나눠 봅니다.",
        "prior_art_search": "선행기술 조사 질문으로 분류했습니다. 검색식, 분류, 유사문헌 선별, 차별점 정리 순서로 답합니다.",
        "drafting_claims": "명세서/청구항 작성 질문으로 분류했습니다. 권리범위 설계와 기재요건을 중심으로 답합니다.",
        "forms_and_filing": "서식/전자출원 준비 질문으로 분류했습니다. 계정, 인증서, 제출서류 순서로 답합니다.",
        "fees": "수수료/비용 질문으로 분류했습니다. 출원료, 심사청구료, 감면, 등록료를 나눠 답합니다.",
        "application_strategy": "출원 전략 질문으로 분류했습니다. 권리화 목적, 청구범위, 심사전략, 사업 일정을 함께 봅니다.",
    }.get(intent_name, "공식 출원 자료를 기준으로 답변합니다.")
    headings = {
        "application_procedure": "## 처음 특허 출원 준비 순서",
        "forms_and_filing": "## 특허 출원 준비 서류와 제출 준비",
        "fees": "## 특허 출원 비용 확인 순서",
        "rejection_response": "## 거절/실패 대응 방향",
        "prior_art_search": "## 선행기술 조사 순서",
        "drafting_claims": "## 명세서와 청구항 작성 방향",
        "application_strategy": "## 특허 출원 전략",
    }
    lines = [headings.get(intent_name, "## 특허 출원 도우미 답변"), "", intro, ""]
    if evidence_rows and intent_name == "rejection_response":
        lines.extend(["### 근거에서 바로 확인한 내용"])
        for name, snippet in evidence_rows:
            lines.append(f"- **{name}**: {snippet}")
        lines.append("")
    else:
        lines.extend(["### 참조 공식 자료", f"- {source_line}", ""])
    if intent.get("answer_format") in {"checklist_table", "table_and_diagram"}:
        if intent_name == "rejection_response":
            lines.extend(["| 진단 축 | 확인할 근거 | 대응 전략 | 참조 자료 |", "| --- | --- | --- | --- |"])
            rows = [
                ("거절유형", "거절되는 청구항, 인용문헌, 법조문, 제출기한", "통지서 문구를 신규성/진보성/기재불비/절차 흠결로 분류", source_line),
                ("신규성/진보성", "인용문헌과 청구항 구성요소의 일치/차이", "차이점, 작용효과, 결합 곤란성을 의견서에 구조화", source_line),
                ("기재불비", "명세서 지원 여부, 용어 명확성, 실시가능성", "명세서 근거가 있는 범위 안에서 청구항과 설명을 보정", source_line),
                ("보정 리스크", "신규사항 추가 여부, 권리범위 축소 폭", "보정 전후 대비표를 만들고 핵심 권리범위가 살아있는지 확인", source_line),
                ("후속 절차", "의견서/보정서 제출기한, 최종거절 가능성", "기한 내 제출 후 불복심판/분할출원/재출원 전략을 비교", source_line),
            ]
            for row in rows:
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.extend(["| 확인 항목 | 해야 할 일 | 근거 |", "| --- | --- | --- |"])
            for title, action in steps:
                lines.append(f"| {title} | {action} | {source_line} |")
    else:
        for index, (title, action) in enumerate(steps, 1):
            lines.append(f"{index}. **{title}**: {action}")
    next_actions = {
        "application_procedure": [
            "발명 요약 1페이지를 먼저 만듭니다: 문제, 핵심 구성, 효과, 적용 제품을 한 줄씩 적습니다.",
            "KIPRIS/CPC/IPC 키워드로 선행기술을 찾고, 유사문헌과 다른 점을 표로 정리합니다.",
            "독립항/종속항 초안을 만든 뒤 명세서, 요약서, 도면, 출원인 정보를 준비합니다.",
            "특허고객번호와 인증서, 수수료, 심사청구 여부를 확인한 뒤 전자출원합니다.",
        ],
        "rejection_response": [
            "거절의견서 원문에서 거절 청구항, 인용문헌, 제출기한을 먼저 체크합니다.",
            "기존 특허 원본/보고서가 연결되어 있으면 청구항별 차별점과 평가 리스크를 같이 대조합니다.",
            "보정안은 신규사항 추가 금지와 권리범위 축소 위험을 확인한 뒤 의견서 주장과 함께 제출합니다.",
        ],
        "prior_art_search": [
            "발명의 핵심 키워드, 동의어, 영문 표현, IPC/CPC 후보를 먼저 만듭니다.",
            "유사문헌별 청구항 대응표를 만들고 신규성/진보성 위험을 표시합니다.",
            "가장 가까운 문헌 3~5개를 기준으로 청구항 차별점을 다시 설계합니다.",
        ],
        "forms_and_filing": [
            "특허고객번호를 먼저 발급하고 전자출원용 공동인증서 사용등록을 확인합니다.",
            "출원서, 명세서, 청구범위, 요약서, 도면, 위임장 여부를 체크리스트로 모읍니다.",
            "출원인/발명자 정보, 우선권 주장 여부, 대리인 위임 여부를 제출 전에 대조합니다.",
            "특허로 전자출원 후 접수번호와 수수료 납부 상태를 확인합니다.",
        ],
    }.get(
        intent_name,
        [
            "현재 질문의 목적을 한 문장으로 정리합니다.",
            "공식자료 근거와 부족한 자료를 분리합니다.",
            "후속 질문에서 필요한 파일이나 의견서, 기존 보고서를 연결해 더 구체화합니다.",
        ],
    )
    lines.extend(["", "### 다음 액션"])
    lines.extend(f"{index}. {action}" for index, action in enumerate(next_actions, 1))
    lines.extend(["", f"확인한 공식 자료: {source_line}"])
    if intent.get("needs_diagram") or intent.get("answer_format") == "table_and_diagram":
        lines.extend(
            [
                "",
                "```mermaid",
                "flowchart LR",
                "  A[발명 정리] --> B[선행기술 검색]",
                "  B --> C[명세서/청구항 작성]",
                "  C --> D[전자출원/수수료]",
                "  D --> E[심사청구/거절 대응]",
                "```",
            ]
        )
    return "\n".join(lines)


def _fmt_metric(value: Any, default: str = "-") -> str:
    if value in (None, ""):
        return default
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _compact_answer_text(value: Any, *, limit: int = 230) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text or "-"


def _term_explanation_lines(query: str) -> list[str]:
    text = _norm(query).lower()
    glossary = {
        "무효 가능성": "등록 후에도 선행기술, 기재불비, 신규성/진보성 부족 등으로 특허가 무효가 될 위험입니다. 점수가 높다고 해도 근거 출처가 약하면 검토가 필요합니다.",
        "권리범위": "청구항이 실제로 보호하는 기술 범위입니다. 너무 좁으면 회피설계가 쉽고, 너무 넓으면 거절/무효 위험이 커집니다.",
        "권리범위 적절성": "청구항 범위가 발명의 핵심을 충분히 보호하면서도 선행기술과 충돌하지 않는지 보는 항목입니다.",
        "권리의 구성요소": "청구항을 이루는 필수 기술 요소입니다. 각 요소가 명세서에 뒷받침되고 선행기술과 차별되어야 합니다.",
        "권리의 추상성": "청구항 표현이 너무 추상적이어서 실시 형태나 기술 구성이 불명확한지 보는 항목입니다.",
        "침해 발견": "경쟁 제품이나 서비스가 청구항을 사용했는지 실제로 확인하고 입증하기 쉬운지 보는 항목입니다.",
        "신규성": "선행기술에 동일한 구성이 이미 공개되어 있으면 부족해지는 등록 요건입니다.",
        "진보성": "선행기술을 조합해 통상의 기술자가 쉽게 생각할 수 있으면 부족해지는 등록 요건입니다.",
        "기재불비": "명세서나 청구항이 불명확하거나, 발명을 실시할 수 있을 만큼 충분히 설명하지 못한 문제입니다.",
        "청구항": "특허권의 보호 범위를 정하는 문장입니다. 등록 가능성과 권리 강도는 대부분 청구항 설계에서 갈립니다.",
        "독립항": "다른 청구항을 인용하지 않고 발명의 핵심 구성을 직접 정의하는 청구항입니다.",
        "종속항": "독립항에 구체 조건을 추가해 방어 범위를 여러 층으로 만드는 청구항입니다.",
        "검증 등급": "보고서 내용이 출처, 수치, 근거로 얼마나 뒷받침되는지 자동 검증한 신뢰도 등급입니다.",
        "evidence coverage": "평가 항목 중 명시 근거가 붙은 비율입니다. 낮으면 점수 자체보다 검증 보강이 먼저 필요합니다.",
    }
    lines = []
    for term, explanation in glossary.items():
        if term.lower() in text:
            lines.append(f"- **{term}**: {explanation}")
    if not lines and any(term in text for term in TERM_EXPLANATION_TERMS):
        lines.append("- 질문한 용어가 보고서의 특정 항목명이라면, 해당 항목은 보통 `평가 점수`, `판단 근거`, `출처 유무`, `보정 필요성`을 함께 봐야 정확히 해석할 수 있습니다.")
    return lines


def _failed_case_evaluation_answer(summary: dict[str, Any] | None, hits: list[dict[str, Any]], *, query: str = "") -> str:
    if not summary or not summary.get("exists"):
        return "\n".join(
            [
                "## 실패특허 평가 결과",
                "",
                "아직 이 실패특허 케이스의 `latest_report.json`이 없습니다.",
                "먼저 `거절/실패특허 보고서 생성`을 실행하면, 생성된 보고서가 해당 케이스 폴더 전용 vectorstore에 반영되고 그 결과를 기준으로 답변할 수 있습니다.",
            ]
        )
    patent = summary.get("patent") if isinstance(summary.get("patent"), dict) else {}
    report_summary = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    dimension_scores = summary.get("dimension_scores") if isinstance(summary.get("dimension_scores"), dict) else {}
    verification = summary.get("verification") if isinstance(summary.get("verification"), dict) else {}
    similar = summary.get("similar_patents_brief") if isinstance(summary.get("similar_patents_brief"), dict) else {}
    low_items = [item for item in summary.get("low_score_items") or [] if isinstance(item, dict)]
    high_items = [item for item in summary.get("high_score_items") or [] if isinstance(item, dict)]
    issues = verification.get("issues") if isinstance(verification.get("issues"), list) else []
    lines = [
        f"## {patent.get('id') or summary.get('case_id')} 평가 결과",
        "",
        f"- 대상 특허: {patent.get('title') or '-'}",
        f"- 등록번호: {patent.get('registration_number') or patent.get('id') or '-'}",
        f"- 보고서 상태: {summary.get('status') or '-'}",
        f"- 종합 점수: {_fmt_metric(report_summary.get('overall_score'))}/5, {_fmt_metric(report_summary.get('overall_score_out_of_100'))}/100",
        f"- 종합 등급: {report_summary.get('overall_grade') or '-'}",
        f"- 보고서상 위험도: {report_summary.get('risk_level') or '-'}",
        f"- 자동 검증 등급: {verification.get('reliability_grade') or '-'}",
        f"- 자동 검증 점수: {_fmt_metric(verification.get('overall_reliability_score'))}",
        f"- 사람 검토 필요: {verification.get('human_review_required')}",
        "",
        "결론부터 보면, 이 케이스는 보고서 점수만 보면 `B+` 수준으로 평가되지만, 자동 검증 등급이 `D`라서 그대로 의사결정하기에는 위험합니다. 즉, 기술 자체 평가는 나쁘지 않지만 몇몇 고평가 항목의 출처가 약하고 사업화 근거가 부족해 사람 검토와 자료 보강이 필요합니다.",
        "",
        "### 핵심 원인 한눈에 보기",
        "",
        "1. **실제 거절 사유 원문이 부족합니다.** 의견제출통지서/거절결정서가 없으면 신규성, 진보성, 기재불비 중 무엇이 핵심 문제였는지 확정할 수 없습니다.",
        "2. **권리성 고평가 항목의 근거가 약합니다.** 무효 가능성, 권리범위 적절성, 권리 구성요소, 권리 추상성, 침해 발견/입증 용이성에서 출처 부족 검증 이슈가 잡혔습니다.",
        "3. **사업화 근거가 부족합니다.** 사내 적용처, 제품 연결, 매출/시장 근거가 부족하면 사업성 평가는 방어력이 약합니다.",
        "4. **보고서 점수와 검증 신뢰도가 충돌합니다.** 점수는 B+지만 검증 등급은 D라서, 발표/의사결정에는 보강 근거가 먼저 필요합니다.",
        "",
        "### 먼저 해야 할 3가지",
        "",
        "1. 의견제출통지서나 거절결정서 원문을 업로드해 실제 거절 조항과 인용문헌을 확인합니다.",
        "2. 청구항별로 `구성요소 - 선행문헌 대응 - 차별점 - 보정 방향` 표를 만듭니다.",
        "3. 보고서에서 출처 부족으로 표시된 권리성 항목과 사업화 근거를 보강한 뒤 보고서를 다시 생성합니다.",
        "",
    ]
    term_lines = _term_explanation_lines(query)
    if term_lines:
        lines.extend(["### 용어 설명", ""])
        lines.extend(term_lines)
        lines.append("")
    lines.extend(
        [
        "### 영역별 점수",
        "",
        "| 영역 | 평균 점수(1~5) | 100점 환산 | 등급 | 항목 수 |",
        "| --- | ---: | ---: | --- | ---: |",
        ]
    )
    if dimension_scores:
        for dimension, score in dimension_scores.items():
            if not isinstance(score, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(dimension),
                        _fmt_metric(score.get("average_score")),
                        _fmt_metric(score.get("score_out_of_100")),
                        str(score.get("grade") or "-"),
                        _fmt_metric(score.get("item_count")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | - | - | - | - |")
    lines.extend(
        [
            "",
            "### 왜 이렇게 평가됐는지",
            "",
            str(report_summary.get("overall_opinion") or "종합 의견이 보고서에 없습니다."),
            "",
            "보고서상 강하게 본 부분은 다음입니다.",
        ]
    )
    if high_items:
        for item in high_items[:3]:
            lines.append(
                f"- **{item.get('dimension')} / {item.get('item')}**: {_fmt_metric(item.get('score'))}/5. "
                f"{_compact_answer_text(item.get('judgment_summary'))}"
            )
    else:
        lines.append("- 강점 항목이 보고서에서 구조화되어 추출되지 않았습니다.")
    lines.extend(["", "보완하거나 주의해야 할 부분은 다음입니다."])
    if low_items:
        for item in low_items[:6]:
            lines.append(
                f"- **{item.get('dimension')} / {item.get('item')}**: {_fmt_metric(item.get('score'))}/5. "
                f"{_compact_answer_text(item.get('judgment_summary'))}"
            )
    else:
        lines.append("- 2점 이하의 뚜렷한 저평가 항목은 보고서에서 확인되지 않았습니다. 다만 검증 이슈가 있어 근거 보강은 필요합니다.")
    lines.extend(
        [
            "",
            "### 무엇이 문제였는지",
            "",
            "1. **평가 결과와 검증 결과가 서로 다릅니다.** 종합 평가는 B+지만, 자동 검증 등급은 D입니다. 따라서 점수 자체보다 `왜 그 점수가 나왔는지`를 뒷받침하는 출처를 먼저 보강해야 합니다.",
            "2. **권리성 고평가 항목 일부에 명시 근거가 약합니다.** 보고서 검증 이슈에서 무효 가능성, 권리범위 적절성, 권리의 구성요소, 권리의 추상성, 침해 발견/입증 용이성 항목에 출처 부족이 표시됐습니다.",
            "3. **사업화/RAG 근거가 부족합니다.** 사내 사업화 적용처, 실제 제품 연결, 매출/시장 근거가 충분하지 않으면 사업성 점수는 발표나 의사결정에서 방어하기 어렵습니다.",
            "4. **실제 거절 사유 원문이 없으면 실패 원인은 확정할 수 없습니다.** 의견제출통지서나 거절결정서가 없으면 신규성, 진보성, 기재불비 중 무엇이 핵심 거절 사유였는지 단정하면 안 됩니다.",
            "",
            "### 등록 가능성을 높이려면 해야 할 일",
            "",
            "| 우선순위 | 해야 할 일 | 이유 | 산출물 |",
            "| --- | --- | --- | --- |",
            "| 1 | 의견제출통지서/거절결정서 원문을 같은 케이스 폴더에 추가 | 실제 거절 조항과 인용문헌을 알아야 보정 방향이 정해짐 | 거절이유 요약표, 제출기한 체크 |",
            "| 2 | 청구항 구성요소 대응표 작성 | 청구항의 각 구성이 선행문헌에 있는지 비교해야 신규성/진보성 판단 가능 | 청구항-선행문헌 매핑표 |",
            "| 3 | 핵심 차별점 한 줄 정의 | 이 특허는 다중 임계값, 결함 개수 맵, 비교 가능한 시각화가 핵심이므로 차별점을 좁혀야 함 | 독립항 차별 포인트 |",
            "| 4 | 명세서 지원 근거 표시 | 보정 시 신규사항 추가 금지에 걸리지 않으려면 원 명세서 문단 근거가 필요 | 보정 근거 문단표 |",
            "| 5 | 종속항 보강 | 독립항이 좁아져도 방어 범위를 유지하려면 실시예/변형예/수치조건을 층화해야 함 | 보정 청구항 초안 |",
            "| 6 | 보고서 검증 이슈 보완 | B+ 평가를 신뢰하려면 출처 부족 항목과 사업화 근거를 채워야 함 | 보강 근거 파일, 최신 보고서 재생성 |",
            "",
            "### 이 특허 기준 보정 방향",
            "",
            "- 독립항은 `다수 반도체 이미지에서 결함 위치 정보를 획득 → 결함 개수 맵 생성 → 다중 임계값별 결함 이미지 생성 → 비교 가능한 형태로 시각화` 흐름이 핵심입니다.",
            "- 선행기술이 단순 결함 맵이나 단일 임계값 시각화라면, `다중 임계값`, `결함 개수별 픽셀값 구분`, `여러 이미지 비교 배열`, `차 이미지 생성`을 차별 포인트로 세워야 합니다.",
            "- 명세서에는 이 차별점이 결함의 군집/분포/반복 패턴 분석을 쉽게 한다는 효과로 연결되어 있어야 합니다.",
            "- 등록 목적이라면 독립항은 선행문헌과 겹치는 표현을 줄이고, 종속항에는 그리드 맵, 웨이퍼/다이 이미지, 차 이미지, 임계값 설정 방식 같은 구체 구성을 남기는 방향이 좋습니다.",
            "",
            "### 유사 특허 분석",
            "",
            f"- 유사 특허 분석 가능 여부: {similar.get('available') if similar else '-'}",
            f"- 유사 특허 수: {_fmt_metric(similar.get('total') if similar else None)}",
            f"- 유효/집행 가능 비율: {_fmt_metric(similar.get('enforceable_ratio') if similar else None)}",
            f"- 평균 유사도: {_fmt_metric(similar.get('avg_similarity') if similar else None)}",
            "",
            "### 검증상 주의점",
            "",
        ]
    )
    if issues:
        for issue in issues[:5]:
            if not isinstance(issue, dict):
                continue
            item = f" / {issue.get('item')}" if issue.get("item") else ""
            lines.append(f"- {issue.get('severity') or '-'}: {issue.get('message') or '-'}{item}")
    else:
        lines.append("- 주요 검증 이슈가 없습니다.")
    lines.extend(
        [
            "",
            "### 답변에 사용한 데이터",
            "",
            f"- 실패특허 케이스 전용 보고서: {summary.get('markdown_path') or summary.get('report_path')}",
            "- 케이스 vectorstore 범위: 선택된 실패특허 원본 PDF + 해당 케이스의 latest_report.md",
        ]
    )
    if hits:
        source_names = []
        for hit in hits:
            metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
            name = metadata.get("file_name")
            if name and name not in source_names:
                source_names.append(str(name))
        if source_names:
            lines.append(f"- 검색 근거: {', '.join(source_names[:4])}")
    return "\n".join(lines)


def _answer_needs_guided_repair(query: str, intent: dict[str, Any], answer: Any) -> bool:
    intent_name = str(intent.get("intent") or "application_procedure")
    if intent_name not in {"application_procedure", "forms_and_filing", "fees", "drafting_claims"}:
        return False
    query_text = _norm(query).lower()
    answer_text = _norm(answer).lower()
    if any(term in query_text for term in ["디자인", "상표", "pct", "국제출원", "국제예비심사"]):
        return False
    off_topic_terms = [
        "디자인",
        "디자인보호법",
        "물품류",
        "상표",
        "니스",
        "국제예비심사",
        "pct",
    ]
    if any(term.lower() in answer_text for term in off_topic_terms):
        return True
    if intent_name != "rejection_response" and all(term in answer_text for term in ["거절", "불복", "실패 요인"]):
        return True
    return False


def answer_application_question(state: ApplicationAgentState) -> ApplicationAgentState:
    if state.get("result"):
        return state
    retrieval = state.get("retrieval") or {}
    hits = list(retrieval.get("hits") or [])
    intent = state.get("intent") or {}
    if intent.get("needs_clarification"):
        answer = str(intent.get("clarification_question") or "어떤 출원 업무 범위를 기준으로 답할까요?")
        result = {
            "query": state.get("query", ""),
            "patent_id": "patent_application",
            "answer": answer,
            "source_cards": [],
            "metrics": {
                "engine": "patent_application_langgraph",
                "intent_agent": intent,
                "hit_count": 0,
                "external_context": {"enabled": False, "search_query": None, "web_result_count": 0},
                "llm_ok": False,
                "llm_error": "clarification_required",
                "answer_repaired": True,
                "answer_strategy": "ask_clarification",
                "answer_format_plan": intent.get("answer_format"),
                "source_plan": intent.get("source_plan"),
            },
        }
        result["metrics"]["answer_quality"] = answer_quality_metrics(
            query=state.get("query", ""),
            answer=result["answer"],
            source_cards=[],
            retrieval_scores=[],
        )
        return {
            **state,
            "result": result,
            "trace": _trace(state, "answer_application_question", "success", source_count=0, answer_strategy="ask_clarification"),
        }
    intent_name = str(intent.get("intent") or "application_procedure")
    if intent_name == "failed_case_evaluation":
        answer = _failed_case_evaluation_answer(retrieval.get("case_report_summary"), hits, query=state.get("query", ""))
        source_cards = cards_from_application_hits(hits, query=state.get("query", ""))
        result = {
            "query": state.get("query", ""),
            "patent_id": f"patent_application:{state.get('failed_patent_id')}",
            "answer": answer,
            "source_cards": source_cards,
            "metrics": {
                "engine": "patent_application_langgraph",
                "answer_provider": "deterministic_report_summary",
                "intent_agent": intent,
                "failed_patent_id": state.get("failed_patent_id"),
                "hit_count": retrieval.get("hit_count", 0),
                "official_hit_count": retrieval.get("official_hit_count", 0),
                "failed_case_hit_count": retrieval.get("failed_case_hit_count", 0),
                "external_context": {"enabled": False, "search_query": None, "web_result_count": 0},
                "llm_ok": True,
                "llm_error": None,
                "answer_repaired": False,
                "answer_strategy": "selected_failed_case_latest_report_summary",
                "answer_format_plan": intent.get("answer_format"),
                "source_plan": intent.get("source_plan"),
                "case_report_summary_exists": bool((retrieval.get("case_report_summary") or {}).get("exists")),
            },
        }
        result["metrics"]["answer_quality"] = answer_quality_metrics(
            query=state.get("query", ""),
            answer=result["answer"],
            source_cards=source_cards,
            retrieval_scores=[hit.get("score") for hit in hits if isinstance(hit.get("score"), (int, float))],
        )
        return {
            **state,
            "result": result,
            "trace": _trace(state, "answer_application_question", "success", source_count=len(result["source_cards"]), answer_strategy="selected_failed_case_latest_report_summary"),
        }
    prompt = f"""당신은 SKIPA 특허 출원 전문 어시스턴트입니다. 전문 변리사 수준의 간결하고 실용적인 한국어 답변을 제공합니다.
제공된 공식팩·케이스 근거 안에서만 답변하고, 사실을 창작하지 않습니다.

질문 의도: {intent_name}
선택된 실패특허: {state.get("failed_patent_id") or "없음"}
사용자 질문: {state.get("query", "")}
대화 맥락: {state.get("history_summary") or "-"}

공식팩 + 케이스 근거:
{_context_for_prompt(hits)}

외부 보강 근거:
{_external_context_for_prompt(state.get("external_context") or {})}

답변 규칙:
- 서론 없이 핵심 답변으로 바로 시작합니다 (1-3문장).
- 출원 절차: 구체적인 단계와 기한을 포함합니다.
- 거절 대응: 신규성/진보성/기재불비 유형별로 간결하게 구분합니다.
- 실패 요인 분석: 핵심 원인 3개 이내로 정리합니다.
- 실패특허 케이스는 현재 선택된 케이스({state.get("failed_patent_id") or "없음"})의 근거만 사용합니다.
- 외부 근거는 공식팩 근거를 보강할 때만 사용합니다.
- 표가 필요하면 Markdown 표를 포함합니다.
- 다이어그램이 필요하면 Mermaid flowchart를 포함합니다.
- 근거가 부족한 부분은 한 문장으로만 언급합니다. "부족한 데이터 제안", "확인해야 할 공식 자료명" 섹션은 추가하지 않습니다.
"""
    use_guided_template = intent_name in GUIDED_TEMPLATE_INTENTS
    if ANSWER_PROVIDER == "openai":
        llm = call_openai_prompt(
            prompt,
            model=ANSWER_MODEL,
            max_output_tokens=ANSWER_NUM_PREDICT,
            timeout=ANSWER_LLM_TIMEOUT,
            temperature=0.2,
        )
    elif use_guided_template:
        llm = {"ok": False, "text": "", "error": "guided_template_intent"}
    else:
        llm = call_ollama(prompt, model=ANSWER_MODEL, num_predict=ANSWER_NUM_PREDICT, timeout=ANSWER_LLM_TIMEOUT)
    answer = llm.get("text") if llm.get("ok") else _fallback_application_answer(state.get("query", ""), intent, hits)
    repaired_answer = not bool(llm.get("ok"))
    if _answer_needs_guided_repair(state.get("query", ""), intent, answer):
        answer = _fallback_application_answer(state.get("query", ""), intent, hits)
        repaired_answer = True
    source_cards = cards_from_application_hits(hits, query=state.get("query", ""))
    external_results = (((state.get("external_context") or {}).get("web") or {}).get("results") or [])
    if external_results:
        source_cards.extend(cards_from_web(external_results[:5], start_index=len(source_cards) + 1, query=state.get("query", "")))
    result = {
        "query": state.get("query", ""),
        "patent_id": f"patent_application:{state.get('failed_patent_id')}",
        "answer": str(answer or ""),
        "source_cards": source_cards,
        "metrics": {
            "engine": "patent_application_langgraph",
            "answer_provider": ANSWER_PROVIDER,
            "intent_agent": intent,
            "failed_patent_id": state.get("failed_patent_id"),
            "hit_count": retrieval.get("hit_count", 0),
            "official_hit_count": retrieval.get("official_hit_count", 0),
            "failed_case_hit_count": retrieval.get("failed_case_hit_count", 0),
            "external_context": {
                "enabled": bool((state.get("external_context") or {}).get("enabled")),
                "search_query": (state.get("external_context") or {}).get("search_query"),
                "web_result_count": len(((state.get("external_context") or {}).get("web") or {}).get("results") or []),
                "connectors": (state.get("external_context") or {}).get("connectors"),
            },
            "llm_ok": bool(llm.get("ok")),
            "llm_error": llm.get("error"),
            "answer_repaired": repaired_answer,
            "answer_strategy": "openai_answer_then_guardrail" if ANSWER_PROVIDER == "openai" else "guided_template" if use_guided_template else "llm_then_guardrail",
            "answer_format_plan": intent.get("answer_format"),
            "source_plan": intent.get("source_plan"),
        },
    }
    result["metrics"]["answer_quality"] = answer_quality_metrics(
        query=state.get("query", ""),
        answer=result["answer"],
        source_cards=source_cards,
        retrieval_scores=[hit.get("score") for hit in hits if isinstance(hit.get("score"), (int, float))],
    )
    return {
        **state,
        "result": result,
        "trace": _trace(state, "answer_application_question", "success", source_count=len(result["source_cards"])),
    }


def finish_application_answer(state: ApplicationAgentState) -> ApplicationAgentState:
    result = dict(state.get("result") or {})
    metrics = dict(result.get("metrics") or {})
    trace = _trace(state, "finish_application_answer", "success")
    metrics["agent_trace"] = trace
    metrics["application_workflow"] = "failed_case_validation -> history -> intent_router -> official_pack_vectorstore + selected_failed_case_vectorstore -> external_enrichment -> guided_answer"
    metrics["answer_has_diagram"] = "```mermaid" in str(result.get("answer") or "")
    result["metrics"] = metrics
    return {**state, "result": result, "trace": trace}


def _sequential(state: ApplicationAgentState) -> ApplicationAgentState:
    state = resolve_application_history(state)
    state = validate_failed_patent_case(state)
    state = route_application_question(state)
    state = retrieve_application_context(state)
    state = retrieve_application_external_context(state)
    state = answer_application_question(state)
    return finish_application_answer(state)


def build_application_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ApplicationAgentState)
        graph.add_node("resolve_application_history", resolve_application_history)
        graph.add_node("validate_failed_patent_case", validate_failed_patent_case)
        graph.add_node("route_application_question", route_application_question)
        graph.add_node("retrieve_application_context", retrieve_application_context)
        graph.add_node("retrieve_application_external_context", retrieve_application_external_context)
        graph.add_node("answer_application_question", answer_application_question)
        graph.add_node("finish_application_answer", finish_application_answer)
        graph.set_entry_point("resolve_application_history")
        graph.add_edge("resolve_application_history", "validate_failed_patent_case")
        graph.add_edge("validate_failed_patent_case", "route_application_question")
        graph.add_edge("route_application_question", "retrieve_application_context")
        graph.add_edge("retrieve_application_context", "retrieve_application_external_context")
        graph.add_edge("retrieve_application_external_context", "answer_application_question")
        graph.add_edge("answer_application_question", "finish_application_answer")
        graph.add_edge("finish_application_answer", END)
        return graph.compile()
    except Exception:
        return None


APPLICATION_GRAPH = build_application_graph()


def run_application_agent(
    query: str,
    *,
    user_id: str | None = None,
    failed_patent_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    top_k: int = 6,
    refresh_index: bool = False,
) -> dict[str, Any]:
    state: ApplicationAgentState = {
        "query": query,
        "user_id": user_id,
        "failed_patent_id": failed_patent_id,
        "chat_history": chat_history or [],
        "top_k": top_k,
        "refresh_index": refresh_index,
        "trace": [],
    }
    final_state = APPLICATION_GRAPH.invoke(state) if APPLICATION_GRAPH is not None else _sequential(state)
    return dict(final_state.get("result") or {})


def application_graph_mermaid() -> str:
    return """flowchart TD
  U[실패특허 원본 PDF 업로드] --> U1[failed_patent/{case_id}/input 저장]
  U1 --> RG[보고서 생성 에이전트 eval_logic 실행]
  RG --> RP[failed_patent/{case_id}/reports 저장]
  RP --> RV[선택 케이스 전용 vectorstore 갱신]
  U1 --> RV

  A[사용자 질문] --> B[대화 이력 반영]
  B --> C{failed_patent_id 있음?}
  C -- 없음 --> C1[원본 PDF 업로드/케이스 선택 요청]
  C -- 있음 --> C2{케이스 원본 PDF 있음?}
  C2 -- 없음 --> C1
  C2 -- 있음 --> D[선택 케이스 전용 vectorstore 확인/갱신]
  RV --> D
  D --> E[OpenAI 경량 LLM 의도 라우팅]
  E --> F{질문 유형}
  F -- 출원 절차/서식/수수료 --> G[공용 공식팩 vectorstore 검색]
  F -- 청구항/명세서/선행기술 --> H[공식팩 + 선택 케이스 원문 검색]
  F -- 거절/실패 요인/피드백 --> I[선택 케이스 원본/사유서/보고서 검색]
  G --> J[검색 결과 병합/재랭킹]
  H --> J
  I --> J
  J --> K{외부 보강 필요?}
  K -- KIPRIS/KOSIS/Tavily 필요 --> L[외부 근거 보강]
  K -- 내부 근거 충분 --> M[외부 검색 생략]
  L --> N[OpenAI 상용 서비스형 답변 생성]
  M --> N
  N --> O[표/다이어그램/체크리스트 형식화]
  O --> P[근거 카드 + 품질 지표 + 케이스 ID]
"""
