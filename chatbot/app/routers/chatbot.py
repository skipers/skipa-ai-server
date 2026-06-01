"""Swagger-visible chatbot inspection and query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import EMBEDDING_MODEL, GEN_MODEL, PUBLIC_FILE_BASE_URL, TOP_K
from ..schemas import SearchRequest, SearchResponse
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
from ..vectorstore import audit_and_refresh_vectorstores, refresh_vectorstores, vectorstore_status


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
    return refresh_vectorstores()


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


@rag_router.post("/query", response_model=SearchResponse, summary="RAG 질의 alias")
def rag_query(request: SearchRequest) -> dict:
    return post_search(request)


@agent_router.post("/query", response_model=SearchResponse, summary="Agent 질의 alias")
def agent_query(request: SearchRequest) -> dict:
    return post_search(request)


@router.get("/wiki-audit/report", summary="wiki 감사 리포트")
@wiki_router.get("/audit-report", summary="wiki 감사 리포트")
def get_wiki_audit_report() -> dict:
    return wiki_audit_report()


@router.post("/wiki-audit/run", summary="wiki/챗봇 데이터 감사 실행 및 vectorstore 갱신")
@wiki_router.post("/audit", summary="wiki/챗봇 데이터 감사 실행 및 vectorstore 갱신")
def post_wiki_audit(refresh_vectorstore: bool = Query(True, description="감사 후 전체 vectorstore 재생성 여부")) -> dict:
    return audit_and_refresh_vectorstores(refresh_vectorstore=refresh_vectorstore)
