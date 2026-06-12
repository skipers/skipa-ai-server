"""Pre-application evaluation API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ..agents.pre_eval_graph import pre_eval_graph_mermaid, run_pre_eval_chat_agent
from ..schemas import (
    ChatHistoryItem,
    PreEvalChatRequest,
    PreEvalReportCompleteRequest,
    PreEvalReportCompleteResponse,
    PublicChatResponse,
)
from ..pre_eval_data import (
    create_pre_eval_case,
    get_pre_eval_report,
    handle_report_complete_webhook,
    list_pre_application_vectorstores,
    list_pre_eval_cases,
    pre_application_vectorstore_status,
    pre_eval_case_status,
    refresh_pre_eval_case_index,
    search_pre_application_vectorstore,
    search_pre_eval_vectorstore,
)


router = APIRouter(prefix="/api/v1/pre-eval", tags=["pre-eval"])


def _chat_history_payload(items: list[ChatHistoryItem]) -> list[dict]:
    return [item.model_dump(exclude_none=True) for item in items]


# ── 🟢 외부 공개 API ──────────────────────────────────────────────────────

@router.post(
    "/webhook/report-complete",
    response_model=PreEvalReportCompleteResponse,
    summary="[외부] 사전 출원 보고서 생성 완료 알림",
    description=(
        "외부 시스템(사전 출원 평가 서비스)이 보고서 생성 완료를 알릴 때 호출합니다.\n\n"
        "- `patent_id`: 보고서가 생성된 특허 ID (예: `10-2142205`)\n\n"
        "MinIO에서 `report.json`을 탐색하여 `pre-{patent_id}` 컬렉션에 임베딩·저장합니다.\n"
        "저장 후 `/cases/{patent_id}/chat` 으로 바로 챗봇 사용이 가능합니다.\n\n"
        "벡터스토어는 blue-green 없이 단순 upsert 방식으로 누적 생성됩니다."
    ),
)
def post_report_complete_webhook(body: PreEvalReportCompleteRequest) -> dict:
    return handle_report_complete_webhook(body.patent_id.strip())


@router.post(
    "/cases/{case_id}/chat",
    response_model=PublicChatResponse,
    summary="[외부] 사전평가 챗봇 답변",
    description=(
        "사전평가 케이스 `pre-{case_id}` 벡터스토어를 기반으로 질문에 답변합니다.\n\n"
        "웹훅(`/webhook/report-complete`)으로 인덱싱이 완료된 후 사용 가능합니다.\n\n"
        "요청 필드:\n"
        "- `chat_history` (선택): 이전 대화 목록\n"
        "- `question` (필수): 질문\n"
        "- `user_id` (선택): 사용자 식별자\n"
        "- `top_k` (선택, 기본 8): 검색 청크 수"
    ),
)
def post_pre_application_chat(case_id: str, body: PreEvalChatRequest) -> dict:
    return run_pre_eval_chat_agent(
        body.question,
        case_id=case_id,
        user_id=body.user_id,
        chat_history=_chat_history_payload(body.chat_history),
        top_k=body.top_k,
    )


@router.get(
    "/vectorstore/status",
    summary="[외부] 사전 출원 특허 벡터스토어 전체 목록 및 상태",
    description=(
        "`pre-{patent_id}` 패턴으로 생성된 모든 사전 출원 특허 벡터스토어의 상태를 반환합니다.\n\n"
        "각 항목에는 컬렉션 이름, 문서 수, 인덱싱 시각이 포함됩니다."
    ),
)
def get_pre_application_vectorstore_status() -> dict:
    items = list_pre_application_vectorstores()
    return {"count": len(items), "items": items}


@router.get(
    "/vectorstore/{patent_id}/status",
    summary="[외부] 사전 출원 특허 개별 벡터스토어 상태",
    description="특정 `patent_id`에 대한 `pre-{patent_id}` 컬렉션의 상세 상태를 반환합니다.",
)
def get_pre_application_single_vectorstore_status(patent_id: str) -> dict:
    return pre_application_vectorstore_status(patent_id)


@router.post(
    "/cases/{case_id}/search",
    summary="[외부] 사전 출원 특허 벡터스토어 직접 검색",
    description="`pre-{case_id}` 컬렉션에서 쿼리와 유사한 청크를 반환합니다.",
)
def post_pre_application_search(case_id: str, body: dict[str, Any]) -> dict:
    query = str(body.get("query") or "")
    top_k = int(body.get("top_k") or 8)
    return search_pre_application_vectorstore(case_id, query, top_k=top_k)


# ── 🔧 내부 운영 API — 레거시 사전평가 케이스 (내부용) ───────────────────

@router.post(
    "/evaluate",
    summary="사전평가 실행 및 케이스 생성 (내부 운영용)",
    include_in_schema=False,
)
def post_evaluate(body: dict[str, Any]) -> dict:
    """내부 운영용: 직접 평가 로직을 실행합니다.
    외부 연동은 /webhook/report-complete 를 사용하세요.
    """
    enable_llm = bool(body.pop("enable_llm", True))
    run_web_search = bool(body.pop("run_web_search", True))
    return create_pre_eval_case(body, enable_llm=enable_llm, run_web_search=run_web_search)


@router.get("/cases", summary="사전평가 케이스 목록", include_in_schema=False)
def get_cases() -> dict:
    return {"items": list_pre_eval_cases()}


@router.get("/cases/{case_id}", summary="사전평가 케이스 상태 및 vectorstore 정보", include_in_schema=False)
def get_case(case_id: str) -> dict:
    return pre_eval_case_status(case_id)


@router.get("/cases/{case_id}/report", summary="사전평가 보고서 원본 JSON", include_in_schema=False)
def get_case_report(case_id: str) -> dict:
    return get_pre_eval_report(case_id)


@router.post(
    "/cases/{case_id}/index/refresh",
    summary="사전평가 케이스 vectorstore 재빌드",
    include_in_schema=False,
)
def post_case_index_refresh(case_id: str) -> dict:
    return refresh_pre_eval_case_index(case_id)


@router.post("/cases/{case_id}/chat/legacy", summary="레거시 사전평가 케이스 챗봇", include_in_schema=False)
def post_case_chat_legacy(case_id: str, body: dict[str, Any]) -> dict:
    return run_pre_eval_chat_agent(
        str(body.get("question") or ""),
        case_id=case_id,
        user_id=body.get("user_id"),
        chat_history=list(body.get("chat_history") or []),
        top_k=int(body.get("top_k") or 8),
    )


@router.post("/cases/{case_id}/search/legacy", summary="레거시 사전평가 케이스 vectorstore 직접 검색", include_in_schema=False)
def post_case_search_legacy(case_id: str, body: dict[str, Any]) -> dict:
    query = str(body.get("query") or "")
    top_k = int(body.get("top_k") or 8)
    return search_pre_eval_vectorstore(case_id, query, top_k=top_k)


@router.get("/graph/mermaid", summary="사전평가 챗봇 LangGraph Mermaid", include_in_schema=False)
def get_graph_mermaid() -> dict:
    return {"format": "mermaid", "diagram": pre_eval_graph_mermaid()}
