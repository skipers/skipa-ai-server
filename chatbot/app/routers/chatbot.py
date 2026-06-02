"""Swagger-visible chatbot inspection and query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..agents.application_graph import application_graph_mermaid, run_application_agent
from ..agents.graph import chat_graph_mermaid, run_chat_agent
from ..agents.ingestion_graph import ingestion_graph_mermaid, run_ingestion_graph
from ..agents.wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid
from ..application_data import (
    application_download_report,
    application_external_status,
    application_index_status,
    download_application_sources,
    preprocess_application_pack,
    refresh_application_index,
)
from ..config import (
    ANSWER_LLM_TIMEOUT,
    ANSWER_MODEL,
    EMBEDDING_MODEL,
    GEN_MODEL,
    INTENT_LLM_TIMEOUT,
    INTENT_MODEL,
    PUBLIC_FILE_BASE_URL,
    TOP_K,
)
from ..rag.legacy_adapter import (
    legacy_engine_status,
    patent_summary_cards,
    render_page_image,
    write_feedback,
)
from ..schemas import (
    AnswerResponse,
    AuditApplyRequest,
    BusinessReindexRequest,
    ChatRequest,
    FeedbackRequest,
    PatentApplicationChatRequest,
    PatentApplicationDownloadRequest,
    PatentApplicationPreprocessRequest,
    PreprocessRunRequest,
    ReindexRequest,
    SearchRequest,
    SearchResponse,
    WikiAgentRunRequest,
)
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
from ..vectorstore import normalize_wiki_context_files, refresh_vectorstores, run_audit, vectorstore_status


router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
legacy_rag_router = APIRouter(prefix="/rag", tags=["legacy-rag"])
agent_router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
wiki_router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])
application_router = APIRouter(prefix="/api/v1/application", tags=["application"])


@router.get("/config", summary="챗봇 설정과 데이터 루트 확인")
def get_config() -> dict:
    return {
        **data_overview(),
        "public_file_base_url": PUBLIC_FILE_BASE_URL,
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GEN_MODEL,
        "intent_model": INTENT_MODEL,
        "answer_model": ANSWER_MODEL,
        "intent_llm_timeout": INTENT_LLM_TIMEOUT,
        "answer_llm_timeout": ANSWER_LLM_TIMEOUT,
        "default_top_k": TOP_K,
        "legacy_rag_engine": legacy_engine_status(),
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


@router.get("/preprocess/status", summary="전처리/vectorstore/application 상태 통합 확인")
def get_preprocess_status() -> dict:
    return {
        "vectorstore": vectorstore_status(),
        "application": application_index_status(),
        "application_external": application_external_status(),
    }


@router.post("/preprocess/run", summary="전처리/wiki 정리/vectorstore refresh/application preprocess 실행")
def post_preprocess_run(request: PreprocessRunRequest) -> dict:
    result: dict[str, object] = {"mode": request.mode}
    if request.mode == "normalize_wiki":
        result["wiki_normalize"] = normalize_wiki_context_files()
    elif request.mode == "refresh_vectorstore":
        result["wiki_normalize"] = normalize_wiki_context_files() if request.use_reviewed else {"status": "skipped"}
        result["vectorstore"] = refresh_vectorstores(use_reviewed=request.use_reviewed)
    elif request.mode == "auto_audit_refresh":
        result["wiki_agent"] = run_wiki_audit_graph(mode="auto_refresh", refresh_vectorstore=True)
    elif request.mode == "audit":
        result["audit"] = run_audit()
    elif request.mode == "application_preprocess":
        result["application"] = preprocess_application_pack(refresh_index=request.refresh_application)
    elif request.mode == "all":
        result["wiki_normalize"] = normalize_wiki_context_files()
        result["vectorstore"] = refresh_vectorstores(use_reviewed=True)
        result["application"] = preprocess_application_pack(refresh_index=request.refresh_application)
    result["status"] = "ok"
    return result


@router.post("/vectorstore/refresh", summary="감사 자동 적용 후 전체 vectorstore 재생성")
def post_vectorstore_refresh(auto_audit: bool = Query(True, description="true면 주의/나쁜 데이터 자동 제외 후 승인본으로 refresh")) -> dict:
    result = run_wiki_audit_graph(mode="auto_refresh" if auto_audit else "refresh")
    return result.get("apply_result") or result.get("refresh_result", result)


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


@rag_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
@agent_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
def get_chat_graph_mermaid() -> dict:
    return {"format": "mermaid", "diagram": chat_graph_mermaid()}


@rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
@legacy_rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
def get_rag_engine_status() -> dict:
    return legacy_engine_status()


@rag_router.get("/patents", summary="레거시 RAG 호환 특허 목록")
@legacy_rag_router.get("/patents", summary="레거시 RAG 호환 특허 목록")
def rag_patents() -> dict:
    patents = list_patents()
    return {"items": patents, "count": len(patents), "engine": legacy_engine_status()}


@rag_router.get("/patent-summary-cards", summary="레거시 RAG 특허 요약 카드")
@legacy_rag_router.get("/patent-summary-cards", summary="레거시 RAG 특허 요약 카드")
def rag_patent_summary_cards() -> dict:
    return patent_summary_cards()


@rag_router.post("/chat", response_model=AnswerResponse, summary="rag.zip 호환 특허별 챗봇 답변")
@legacy_rag_router.post("/chat", response_model=AnswerResponse, summary="rag.zip 호환 특허별 챗봇 답변")
def rag_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=request.patent_id,
        user_id=request.user_id,
        chat_history=request.chat_history,
        context_patent_id=request.context_patent_id,
    )


@rag_router.post("/global/chat", response_model=AnswerResponse, summary="rag.zip 호환 전체 특허 챗봇 답변")
@legacy_rag_router.post("/global/chat", response_model=AnswerResponse, summary="rag.zip 호환 전체 특허 챗봇 답변")
def rag_global_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=None,
        user_id=request.user_id,
        chat_history=request.chat_history,
        context_patent_id=request.context_patent_id,
    )


@rag_router.post("/reindex", summary="특허별 전처리/RAG FAISS 재생성")
@legacy_rag_router.post("/reindex", summary="특허별 전처리/RAG FAISS 재생성")
def rag_reindex(request: ReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="patent",
        patent_id=request.patent_id,
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@rag_router.post("/global/reindex", summary="전체 특허 global FAISS 재생성")
@legacy_rag_router.post("/global/reindex", summary="전체 특허 global FAISS 재생성")
def rag_global_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="global",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@rag_router.post("/business/reindex", summary="업무/공통 business FAISS 재생성")
@legacy_rag_router.post("/business/reindex", summary="업무/공통 business FAISS 재생성")
def rag_business_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="business",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
@legacy_rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
def get_ingestion_mermaid() -> dict:
    return {"format": "mermaid", "diagram": ingestion_graph_mermaid()}


@rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
@legacy_rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
def rag_feedback(request: FeedbackRequest) -> dict:
    return write_feedback(request.model_dump())


@rag_router.get("/page-image", summary="특허 PDF page image 렌더링")
@legacy_rag_router.get("/page-image", summary="특허 PDF page image 렌더링")
def rag_page_image(patent_id: str, file_name: str = Query("original.pdf"), page_no: int = Query(1, ge=1)):
    return render_page_image(patent_id, file_name=file_name, page_no=page_no)


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


@router.post("/wiki-audit/auto-refresh", summary="자동 감사로 주의/나쁜 데이터 제외 후 승인 vectorstore 갱신")
@wiki_router.post("/audit-auto-refresh", summary="자동 감사로 주의/나쁜 데이터 제외 후 승인 vectorstore 갱신")
def post_wiki_audit_auto_refresh() -> dict:
    result = run_wiki_audit_graph(mode="auto_refresh", refresh_vectorstore=True)
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


@application_router.get("/status", summary="특허 출원 도우미 공식팩/index 상태")
def get_application_status() -> dict:
    return application_index_status()


@application_router.get("/external/status", summary="KIPRIS/KOSIS/Tavily 외부 보강 연결 상태")
def get_application_external_status() -> dict:
    return application_external_status()


@application_router.post("/preprocess", summary="특허 출원 공식팩 전처리 리포트 생성 및 vectorstore 갱신")
def post_application_preprocess(request: PatentApplicationPreprocessRequest) -> dict:
    return preprocess_application_pack(refresh_index=request.refresh_index)


@application_router.post("/sources/download", summary="특허 출원 공식 자료 다운로드/크롤링")
def post_application_sources_download(request: PatentApplicationDownloadRequest) -> dict:
    return download_application_sources(
        force=request.force,
        timeout=request.timeout,
        limit=request.limit,
        include_embedded=request.include_embedded,
    )


@application_router.get("/sources/download-report", summary="특허 출원 공식 자료 다운로드/크롤링 리포트")
def get_application_download_report() -> dict:
    return application_download_report()


@application_router.post("/index/refresh", summary="특허 출원 공식팩 vectorstore 갱신")
def post_application_index_refresh() -> dict:
    return refresh_application_index(force=True)


@application_router.post("/chat", response_model=AnswerResponse, summary="특허 출원 도우미 챗봇")
def post_application_chat(request: PatentApplicationChatRequest) -> dict:
    return run_application_agent(
        request.question,
        user_id=request.user_id,
        chat_history=request.chat_history,
        top_k=request.top_k,
        refresh_index=request.refresh_index,
    )


@application_router.get("/chat/mermaid", summary="특허 출원 도우미 LangGraph Mermaid")
def get_application_chat_mermaid() -> dict:
    return {"format": "mermaid", "diagram": application_graph_mermaid()}
