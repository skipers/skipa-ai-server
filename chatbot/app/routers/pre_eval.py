"""Pre-application evaluation API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ..agents.pre_eval_graph import pre_eval_graph_mermaid, run_pre_eval_chat_agent
from ..pre_eval_data import (
    create_pre_eval_case,
    get_pre_eval_report,
    list_pre_eval_cases,
    pre_eval_case_status,
    refresh_pre_eval_case_index,
    search_pre_eval_vectorstore,
)


router = APIRouter(prefix="/api/v1/pre-eval", tags=["pre-eval"])


@router.post("/evaluate", summary="출원 전 사전평가 실행 및 케이스 생성")
def post_evaluate(body: dict[str, Any]) -> dict:
    """특허명·기술설명·청구항 등을 받아 사전평가를 실행하고 결과를 케이스 폴더에 저장합니다.
    평가 완료 후 케이스 전용 vectorstore가 자동 생성되어 바로 채팅을 시작할 수 있습니다.

    요청 필드:
    - patentName (필수): 특허명
    - technologyDescription (필수): 기술 설명
    - claims (선택): 청구항 목록
    - relatedBusiness (선택): 관련 사업
    - targetCountries (선택): 출원 예정 국가 목록
    - enable_llm (선택, 기본 true): LLM 종합 코멘트 생성 여부
    - run_web_search (선택, 기본 true): wiki 웹 검색 실행 여부
    """
    enable_llm = bool(body.pop("enable_llm", True))
    run_web_search = bool(body.pop("run_web_search", True))
    return create_pre_eval_case(body, enable_llm=enable_llm, run_web_search=run_web_search)


@router.get("/cases", summary="사전평가 케이스 목록")
def get_cases() -> dict:
    return {"items": list_pre_eval_cases()}


@router.get("/cases/{case_id}", summary="사전평가 케이스 상태 및 vectorstore 정보")
def get_case(case_id: str) -> dict:
    return pre_eval_case_status(case_id)


@router.get("/cases/{case_id}/report", summary="사전평가 보고서 원본 JSON")
def get_case_report(case_id: str) -> dict:
    return get_pre_eval_report(case_id)


@router.post(
    "/cases/{case_id}/index/refresh",
    summary="사전평가 케이스 vectorstore 재빌드",
    include_in_schema=False,
)
def post_case_index_refresh(case_id: str) -> dict:
    return refresh_pre_eval_case_index(case_id)


@router.post("/cases/{case_id}/chat", summary="사전평가 보고서 기반 챗봇")
def post_case_chat(case_id: str, body: dict[str, Any]) -> dict:
    """사전평가 케이스 보고서 전용 vectorstore를 검색해 질문에 답변합니다.
    챗봇 성능은 특허 챗봇과 동일합니다 (의도 분류 + wiki gate + web 검색 보강).
    """
    return run_pre_eval_chat_agent(
        str(body.get("question") or ""),
        case_id=case_id,
        user_id=body.get("user_id"),
        chat_history=list(body.get("chat_history") or []),
        top_k=int(body.get("top_k") or 8),
    )


@router.post("/cases/{case_id}/search", summary="사전평가 케이스 vectorstore 직접 검색")
def post_case_search(
    case_id: str,
    body: dict[str, Any],
) -> dict:
    query = str(body.get("query") or "")
    top_k = int(body.get("top_k") or 8)
    return search_pre_eval_vectorstore(case_id, query, top_k=top_k)


@router.get("/graph/mermaid", summary="사전평가 챗봇 LangGraph Mermaid", include_in_schema=False)
def get_graph_mermaid() -> dict:
    return {"format": "mermaid", "diagram": pre_eval_graph_mermaid()}
