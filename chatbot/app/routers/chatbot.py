"""Swagger-visible chatbot inspection and query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..agents.graph import chat_graph_mermaid, run_chat_agent
from ..agents.ingestion_graph import ingestion_graph_mermaid, run_ingestion_graph
from ..agents.wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid
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
from ..visual_data import (
    build_missing_patent_visual_indexes,
    build_patent_visual_index,
    patent_visual_index_status,
    search_patent_visuals,
)
from ..schemas import (
    AnswerResponse,
    AuditApplyRequest,
    BusinessReindexRequest,
    ChatRequest,
    ChatHistoryItem,
    FeedbackRequest,
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
from ..vectorstore import (
    bluegreen_refresh_global,
    bluegreen_refresh_patent_only,
    bluegreen_reindex_status,
    full_rebuild_vectorstores,
    nightly_reindex_all,
    normalize_wiki_context_files,
    refresh_vectorstores,
    run_audit,
    vectorstore_status,
)
from ..wiki.topics import (
    TOPIC_SLUGS,
    all_active_topic_slugs,
    get_patent_topic,
    reclassify_all_patents,
    topic_approved_md,
    topic_draft_dir,
)


# ---------------------------------------------------------------------------
# 라우터 정의
#   patent_chat_router : /api/v1/patent-chat  → [주요] 특허 챗봇 API
#   wiki_router        : /api/v1/wiki         → Wiki 감사·분야 관리
#   router (chatbot)   : /api/v1/chatbot      → 운영·인프라 관리 API
#   agent_router       : /api/v1/agent        → patent-chat alias (내부 호환용)
#   rag_router         : /api/v1/rag          → Swagger 미노출 alias
#   legacy_rag_router  : /rag                 → Swagger 미노출 legacy alias
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])
patent_chat_router = APIRouter(prefix="/api/v1/patent-chat", tags=["patent-chat"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["patent-chat"], include_in_schema=False)
legacy_rag_router = APIRouter(prefix="/rag", tags=["patent-chat"], include_in_schema=False)
agent_router = APIRouter(prefix="/api/v1/agent", tags=["agent"], include_in_schema=False)
wiki_router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


def _chat_history_payload(items: list[ChatHistoryItem]) -> list[dict]:
    return [item.model_dump(exclude_none=True) for item in items]


# ── [chatbot] 시스템 설정 조회 ────────────────────────────────────────────

@router.get(
    "/config",
    summary="시스템 설정 및 데이터 루트 확인",
    description=(
        "현재 챗봇의 모델 설정(의도 분류 모델, 답변 생성 모델, 임베딩 모델), "
        "데이터 루트 경로, RAG 엔진 상태, MinIO/Qdrant 연결 정보를 반환합니다."
    ),
)
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


@router.get(
    "/data-links",
    summary="chatbot/data 심볼릭 링크 상태 확인",
    description="chatbot/data 하위 심볼릭 링크(mapped_patent_reports, business)의 연결 상태와 실제 경로를 반환합니다.",
)
def get_data_links() -> dict:
    return link_status()


# ── [chatbot] 특허 데이터 조회 ────────────────────────────────────────────

@router.get(
    "/patents",
    summary="특허 목록 조회",
    description=(
        "챗봇이 검색 가능한 전체 특허 목록을 반환합니다. "
        "mapped_patent_reports(로컬)와 data/patent(공유 데이터)를 합산합니다."
    ),
)
def get_patents() -> dict:
    patents = list_patents()
    return {"count": len(patents), "items": patents}


@router.get(
    "/patents/{patent_id}",
    summary="특허 상세 정보 조회",
    description=(
        "특정 특허의 원문 JSON, 보고서 JSON, Qdrant 인덱스 존재 여부, "
        "파일 목록, chunk 수를 반환합니다. 데이터 파이프라인 진단용입니다."
    ),
)
def get_patent(patent_id: str, include_files: bool = Query(True, description="특허 폴더 파일 목록 포함 여부")) -> dict:
    return patent_detail(patent_id, include_files=include_files)


@router.get(
    "/patents/{patent_id}/files",
    summary="특허 폴더 파일 목록",
    description="특정 특허 폴더 하위의 모든 파일 경로·크기·수정 시각을 반환합니다.",
)
def get_patent_files(patent_id: str, limit: int = Query(300, ge=1, le=1000)) -> dict:
    files = list_files(patent_id, limit=limit)
    return {"patent_id": patent_id, "count": len(files), "items": files}


@router.get(
    "/patents/{patent_id}/input/latest",
    summary="특허 최신 입력 JSON 조회 (parsed.json)",
    description="해당 특허의 original/input/latest.json 또는 parsed.json을 반환합니다. 원문 메타데이터·청구항·명세서가 포함됩니다.",
)
def get_latest_input(patent_id: str) -> dict:
    return latest_json(patent_id, "input")


@router.get(
    "/patents/{patent_id}/report/latest",
    summary="특허 최신 평가 보고서 JSON 조회 (report.json)",
    description="해당 특허의 reports/json/latest.json 또는 report.json을 반환합니다. 자동 점수·LLM 평가·시장 분석이 포함됩니다.",
)
def get_latest_report(patent_id: str) -> dict:
    return latest_json(patent_id, "report")


@router.get(
    "/patents/{patent_id}/chunks",
    summary="특허 RAG chunk 목록 조회",
    description=(
        "Qdrant에 색인된 특허 chunk를 페이지네이션으로 조회합니다.\n\n"
        "- `chunk_file=all` : 원문 + 보고서 전체\n"
        "- `chunk_file=original` : 원문 PDF chunk만\n"
        "- `chunk_file=report` : 보고서 PDF chunk만\n"
        "- `source_type` 필터: `ORIGINAL_PDF`, `REPORT_PDF`, `SHARED_PATENT`, `SHARED_REPORT`"
    ),
)
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


@router.get(
    "/business/chunks",
    summary="공통 Business RAG chunk 조회",
    description="업무 공통 데이터(business/index/all_chunks.jsonl)에서 chunk를 조회합니다. 현재는 비활성화된 데이터 소스입니다.",
)
def get_business_chunks(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)) -> dict:
    return business_chunks(offset=offset, limit=limit)


# ── [chatbot] 저장소 · 연결 상태 ──────────────────────────────────────────

@router.get(
    "/qdrant/status",
    summary="Qdrant 벡터 DB 연결 상태 확인",
    description=(
        "Qdrant 서버 연결 여부, 전체 컬렉션 목록, 임베딩 모델, dashboard URL을 반환합니다. "
        "연결 실패 시 `connected: false`와 `error` 메시지가 포함됩니다."
    ),
)
def get_qdrant_status() -> dict:
    return qdrant_status()


@router.get(
    "/minio/status",
    summary="MinIO 오브젝트 스토리지 연결 상태 확인",
    description=(
        "MinIO 연결 여부, 원격 오브젝트 수, 로컬 동기화된 특허 수, console URL을 반환합니다. "
        "로컬 캐시가 최신 상태인지 확인할 때 사용합니다."
    ),
)
def get_minio_status() -> dict:
    return minio_patent_status()


@router.post(
    "/minio/sync",
    summary="MinIO → 로컬 특허 데이터 동기화",
    description=(
        "MinIO `s3://{bucket}/patent/` 의 특허 데이터를 로컬 공유 patent 캐시(`data/patent/`)로 동기화합니다. "
        "`rebuild_index=true`(기본값)면 동기화 후 shared vectorstore(`skipa_patent_docs`)도 blue-green 재색인합니다."
    ),
)
def post_minio_sync(rebuild_index: bool = Query(True, description="동기화 후 공유 특허 vectorstore를 재생성할지 여부")) -> dict:
    return sync_patent_data_from_minio(rebuild_index=rebuild_index)


# ── [chatbot] Vectorstore 상태 · 관리 ────────────────────────────────────

@router.get(
    "/vectorstore/status",
    summary="Vectorstore 전체 현황 조회",
    description=(
        "특허별·분야별 wiki·글로벌 Qdrant 컬렉션의 존재 여부, 문서 수, "
        "blue-green alias 상태를 한 번에 반환합니다."
    ),
)
def get_vectorstore_status() -> dict:
    return vectorstore_status()


@router.get(
    "/preprocess/status",
    summary="전처리 파이프라인 전체 상태 통합 조회",
    description=(
        "Vectorstore, MinIO, Qdrant 연결 상태를 한 번에 확인합니다. 시스템 점검 시 사용합니다."
    ),
)
def get_preprocess_status() -> dict:
    return {
        "vectorstore": vectorstore_status(),
        "minio": minio_patent_status(),
        "qdrant": qdrant_status(),
    }


@router.post(
    "/vectorstore/refresh",
    summary="Vectorstore 전체 재생성 (감사 자동 적용 포함)",
    description=(
        "`auto_audit=true`(기본값)면 저품질·주의 데이터를 자동 감사·제외 후 승인 데이터 기준으로 "
        "전체 Vectorstore를 blue-green 방식으로 재생성합니다. "
        "직접 `/preprocess/run?mode=refresh_vectorstore` 호출과 동일합니다."
    ),
)
def post_vectorstore_refresh(auto_audit: bool = Query(True, description="true면 주의/나쁜 데이터 자동 제외 후 승인본으로 refresh")) -> dict:
    result = run_wiki_audit_graph(mode="auto_refresh" if auto_audit else "refresh")
    return result.get("apply_result") or result.get("refresh_result", result)


@router.post(
    "/vectorstore/full-rebuild",
    summary="Vectorstore 완전 초기화 후 재구축",
    description=(
        "특허·wiki 관련 Qdrant 컬렉션을 **전부 삭제**하고 처음부터 재색인합니다.\n\n"
        "**재구축 순서:**\n"
        "1. `data/patent/` → `skipa_patent_docs` (shared patents) blue-green 재색인\n"
        "2. 분야별 wiki → `skipa_wiki_topic_{slug}` blue-green 재색인\n"
        "3. 전체 wiki 통합 → `skipa_wiki_live` blue-green 재색인\n\n"
        "⚠️ application, pre-eval, visual 컬렉션은 영향받지 않습니다."
    ),
)
def post_vectorstore_full_rebuild() -> dict:
    return full_rebuild_vectorstores()


# ── [chatbot] Blue-Green 관리 ─────────────────────────────────────────────

@router.get(
    "/bluegreen/status",
    summary="Blue-Green Vectorstore 현황 조회",
    description=(
        "특허·wiki blue-green 컬렉션 상태를 반환합니다.\n\n"
        "- **특허** (`global_patent`): API 호출 시 교체 (`POST /bluegreen/refresh`)\n"
        "- **Wiki** (`global_wiki`): 1시간 스케줄러가 자동 교체\n\n"
        "각 항목에는 활성 슬롯(green/blue), 문서 수, 마지막 교체 시각이 포함됩니다."
    ),
)
def get_bluegreen_status() -> dict:
    return bluegreen_reindex_status()


@router.post(
    "/bluegreen/refresh",
    summary="특허 Blue-Green 즉시 교체 실행",
    description=(
        "특허 원본 PDF·보고서 글로벌 컬렉션을 blue-green으로 즉시 재색인합니다.\n\n"
        "Wiki 컬렉션은 1시간 스케줄러가 별도로 관리하므로 이 API로는 교체되지 않습니다.\n\n"
        "현재 green이 활성이면 blue 슬롯에 재색인 후 alias를 blue로 교체합니다."
    ),
)
def post_bluegreen_refresh() -> dict:
    return bluegreen_refresh_patent_only()


@router.get(
    "/vectorstore/patent/status",
    summary="특허 Blue-Green Vectorstore 상세 상태",
    description=(
        "글로벌 특허 컬렉션의 blue-green 슬롯 상태, 문서 수, 마지막 교체 시각을 반환합니다.\n\n"
        "재색인: `POST /bluegreen/refresh`"
    ),
)
def get_patent_vectorstore_status() -> dict:
    from ..qdrant_store import bluegreen_collection_status, bluegreen_patent_alias, collection_info, patent_collection
    alias = bluegreen_patent_alias()
    green = f"{alias}_green"
    blue = f"{alias}_blue"
    bg_status = bluegreen_collection_status(alias, green, blue)
    last = {}
    try:
        from ..vectorstore import _load_bluegreen_status
        last = _load_bluegreen_status()
    except Exception:
        pass
    return {
        "type": "patent",
        "schedule": "on_api_call",
        "alias": alias,
        "patent_refreshed_at": last.get("patent_refreshed_at"),
        "bluegreen": bg_status,
    }


@router.get(
    "/vectorstore/wiki/status",
    summary="Wiki Blue-Green Vectorstore 상세 상태",
    description=(
        "글로벌 wiki 컬렉션의 blue-green 슬롯 상태, 문서 수, 다음 자동 교체 시각을 반환합니다.\n\n"
        "재색인 주기: 1시간 자동 스케줄"
    ),
)
def get_wiki_vectorstore_status() -> dict:
    from ..qdrant_store import bluegreen_collection_status, bluegreen_wiki_alias
    alias = bluegreen_wiki_alias()
    green = f"{alias}_green"
    blue = f"{alias}_blue"
    bg_status = bluegreen_collection_status(alias, green, blue)
    last = {}
    try:
        from ..vectorstore import _load_bluegreen_status
        last = _load_bluegreen_status()
    except Exception:
        pass
    from datetime import datetime, timedelta
    next_run: str | None = None
    wiki_at = last.get("wiki_refreshed_at")
    if wiki_at:
        try:
            next_run = (datetime.fromisoformat(wiki_at) + timedelta(hours=1)).isoformat(timespec="seconds")
        except Exception:
            pass
    return {
        "type": "wiki",
        "schedule": "every_1_hour",
        "alias": alias,
        "wiki_refreshed_at": wiki_at,
        "next_scheduled_run": next_run,
        "bluegreen": bg_status,
    }


# ── [chatbot] 전처리 파이프라인 실행 ─────────────────────────────────────

@router.post(
    "/preprocess/run",
    summary="전처리 파이프라인 실행",
    description=(
        "`mode` 파라미터로 실행할 작업을 선택합니다.\n\n"
        "| mode | 설명 |\n"
        "|------|------|\n"
        "| `normalize_wiki` | 승인 wiki 데이터를 분야별 approved_context.md로 정규화 |\n"
        "| `refresh_vectorstore` | wiki 정규화 + 전체 vectorstore 재생성 |\n"
        "| `auto_audit_refresh` | wiki 자동 감사 → 저품질 제외 → vectorstore 재생성 |\n"
        "| `audit` | 데이터 품질 감사만 실행 (vectorstore 변경 없음) |\n"
        "| `shared_index` | data/patent/ → skipa_patent_docs blue-green 재색인 |\n"
        "| `visual_index` | 신규 특허 원본 PDF 도표·이미지 증분 색인 |\n"
        "| `nightly_reindex` | 전체 야간 재색인 워크플로우 실행 |\n"
        "| `all` | wiki 정규화 + vectorstore + visual 전체 |\n"
    ),
)
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
    elif request.mode == "nightly_reindex":
        result["nightly_reindex"] = nightly_reindex_all()
    elif request.mode == "shared_index":
        from ..shared_data import build_shared_vectorstore
        result["shared_index"] = build_shared_vectorstore()
    elif request.mode == "visual_index":
        result["visual_index"] = build_missing_patent_visual_indexes(force=False)
    elif request.mode == "all":
        result["wiki_normalize"] = normalize_wiki_context_files()
        result["vectorstore"] = refresh_vectorstores(use_reviewed=True)
        result["visual_index"] = build_missing_patent_visual_indexes(force=False)
    result["status"] = "ok"
    return result


# ── [chatbot] Visual(이미지·도표) Vectorstore ────────────────────────────

@router.get(
    "/visual-vectorstore/status",
    summary="Visual Vectorstore 상태 조회 (특허 원본 도표·이미지)",
    description=(
        "CLIP 이미지 임베딩 + OpenAI 텍스트 임베딩으로 구성된 "
        "`skipa_patent_visual_clip` 컬렉션의 존재 여부와 문서 수를 반환합니다."
    ),
)
def get_visual_vectorstore_status() -> dict:
    return patent_visual_index_status()


@router.post(
    "/visual-vectorstore/refresh",
    summary="Visual Vectorstore 증분 색인",
    description=(
        "특허 원본 PDF에서 추출한 도표·표·이미지를 CLIP 이미지 임베딩으로 색인합니다.\n\n"
        "- `force=false`(기본값): 이미 manifest가 있는 특허는 건너뜀 (증분 색인)\n"
        "- `force=true`: 전체 특허 visual index 강제 재생성\n"
        "- `patent_id` 지정: 해당 특허 1건만 처리"
    ),
)
def post_visual_vectorstore_refresh(
    force: bool = Query(False, description="true면 기존 manifest가 있어도 모든 특허 visual index를 다시 생성"),
    patent_id: str | None = Query(None, description="특정 특허 1건만 처리. 비우면 누락/신규 특허 전체 처리"),
) -> dict:
    if patent_id:
        return build_patent_visual_index(patent_id, force=force)
    return build_missing_patent_visual_indexes(force=force)


@router.post(
    "/visual-vectorstore/search",
    summary="Visual Vectorstore 검색 (이미지·도표 의미 검색)",
    description=(
        "CLIP 텍스트 인코더(cross-modal) + OpenAI 텍스트 임베딩을 RRF로 결합해 "
        "특허 원본의 도표·표·이미지를 의미 기반으로 검색합니다.\n\n"
        "Request body: `{\"query\": \"...\", \"patent_id\": \"...(선택)\", \"top_k\": 6}`"
    ),
)
def post_visual_vectorstore_search(body: dict) -> dict:
    return search_patent_visuals(
        str(body.get("query") or ""),
        patent_id=body.get("patent_id"),
        top_k=int(body.get("top_k") or 6),
    )


# ── [chatbot] RAG 검색 · 답변 (디버그용) ─────────────────────────────────

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="RAG 검색 직접 호출 (디버그용)",
    description=(
        "Qdrant vectorstore에서 유사도 검색을 직접 실행하고 결과를 반환합니다. "
        "챗봇 답변 없이 근거 검색 결과만 확인할 때 사용합니다. "
        "실제 채팅은 `patent-chat` 태그의 `/chat` 엔드포인트를 사용하세요."
    ),
)
def post_search(request: SearchRequest) -> dict:
    return search_chunks(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )


@router.post(
    "/query",
    response_model=SearchResponse,
    summary="RAG 검색 alias (= /search)",
    include_in_schema=False,
)
def post_query(request: SearchRequest) -> dict:
    return post_search(request)


@router.post(
    "/answer",
    response_model=AnswerResponse,
    summary="챗봇 답변 생성 (SearchRequest 기반)",
    include_in_schema=False,
)
def post_answer(request: SearchRequest) -> dict:
    return run_chat_agent(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )


# ── [patent-chat] 검색·답변 alias (rag_router는 Swagger 미노출) ──────────

@patent_chat_router.post("/query", response_model=SearchResponse, summary="특허 RAG 근거 검색")
@rag_router.post("/query", response_model=SearchResponse, summary="RAG 질의 alias")
def rag_query(request: SearchRequest) -> dict:
    return post_search(request)


@agent_router.post(
    "/query",
    response_model=SearchResponse,
    summary="[alias] 근거 검색 — patent-chat/query 와 동일",
    description="내부 호환용 alias입니다. 신규 개발 시 `POST /api/v1/patent-chat/query` 를 사용하세요.",
)
def agent_query(request: SearchRequest) -> dict:
    return post_search(request)


@patent_chat_router.post("/answer", response_model=AnswerResponse, summary="특허 챗봇 답변 생성 (SearchRequest)")
@rag_router.post("/answer", response_model=AnswerResponse, summary="RAG 답변 alias")
def rag_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@agent_router.post(
    "/answer",
    response_model=AnswerResponse,
    summary="[alias] 챗봇 답변 — patent-chat/answer 와 동일",
    description="내부 호환용 alias입니다. 신규 개발 시 `POST /api/v1/patent-chat/answer` 를 사용하세요.",
)
def agent_answer(request: SearchRequest) -> dict:
    return post_answer(request)


@patent_chat_router.get("/chat/mermaid", summary="챗봇 LangGraph 워크플로우 다이어그램", include_in_schema=False)
@rag_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
@agent_router.get("/chat/mermaid", summary="챗봇 LangGraph 답변 workflow Mermaid")
def get_chat_graph_mermaid() -> dict:
    return {"format": "mermaid", "diagram": chat_graph_mermaid()}


@patent_chat_router.get("/engine/status", summary="Hybrid Retrieval 엔진 상태", include_in_schema=False)
@rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
@legacy_rag_router.get("/engine/status", summary="복구된 rag.zip 엔진 사용 가능 여부")
def get_rag_engine_status() -> dict:
    return legacy_engine_status()


@patent_chat_router.get("/patents", summary="특허 챗봇 특허 목록", include_in_schema=False)
@rag_router.get("/patents", summary="통합 RAG 특허 목록")
@legacy_rag_router.get("/patents", summary="특허 챗봇 호환 특허 목록")
def rag_patents() -> dict:
    patents = list_patents()
    return {"items": patents, "count": len(patents), "engine": legacy_engine_status()}


# ── [patent-chat] 주요 채팅 엔드포인트 ───────────────────────────────────

@patent_chat_router.get(
    "/patent-summary-cards",
    summary="특허 요약 카드 목록",
    description="UI에서 특허 선택 드롭다운에 표시할 특허별 요약 정보(제목·점수·등급)를 반환합니다.",
)
@rag_router.get("/patent-summary-cards", summary="통합 RAG 특허 요약 카드")
@legacy_rag_router.get("/patent-summary-cards", summary="특허 챗봇 호환 특허 요약 카드")
def rag_patent_summary_cards() -> dict:
    return patent_summary_cards()


@patent_chat_router.post(
    "/chat",
    response_model=AnswerResponse,
    summary="특허 선택 챗봇 답변",
    description=(
        "선택한 특허(`patent_id`)를 기준으로 원문·보고서·wiki·웹 근거를 통합해 답변합니다.\n\n"
        "- `patent_id` 없이 호출하면 전체 특허 DB에서 검색합니다.\n"
        "- `chat_history`: 최근 대화 목록을 전달하면 후속 질문 컨텍스트를 유지합니다."
    ),
)
@rag_router.post("/chat", response_model=AnswerResponse, summary="통합 RAG 특허별 챗봇 답변")
@legacy_rag_router.post("/chat", response_model=AnswerResponse, summary="특허 챗봇 호환 답변")
def rag_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=request.patent_id,
        user_id=request.user_id,
        chat_history=_chat_history_payload(request.chat_history),
    )


@patent_chat_router.post(
    "/global/chat",
    response_model=AnswerResponse,
    summary="전체 특허 챗봇 답변 (특허 미선택)",
    description=(
        "특정 특허를 선택하지 않고 전체 특허 DB(`skipa_patent_docs`)에서 관련 근거를 탐색해 답변합니다. "
        "전체 탐색이므로 특허 선택 채팅보다 응답 근거 범위가 넓습니다."
    ),
)
@rag_router.post("/global/chat", response_model=AnswerResponse, summary="통합 RAG 전체 특허 챗봇 답변")
@legacy_rag_router.post("/global/chat", response_model=AnswerResponse, summary="전체 특허 챗봇 호환 답변")
def rag_global_chat(request: ChatRequest) -> dict:
    return run_chat_agent(
        request.question,
        patent_id=None,
        user_id=request.user_id,
        chat_history=_chat_history_payload(request.chat_history),
    )


@patent_chat_router.post(
    "/reindex",
    include_in_schema=False,
    summary="특허별 Qdrant 인덱스 재생성",
    description=(
        "특정 특허의 Qdrant 인덱스를 재생성합니다. "
        "새 특허 데이터가 추가됐거나 원문·보고서가 갱신된 경우 호출합니다. "
        "`refresh_reviewed_vectorstore=true`면 사람 승인 데이터 기반 vectorstore도 함께 갱신합니다."
    ),
)
@rag_router.post("/reindex", summary="특허별 Qdrant 인덱스 재생성")
@legacy_rag_router.post("/reindex", summary="특허별 Qdrant 인덱스 재생성")
def rag_reindex(request: ReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="patent",
        patent_id=request.patent_id,
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.post(
    "/global/reindex",
    include_in_schema=False,
    summary="전체 특허 글로벌 인덱스 재생성",
    description=(
        "전체 특허를 하나의 글로벌 Qdrant 컬렉션으로 재색인합니다. "
        "특허가 대거 추가·삭제됐을 때 사용합니다. "
        "일반적으로는 `/chatbot/vectorstore/full-rebuild` 또는 blue-green refresh를 사용하세요."
    ),
)
@rag_router.post("/global/reindex", summary="전체 특허 global Qdrant 인덱스 재생성")
@legacy_rag_router.post("/global/reindex", summary="전체 특허 global Qdrant 인덱스 재생성")
def rag_global_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="global",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.post(
    "/business/reindex",
    summary="업무 공통 인덱스 재생성 (비활성)",
    include_in_schema=False,
)
@rag_router.post("/business/reindex", summary="업무/공통 Qdrant 인덱스 재생성")
@legacy_rag_router.post("/business/reindex", summary="업무/공통 Qdrant 인덱스 재생성")
def rag_business_reindex(request: BusinessReindexRequest) -> dict:
    return run_ingestion_graph(
        scope="business",
        force_rebuild=request.force_rebuild,
        refresh_reviewed_vectorstore=request.refresh_reviewed_vectorstore,
    )


@patent_chat_router.get(
    "/ingestion/mermaid",
    summary="전처리·재색인 워크플로우 다이어그램",
    include_in_schema=False,
)
@rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
@legacy_rag_router.get("/ingestion/mermaid", summary="전처리/RAG 재색인 LangGraph Mermaid")
def get_ingestion_mermaid() -> dict:
    return {"format": "mermaid", "diagram": ingestion_graph_mermaid()}


@patent_chat_router.post(
    "/feedback",
    summary="챗봇 답변 피드백 저장",
    description="사용자가 챗봇 답변에 남긴 평가(rating, reason)를 저장합니다. 데이터 품질 개선에 활용됩니다.",
)
@rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
@legacy_rag_router.post("/feedback", summary="챗봇 답변 피드백 저장")
def rag_feedback(request: FeedbackRequest) -> dict:
    return write_feedback(request.model_dump())


@patent_chat_router.get(
    "/page-image",
    summary="특허 PDF 페이지 이미지 렌더링",
    description="특허 원본 PDF의 특정 페이지를 이미지로 렌더링해 반환합니다. UI에서 원문 페이지 미리보기에 사용합니다.",
)
@rag_router.get("/page-image", summary="특허 PDF page image 렌더링")
@legacy_rag_router.get("/page-image", summary="특허 PDF page image 렌더링")
def rag_page_image(patent_id: str, file_name: str = Query("original.pdf"), page_no: int = Query(1, ge=1)):
    return render_page_image(patent_id, file_name=file_name, page_no=page_no)


# ── [wiki] 감사 · 검토 엔드포인트 ────────────────────────────────────────

@router.get(
    "/wiki-audit/report",
    summary="Wiki 감사 리포트 조회",
    description="가장 최근 감사 결과의 Markdown 리포트를 반환합니다. `/wiki/audit-report` 와 동일합니다.",
)
@wiki_router.get(
    "/audit-report",
    summary="Wiki 감사 리포트 조회",
    description="가장 최근 감사 결과의 Markdown 리포트를 반환합니다.",
)
def get_wiki_audit_report() -> dict:
    return wiki_audit_report()


@router.post(
    "/wiki-audit/run",
    summary="Wiki 데이터 품질 감사 실행",
    description=(
        "특허·보고서·wiki chunk를 스캔해 품질 문제(빈 텍스트, OCR 노이즈, 민감정보, 중복)를 탐지합니다. "
        "결과는 finding 목록으로 반환되며, 사람이 검토 후 `/wiki-audit/apply`로 적용합니다."
    ),
)
@wiki_router.post(
    "/audit",
    summary="Wiki 데이터 품질 감사 실행",
    description="특허·보고서·wiki chunk 품질 감사를 실행합니다. 결과는 `/audit-review`에서 확인합니다.",
)
def post_wiki_audit(refresh_vectorstore: bool = Query(False, description="사람 검토 전 raw vectorstore 강제 갱신 여부")) -> dict:
    result = run_wiki_audit_graph(mode="audit", refresh_vectorstore=refresh_vectorstore)
    audit = result.get("audit", result)
    if isinstance(audit, dict):
        audit["agent_trace"] = result.get("trace", [])
    return audit


@router.get(
    "/wiki-audit/review",
    summary="Wiki 감사 사람 검토용 Markdown 조회",
    description=(
        "감사 결과를 사람이 검토할 수 있는 Markdown 형식으로 반환합니다. "
        "각 finding 항목의 rule_id, severity, excerpt를 포함합니다."
    ),
)
@wiki_router.get(
    "/audit-review",
    summary="Wiki 감사 사람 검토용 Markdown 조회",
    description="감사 finding 목록을 Markdown 형식으로 반환합니다. `/wiki-audit/apply` 전 검토에 사용합니다.",
)
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


@wiki_router.post("/topics/reclassify", summary="전체 특허 분야 재분류 (새 폴더 자동 생성)", include_in_schema=False)
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


@wiki_router.post("/agent/run", summary="Wiki LangGraph agent 직접 실행", include_in_schema=False)
def post_wiki_agent_run(request: WikiAgentRunRequest) -> dict:
    return run_wiki_audit_graph(
        mode=request.mode,
        audit_id=request.audit_id,
        exclude_finding_ids=request.exclude_finding_ids,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_vectorstore=request.refresh_vectorstore,
    )


@wiki_router.get("/agent/mermaid", summary="Wiki LangGraph agent Mermaid", include_in_schema=False)
def get_wiki_agent_mermaid() -> dict:
    return {"format": "mermaid", "diagram": wiki_audit_graph_mermaid()}
