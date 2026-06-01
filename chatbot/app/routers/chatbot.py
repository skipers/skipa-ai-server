"""Swagger-visible chatbot inspection and query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..agents.graph import run_chat_agent
from ..agents.wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid
from ..config import EMBEDDING_MODEL, GEN_MODEL, PUBLIC_FILE_BASE_URL, TOP_K
from ..schemas import AnswerResponse, AuditApplyRequest, SearchRequest, SearchResponse, WikiAgentRunRequest
from ..store import (
    business_chunks,
    data_overview,
    latest_json,
    link_status,
    list_files,
    list_patents,
    patent_chunks,
    patent_detail,
    search_chunks,
    wiki_audit_report,
)
from ..vectorstore import vectorstore_status


router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
agent_router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
wiki_router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


@router.get("/config", summary="챗봇 설정과 데이터 루트 확인")
def get_config() -> dict:
    return {
        **data_overview(),
        "public_file_base_url": PUBLIC_FILE_BASE_URL,
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GEN_MODEL,
        "default_top_k": TOP_K,
    }


@router.get("/data-links", summary="chatbot/data symlink 상태 확인")
def get_data_links() -> dict:
    return link_status()


@router.get("/patents", summary="챗봇이 사용할 수 있는 특허 목록")
def get_patents() -> dict:
    patents = list_patents()
    return {"count": len(patents), "items": patents}


@router.get("/patents/{patent_id}", summary="특허별 원문/보고서/wiki/index 상태")
def get_patent(patent_id: str, include_files: bool = Query(True, description="특허 폴더 파일 목록 포함 여부")) -> dict:
    return patent_detail(patent_id, include_files=include_files)


@router.get("/patents/{patent_id}/files", summary="특허 폴더 파일 목록")
def get_patent_files(patent_id: str, limit: int = Query(300, ge=1, le=1000)) -> dict:
    files = list_files(patent_id, limit=limit)
    return {"patent_id": patent_id, "count": len(files), "items": files}


@router.get("/patents/{patent_id}/input/latest", summary="최신 특허 input JSON")
def get_latest_input(patent_id: str) -> dict:
    return latest_json(patent_id, "input")


@router.get("/patents/{patent_id}/report/latest", summary="최신 보고서 JSON")
def get_latest_report(patent_id: str) -> dict:
    return latest_json(patent_id, "report")


@router.get("/patents/{patent_id}/chunks", summary="특허별 chunk 조회")
def get_chunks(
    patent_id: str,
    chunk_file: str = Query("all", description="all, original, report, original_visual, report_visual"),
    source_type: list[str] | None = Query(None, description="ORIGINAL_PDF, REPORT_PDF 등"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    return patent_chunks(
        patent_id,
        chunk_file=chunk_file,
        offset=offset,
        limit=limit,
        source_types=set(source_type or []) or None,
    )


@router.get("/business/chunks", summary="공통 business RAG chunk 조회")
def get_business_chunks(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)) -> dict:
    return business_chunks(offset=offset, limit=limit)


@router.get("/vectorstore/status", summary="챗봇 vectorstore 갱신 상태")
def get_vectorstore_status() -> dict:
    return vectorstore_status()


@router.post("/vectorstore/refresh", summary="전체 특허/사업 데이터 vectorstore 재생성")
def post_vectorstore_refresh() -> dict:
    result = run_wiki_audit_graph(mode="refresh")
    return result.get("refresh_result", result)


@router.post("/search", response_model=SearchResponse, summary="챗봇 RAG 검색 확인")
def post_search(request: SearchRequest) -> dict:
    return search_chunks(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )


@router.post("/query", response_model=SearchResponse, summary="챗봇 질의 API 확인")
def post_query(request: SearchRequest) -> dict:
    return post_search(request)


@router.post("/answer", response_model=AnswerResponse, summary="챗봇 답변 API")
def post_answer(request: SearchRequest) -> dict:
    return run_chat_agent(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )


@rag_router.post("/query", response_model=SearchResponse, summary="RAG 질의 alias")
def rag_query(request: SearchRequest) -> dict:
    return post_search(request)


@agent_router.post("/query", response_model=SearchResponse, summary="Agent 질의 alias")
def agent_query(request: SearchRequest) -> dict:
    return post_search(request)


@rag_router.post("/answer", response_model=AnswerResponse, summary="RAG 답변 alias")
def rag_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@agent_router.post("/answer", response_model=AnswerResponse, summary="Agent 답변 alias")
def agent_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@router.get("/wiki-audit/report", summary="wiki 감사 리포트")
@wiki_router.get("/audit-report", summary="wiki 감사 리포트")
def get_wiki_audit_report() -> dict:
    return wiki_audit_report()


@router.post("/wiki-audit/run", summary="wiki/챗봇 데이터 감사 실행 및 나쁜 데이터 후보 추출")
@wiki_router.post("/audit", summary="wiki/챗봇 데이터 감사 실행 및 나쁜 데이터 후보 추출")
def post_wiki_audit(refresh_vectorstore: bool = Query(False, description="사람 검토 전 raw vectorstore 강제 갱신 여부")) -> dict:
    result = run_wiki_audit_graph(mode="audit", refresh_vectorstore=refresh_vectorstore)
    audit = result.get("audit", result)
    if isinstance(audit, dict):
        audit["agent_trace"] = result.get("trace", [])
    return audit


@router.get("/wiki-audit/review", summary="사람 검토용 감사 Markdown 조회")
@wiki_router.get("/audit-review", summary="사람 검토용 감사 Markdown 조회")
def get_wiki_audit_review(audit_id: str | None = Query(None, description="조회할 audit_id. 비우면 최신 감사")) -> dict:
    result = run_wiki_audit_graph(mode="review", audit_id=audit_id)
    review = result.get("review", result)
    if isinstance(review, dict):
        review["agent_trace"] = result.get("trace", [])
    return review


@router.post("/wiki-audit/apply", summary="사람 검토 결과 적용, 승인 Markdown 저장, vectorstore 갱신")
@wiki_router.post("/audit-apply", summary="사람 검토 결과 적용, 승인 Markdown 저장, vectorstore 갱신")
def post_wiki_audit_apply(request: AuditApplyRequest) -> dict:
    result = run_wiki_audit_graph(
        mode="apply",
        audit_id=request.audit_id,
        exclude_finding_ids=request.exclude_finding_ids,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_vectorstore=request.refresh_vectorstore,
    )
    apply_result = result.get("apply_result", result)
    if isinstance(apply_result, dict):
        apply_result["agent_trace"] = result.get("trace", [])
    return apply_result


@wiki_router.post("/agent/run", summary="Wiki LangGraph agent 직접 실행")
def post_wiki_agent_run(request: WikiAgentRunRequest) -> dict:
    return run_wiki_audit_graph(
        mode=request.mode,
        audit_id=request.audit_id,
        exclude_finding_ids=request.exclude_finding_ids,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_vectorstore=request.refresh_vectorstore,
    )


@wiki_router.get("/agent/mermaid", summary="Wiki LangGraph agent Mermaid")
def get_wiki_agent_mermaid() -> dict:
    return {"format": "mermaid", "diagram": wiki_audit_graph_mermaid()}
