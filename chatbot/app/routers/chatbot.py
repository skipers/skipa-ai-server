"""Swagger-visible chatbot inspection and query endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from ..agents.application_graph import application_graph_mermaid, run_application_agent
from ..agents.graph import chat_graph_mermaid, run_chat_agent
from ..agents.ingestion_graph import ingestion_graph_mermaid, run_ingestion_graph
from ..agents.wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid
from ..application_data import (
    application_download_report,
    application_external_status,
    application_index_status,
    create_application_feedback_report,
    create_failed_patent_case,
    download_application_sources,
    failed_patent_case_index_status,
    generate_failed_patent_case_report,
    list_failed_patent_cases,
    preprocess_application_pack,
    refresh_application_index,
    refresh_failed_patent_case_index,
    save_failed_patent_case_report,
)
from ..config import PATENT_APPLICATION_ROOT
from ..config import (
    ANSWER_LLM_TIMEOUT,
    ANSWER_MODEL,
    ANSWER_PROVIDER,
    EMBEDDING_MODEL,
    GEN_MODEL,
    INTENT_LLM_TIMEOUT,
    INTENT_MODEL,
    INTENT_PROVIDER,
    PUBLIC_FILE_BASE_URL,
    TOP_K,
)
from ..rag.legacy_adapter import (
    legacy_engine_status,
    patent_summary_cards,
    render_page_image,
    write_feedback,
)
from ..minio_data import minio_patent_status, sync_patent_data_from_minio
from ..qdrant_store import collection_info, qdrant_status, wiki_collection
from ..schemas import (
    AnswerResponse,
    AuditApplyRequest,
    BusinessReindexRequest,
    ChatRequest,
    FeedbackRequest,
    PatentApplicationChatRequest,
    PatentApplicationDownloadRequest,
    PatentApplicationFailedCaseCreateRequest,
    PatentApplicationFailedCaseReportGenerateRequest,
    PatentApplicationFailedCaseReportSaveRequest,
    PatentApplicationFeedbackRequest,
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
from ..vectorstore import nightly_reindex_all, normalize_wiki_context_files, refresh_vectorstores, run_audit, vectorstore_status
from ..wiki.topics import (
    TOPIC_SLUGS,
    all_active_topic_slugs,
    get_patent_topic,
    reclassify_all_patents,
    topic_approved_md,
    topic_draft_dir,
)


router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
patent_chat_router = APIRouter(prefix="/api/v1/patent-chat", tags=["patent-chat"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["patent-chat"], include_in_schema=False)
legacy_rag_router = APIRouter(prefix="/rag", tags=["patent-chat"], include_in_schema=False)
agent_router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
wiki_router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])
application_router = APIRouter(prefix="/api/v1/application", tags=["application"])


@router.get("/config", summary="챗봇 설정과 데이터 루트 확인")
def get_config() -> dict:
    rag_engine = legacy_engine_status()
    return {
        **data_overview(),
        "public_file_base_url": PUBLIC_FILE_BASE_URL,
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GEN_MODEL,
        "intent_provider": INTENT_PROVIDER,
        "intent_model": INTENT_MODEL,
        "answer_provider": ANSWER_PROVIDER,
        "answer_model": ANSWER_MODEL,
        "intent_llm_timeout": INTENT_LLM_TIMEOUT,
        "answer_llm_timeout": ANSWER_LLM_TIMEOUT,
        "default_top_k": TOP_K,
        "rag_engine": rag_engine,
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
        "minio": minio_patent_status(),
        "qdrant": qdrant_status(),
    }


@router.get("/qdrant/status", summary="Qdrant 연결 및 dashboard 상태")
def get_qdrant_status() -> dict:
    return qdrant_status()


@router.get("/minio/status", summary="MinIO patent 데이터 연결 상태")
def get_minio_status() -> dict:
    return minio_patent_status()


@router.post("/minio/sync", summary="MinIO s3://bucket/patent/ 데이터를 로컬 공유 patent cache로 동기화")
def post_minio_sync(rebuild_index: bool = Query(True, description="동기화 후 공유 특허 vectorstore를 재생성할지 여부")) -> dict:
    return sync_patent_data_from_minio(rebuild_index=rebuild_index)


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
    elif request.mode == "nightly_reindex":
        result["nightly_reindex"] = nightly_reindex_all()
    elif request.mode == "shared_index":
        from ..shared_data import build_shared_vectorstore
        result["shared_index"] = build_shared_vectorstore()
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


@patent_chat_router.post("/query", response_model=SearchResponse, summary="특허 챗봇 근거 검색")
@rag_router.post("/query", response_model=SearchResponse, summary="RAG 질의 alias")
def rag_query(request: SearchRequest) -> dict:
    return post_search(request)


@agent_router.post("/query", response_model=SearchResponse, summary="Agent 질의 alias")
def agent_query(request: SearchRequest) -> dict:
    return post_search(request)


@patent_chat_router.post("/answer", response_model=AnswerResponse, summary="특허 챗봇 답변 생성")
@rag_router.post("/answer", response_model=AnswerResponse, summary="RAG 답변 alias")
def rag_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@agent_router.post("/answer", response_model=AnswerResponse, summary="Agent 답변 alias")
def agent_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@patent_chat_router.get("/chat/mermaid", summary="특허 챗봇 LangGraph 답변 workflow Mermaid")
@rag_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
@agent_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
def get_chat_graph_mermaid() -> dict:
    return {"format": "mermaid", "diagram": chat_graph_mermaid()}


@patent_chat_router.get("/engine/status", summary="Hybrid Retrieval 엔진 상태")
@rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
@legacy_rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
def get_rag_engine_status() -> dict:
    return legacy_engine_status()


@patent_chat_router.get("/patents", summary="특허 챗봇 특허 목록")
@rag_router.get("/patents", summary="통합 RAG 특허 목록")
@legacy_rag_router.get("/patents", summary="특허 챗봇 호환 특허 목록")
def rag_patents() -> dict:
    patents = list_patents()
    return {"items": patents, "count": len(patents), "engine": legacy_engine_status()}


@patent_chat_router.get("/patent-summary-cards", summary="특허 요약 카드")
@rag_router.get("/patent-summary-cards", summary="통합 RAG 특허 요약 카드")
@legacy_rag_router.get("/patent-summary-cards", summary="특허 챗봇 호환 특허 요약 카드")
def rag_patent_summary_cards() -> dict:
    return patent_summary_cards()


@patent_chat_router.post("/chat", response_model=AnswerResponse, summary="특허별 챗봇 답변")
@rag_router.post("/chat", response_model=AnswerResponse, summary="통합 RAG 특허별 챗봇 답변")
@legacy_rag_router.post("/chat", response_model=AnswerResponse, summary="특허 챗봇 호환 답변")
def rag_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=request.patent_id,
        user_id=request.user_id,
        chat_history=request.chat_history,
        context_patent_id=request.context_patent_id,
    )


@patent_chat_router.post("/global/chat", response_model=AnswerResponse, summary="전체 특허 챗봇 답변")
@rag_router.post("/global/chat", response_model=AnswerResponse, summary="통합 RAG 전체 특허 챗봇 답변")
@legacy_rag_router.post("/global/chat", response_model=AnswerResponse, summary="전체 특허 챗봇 호환 답변")
def rag_global_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=None,
        user_id=request.user_id,
        chat_history=request.chat_history,
        context_patent_id=request.context_patent_id,
    )


@patent_chat_router.post("/reindex", summary="특허별 검색 인덱스 재생성")
@rag_router.post("/reindex", summary="특허별 Qdrant 인덱스 재생성")
@legacy_rag_router.post("/reindex", summary="특허별 Qdrant 인덱스 재생성")
def rag_reindex(request: ReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="patent",
        patent_id=request.patent_id,
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.post("/global/reindex", summary="전체 특허 검색 인덱스 재생성")
@rag_router.post("/global/reindex", summary="전체 특허 global Qdrant 인덱스 재생성")
@legacy_rag_router.post("/global/reindex", summary="전체 특허 global Qdrant 인덱스 재생성")
def rag_global_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="global",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.post("/business/reindex", summary="업무/공통 검색 인덱스 재생성")
@rag_router.post("/business/reindex", summary="업무/공통 Qdrant 인덱스 재생성")
@legacy_rag_router.post("/business/reindex", summary="업무/공통 Qdrant 인덱스 재생성")
def rag_business_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="business",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.get("/ingestion/mermaid", summary="전처리/재색인 LangGraph Mermaid")
@rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
@legacy_rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
def get_ingestion_mermaid() -> dict:
    return {"format": "mermaid", "diagram": ingestion_graph_mermaid()}


@patent_chat_router.post("/feedback", summary="챗봇 답변 피드백 저장")
@rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
@legacy_rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
def rag_feedback(request: FeedbackRequest) -> dict:
    return write_feedback(request.model_dump())


@patent_chat_router.get("/page-image", summary="특허 PDF page image 렌더링")
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


@wiki_router.get("/topics", summary="분야별 wiki vectorstore 목록 및 상태")
def get_wiki_topics() -> dict:
    """분야(topic) 목록과 각 분야의 approved_context.md 존재 여부, vectorstore 문서 수를 반환합니다."""

    active = all_active_topic_slugs()
    topics = []
    for slug in TOPIC_SLUGS:
        qdrant = collection_info(wiki_collection(slug))
        approved = topic_approved_md(slug)
        draft_dir = topic_draft_dir(slug)
        draft_count = sum(1 for f in draft_dir.rglob("*.md") if f.is_file()) if draft_dir.exists() else 0
        topics.append(
            {
                "topic": slug,
                "has_data": slug in active,
                "approved_md_exists": approved.exists(),
                "draft_count": draft_count,
                "backend": "qdrant",
                "collection": wiki_collection(slug),
                "vectorstore_exists": bool(qdrant.get("exists")),
                "document_count": qdrant.get("points_count", 0),
                "refreshed_at": None,
                "qdrant": qdrant,
                "paths": {
                    "web_search_data": str(draft_dir),
                    "approved_md": str(approved),
                    "vectorstore": wiki_collection(slug),
                },
            }
        )
    return {"topics": topics, "active_count": len(active), "predefined_slugs": TOPIC_SLUGS}


@wiki_router.get("/topics/{topic_slug}", summary="특정 분야 wiki 상태 조회")
def get_wiki_topic_detail(topic_slug: str) -> dict:
    """특정 분야의 approved_context.md 내용 미리보기와 최근 draft 목록을 반환합니다."""
    from fastapi import HTTPException

    if "/" in topic_slug or "\\" in topic_slug:
        raise HTTPException(status_code=400, detail="잘못된 topic_slug입니다.")

    qdrant = collection_info(wiki_collection(topic_slug))
    approved = topic_approved_md(topic_slug)
    draft_dir = topic_draft_dir(topic_slug)
    drafts = []
    if draft_dir.exists():
        for f in sorted(draft_dir.rglob("*.md"), reverse=True)[:10]:
            drafts.append({"name": f.name, "size_bytes": f.stat().st_size, "path": str(f)})
    preview = ""
    if approved.exists():
        text = approved.read_text(encoding="utf-8", errors="ignore")
        preview = text[:2000] + ("…" if len(text) > 2000 else "")
    return {
        "topic": topic_slug,
        "approved_md_exists": approved.exists(),
        "approved_md_preview": preview,
        "approved_md_path": str(approved),
        "recent_drafts": drafts,
        "backend": "qdrant",
        "collection": wiki_collection(topic_slug),
        "vectorstore_exists": bool(qdrant.get("exists")),
        "document_count": qdrant.get("points_count", 0),
        "refreshed_at": None,
        "qdrant": qdrant,
    }


@wiki_router.post("/topics/refresh", summary="분야별 wiki Qdrant vectorstore 전체 재빌드")
def post_wiki_topics_refresh() -> dict:
    """모든 분야의 wiki vectorstore를 Qdrant collection으로 재빌드합니다. 자정 nightly_reindex에 포함됩니다."""
    result = refresh_vectorstores(use_reviewed=True)
    return {
        "status": "refreshed",
        "topic_wiki_vectorstores": result.get("topic_wiki_vectorstores", []),
        "global_wiki_vectorstore": result.get("global_wiki_vectorstore", {}),
        "refreshed_at": result.get("refreshed_at"),
    }


@wiki_router.post("/topics/reclassify", summary="전체 특허 분야 재분류 (새 폴더 자동 생성)")
def post_reclassify_topics() -> dict:
    """모든 특허 제목을 다시 분석해 분야를 재할당합니다.
    기존 predefined 분야에 들어가지 못하면 제목에서 새 분야 slug를 추출해 WIKI_ROOT에 폴더를 만듭니다.
    """
    result = reclassify_all_patents()
    from collections import Counter
    counts = dict(Counter(result.values()))
    return {"status": "reclassified", "patent_count": len(result), "topic_counts": counts, "mapping": result}


@wiki_router.get("/topics/{topic_slug}/patent", summary="특허 → 분야 매핑 조회")
def get_patent_topic_mapping(patent_id: str = Query(..., description="매핑을 확인할 특허 ID")) -> dict:
    """patent_id가 어떤 분야에 속하는지 반환합니다."""
    topic = get_patent_topic(patent_id)
    return {
        "patent_id": patent_id,
        "topic": topic,
        "vectorstore_path": wiki_collection(topic),
        "collection": wiki_collection(topic),
        "approved_md_path": str(topic_approved_md(topic)),
    }


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


@application_router.post("/feedback/create", summary="의견서/거절사유/기존 평가 보고서를 연결한 출원 피드백 리포트 생성")
def post_application_feedback_create(request: PatentApplicationFeedbackRequest) -> dict:
    return create_application_feedback_report(**request.model_dump())


@application_router.post("/report/generate", summary="호환용 전역 출원 피드백 리포트 생성")
def post_application_report_generate(request: PatentApplicationFeedbackRequest) -> dict:
    payload = request.model_dump()
    if payload.get("title") == "특허 출원 실패/거절 대응 피드백":
        payload["title"] = "특허 출원/실패 분석 보고서"
    return create_application_feedback_report(**payload)


@application_router.post("/feedback/upload", summary="의견서 PDF/문서 업로드 후 출원 피드백 HTML 생성 및 vectorstore 갱신")
def post_application_feedback_upload(
    file: UploadFile = File(..., description="의견서, 거절이유 통지서, 출원 실패 분석 문서 PDF/HWP/HTML/TXT"),
    title: str = Form("특허 출원 실패/거절 대응 피드백"),
    patent_id: str | None = Form(None),
    source_report_path: str | None = Form(None),
    reviewer: str | None = Form(None),
    notes: str | None = Form(None),
    refresh_index: bool = Form(True),
) -> dict:
    upload_dir = PATENT_APPLICATION_ROOT / "feedback" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "opinion.pdf").name
    upload_path = upload_dir / safe_name
    upload_path.write_bytes(file.file.read())
    return create_application_feedback_report(
        title=title,
        patent_id=patent_id,
        opinion_file_path=str(upload_path),
        source_report_path=source_report_path,
        reviewer=reviewer,
        notes=notes,
        refresh_index=refresh_index,
    )


@application_router.get("/failed-patents", summary="출원 도우미 실패특허 케이스 목록")
def get_application_failed_patents() -> dict:
    return list_failed_patent_cases()


@application_router.get("/failed-patents/{case_id}", summary="실패특허 케이스 파일/index 상태")
def get_application_failed_patent(case_id: str) -> dict:
    return failed_patent_case_index_status(case_id)


@application_router.post("/failed-patents/create", summary="서버 로컬 PDF 경로로 실패특허 케이스 생성")
def post_application_failed_patent_create(request: PatentApplicationFailedCaseCreateRequest) -> dict:
    return create_failed_patent_case(
        case_id=request.case_id,
        title=request.title,
        original_pdf_path=request.original_pdf_path,
        rejection_reason_text=request.rejection_reason_text,
        rejection_file_path=request.rejection_file_path,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_index=request.refresh_index,
    )


@application_router.post("/failed-patents/upload", summary="실패특허 원본 PDF와 선택 사유서를 업로드하고 케이스 전용 vectorstore 생성")
def post_application_failed_patent_upload(
    original_pdf: UploadFile = File(..., description="채팅을 시작하기 위해 반드시 필요한 실패특허 원본 PDF"),
    rejection_file: UploadFile | None = File(None, description="선택: 거절의견서/사유서 PDF/문서"),
    case_id: str | None = Form(None),
    title: str | None = Form(None),
    rejection_reason_text: str | None = Form(None),
    reviewer: str | None = Form(None),
    notes: str | None = Form(None),
    refresh_index: bool = Form(True),
) -> dict:
    if not (original_pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="original_pdf는 실패특허 원본 PDF 파일이어야 합니다.")
    rejection_bytes = rejection_file.file.read() if rejection_file is not None else None
    rejection_name = rejection_file.filename if rejection_file is not None else None
    return create_failed_patent_case(
        case_id=case_id,
        title=title or original_pdf.filename,
        original_pdf_bytes=original_pdf.file.read(),
        original_pdf_filename=original_pdf.filename,
        rejection_reason_text=rejection_reason_text,
        rejection_file_bytes=rejection_bytes,
        rejection_file_filename=rejection_name,
        reviewer=reviewer,
        notes=notes,
        refresh_index=refresh_index,
    )


@application_router.post("/failed-patents/{case_id}/index/refresh", summary="선택 실패특허 1건의 전용 vectorstore만 갱신")
def post_application_failed_patent_index_refresh(case_id: str) -> dict:
    return refresh_failed_patent_case_index(case_id)


@application_router.post("/failed-patents/{case_id}/report/save", summary="특허 재평가 API 결과를 해당 실패특허 폴더에 저장하고 전용 vectorstore 갱신")
def post_application_failed_patent_report_save(
    case_id: str,
    request: PatentApplicationFailedCaseReportSaveRequest,
) -> dict:
    return save_failed_patent_case_report(case_id, **request.model_dump())


@application_router.post("/failed-patents/{case_id}/report/generate", summary="보고서 생성 에이전트를 실행하고 해당 실패특허 폴더 reports에 저장")
def post_application_failed_patent_report_generate(
    case_id: str,
    request: PatentApplicationFailedCaseReportGenerateRequest,
) -> dict:
    payload = request.model_dump()
    refresh_index = bool(payload.pop("refresh_index", True))
    title = payload.pop("title", None)
    return generate_failed_patent_case_report(
        case_id,
        title=title,
        options=payload,
        refresh_index=refresh_index,
    )


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
        failed_patent_id=request.failed_patent_id,
        chat_history=request.chat_history,
        top_k=request.top_k,
        refresh_index=request.refresh_index,
    )


@application_router.post("/failed-patents/{case_id}/chat", response_model=AnswerResponse, summary="선택 실패특허 케이스 기준 출원 도우미 챗봇")
def post_application_failed_patent_chat(case_id: str, request: PatentApplicationChatRequest) -> dict:
    return run_application_agent(
        request.question,
        user_id=request.user_id,
        failed_patent_id=case_id,
        chat_history=request.chat_history,
        top_k=request.top_k,
        refresh_index=request.refresh_index,
    )


@application_router.get("/chat/mermaid", summary="특허 출원 도우미 LangGraph Mermaid")
def get_application_chat_mermaid() -> dict:
    return {"format": "mermaid", "diagram": application_graph_mermaid()}
