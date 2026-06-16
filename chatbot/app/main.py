"""FastAPI entrypoint for chatbot Swagger checks."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import os

from .config import (
    BUSINESS_ROOT,
    DATA_ROOT,
    MINIO_SYNC_ON_STARTUP,
    MINIO_WIKI_SYNC_ON_STARTUP,
    PATENTS_ROOT,
    PRE_EVAL_ROOT,
    SHARED_DATA_ROOT,
)
from .routers.admin import router as admin_router
from .routers.insights import router as insights_router
from .routers.pre_eval import router as pre_eval_router
from .routers.chatbot import (
    patent_chat_router,
    re_eval_router,
    router as chatbot_router,
    wiki_router,
)
from .streaming.router import router as streaming_router

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# 환경변수 REINDEX_INTERVAL_SECONDS 로 조정 가능 (기본 3600 = 1시간)
_REINDEX_INTERVAL = int(os.environ.get("REINDEX_INTERVAL_SECONDS", "3600"))
# 앱 시작 후 첫 실행까지 대기 시간 (기본 60초, 빠른 확인을 위해 단축 가능)
_REINDEX_INITIAL_DELAY = int(os.environ.get("REINDEX_INITIAL_DELAY_SECONDS", "60"))


def _next_run_iso() -> str:
    return (datetime.now(KST) + timedelta(seconds=_REINDEX_INTERVAL)).replace(microsecond=0).isoformat()


async def _bluegreen_wiki_loop() -> None:
    """Wiki 글로벌 컬렉션 blue-green 1시간 스케줄러.

    특허 컬렉션은 API 트리거(POST /api/v1/chatbot/bluegreen/refresh)로 교체합니다.
    전체 재인덱싱은 /preprocess/run?mode=nightly_reindex 로 수동 실행합니다.
    """
    logger.info(
        "wiki blue-green 스케줄러 시작 — 초기 대기 %d초 후 첫 실행, 이후 %d초 간격",
        _REINDEX_INITIAL_DELAY, _REINDEX_INTERVAL,
    )
    await asyncio.sleep(_REINDEX_INITIAL_DELAY)
    while True:
        try:
            from .vectorstore import bluegreen_refresh_wiki_only
            logger.info("wiki blue-green reindex 시작")
            result = bluegreen_refresh_wiki_only()
            logger.info(
                "wiki blue-green reindex 완료: color=%s wiki_docs=%s",
                result.get("global_wiki", {}).get("active_color"),
                result.get("wiki_doc_count"),
            )
        except Exception as exc:
            logger.error("wiki blue-green reindex 실패: %s", exc, exc_info=True)
        await asyncio.sleep(_REINDEX_INTERVAL)


async def _startup_minio_sync_loop() -> None:
    """Run MinIO syncs after the app starts so health probes are not blocked."""
    if MINIO_SYNC_ON_STARTUP:
        try:
            from .minio_data import sync_patent_data_from_minio

            result = await asyncio.to_thread(sync_patent_data_from_minio)
            logger.info(
                "MinIO patent sync: status=%s local_patents=%s remote_objects=%s",
                result.get("sync_status") or result.get("status"),
                (result.get("minio") or result).get("local_patent_count"),
                (result.get("minio") or result).get("remote_object_count"),
            )
        except Exception as exc:
            logger.error("MinIO patent sync failed: %s", exc)

    if MINIO_WIKI_SYNC_ON_STARTUP:
        try:
            from .minio_data import sync_wiki_data_from_minio, sync_wiki_data_to_minio

            pull_result = await asyncio.to_thread(sync_wiki_data_from_minio)
            push_result = await asyncio.to_thread(sync_wiki_data_to_minio)
            logger.info(
                "MinIO wiki sync: pull=%s downloaded=%s push=%s uploaded=%s local_files=%s",
                pull_result.get("sync_status") or pull_result.get("status"),
                pull_result.get("downloaded_count"),
                push_result.get("status"),
                push_result.get("uploaded_count"),
                push_result.get("local_wiki_file_count"),
            )
        except Exception as exc:
            logger.error("MinIO wiki sync failed: %s", exc)


@asynccontextmanager
async def lifespan(application: FastAPI):
    startup_minio_task = asyncio.create_task(_startup_minio_sync_loop())

    # BM25 인덱스 pre-warm — 첫 요청 latency 제거
    async def _prewarm_bm25() -> None:
        try:
            from .shared_data import _ensure_bm25_index
            await asyncio.to_thread(_ensure_bm25_index)
            logger.info("BM25 index pre-warmed")
        except Exception as exc:
            logger.warning("BM25 pre-warm skipped: %s", exc)

    asyncio.create_task(_prewarm_bm25())

    task = asyncio.create_task(_bluegreen_wiki_loop())
    logger.info(
        "wiki blue-green 스케줄러 등록 (초기 대기 %ds → 이후 %ds 간격, 특허는 API 트리거)",
        _REINDEX_INITIAL_DELAY, _REINDEX_INTERVAL,
    )
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    startup_minio_task.cancel()
    try:
        await startup_minio_task
    except asyncio.CancelledError:
        pass


STATIC_ROOT = Path(__file__).resolve().parent / "static"

app = FastAPI(
    lifespan=lifespan,
    title="SKIPA AI Chatbot API",
    description=(
        "## SKIPA 재평가 챗봇 · 사전평가 · Portfolio Insights 통합 API\n\n"
        "---\n\n"
        "### 🟢 외부 공개 API — 프론트엔드·파트너 서비스 연동\n\n"
        "| 태그 | 대표 엔드포인트 | 설명 |\n"
        "|------|----------------|------|\n"
        "| **re-eval** | `POST /api/v1/patents/{patent_id}/chat` | 재평가 챗봇 |\n"
        "| **pre-eval** | `POST /api/v1/pre-eval/webhook/report-complete` | 보고서 완료 알림 → 인덱싱 |\n"
        "| **pre-eval** | `POST /api/v1/pre-eval/cases/{case_id}/chat` | 사전평가 챗봇 |\n"
        "| **pre-eval** | `GET /api/v1/pre-eval/vectorstore/status` | 사전 출원 벡터스토어 현황 |\n"
        "| **insights** | `POST /api/v1/portfolio/insights` | 포트폴리오 AI 인사이트 생성 |\n"
        "---\n\n"
        "### 🔧 내부 운영 API — 백오피스·배포 파이프라인 전용\n\n"
        "| 태그 | 설명 |\n"
        "|------|------|\n"
        "| **chatbot** | MinIO·Qdrant·Vectorstore·Blue-Green·전처리 관리 |\n"
        "| **wiki** | Wiki 품질 감사·승인·분야별 Vectorstore 관리 |\n\n"
        "#### 벡터스토어 전략\n"
        "| 컬렉션 | 교체 방식 | 주기 |\n"
        "|--------|----------|------|\n"
        "| 특허 원본 PDF·보고서 (`global_patent`) | Blue-Green | API 호출 시 (`POST /api/v1/chatbot/bluegreen/refresh`) |\n"
        "| Wiki (`global_wiki`) | Blue-Green | 1시간 자동 스케줄 |\n"
        "| 사전평가 케이스 (`pre-{case_id}`) | 단순 upsert 누적 | 웹훅 수신 시 즉시 인덱싱 |\n"
    ),
    version="1.0.0",
    openapi_tags=[
        # ── 🟢 외부 공개 API ──────────────────────────────────────────────────
        {
            "name": "re-eval",
            "description": (
                "**🟢 [외부 공개] 재평가 챗봇 답변**\n\n"
                "LangGraph 의도 라우팅 → Qdrant Hybrid Retrieval → OpenAI 답변 생성 파이프라인입니다.\n\n"
                "`POST /api/v1/patents/{patent_id}/chat` 요청 body에는 "
                "`chat_history`, `question`, `user_id`만 전달합니다.\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /api/v1/patents/{patent_id}/chat` | 재평가 특허 기준 채팅 |\n"
                "| `GET /api/v1/patents` | 재평가 특허 목록 |\n"
                "| `GET /api/v1/patents/summary-cards` | 재평가 특허 요약 카드 |"
            ),
        },
        {
            "name": "pre-eval",
            "description": (
                "**🟢 [외부 공개] 사전 출원 특허 챗봇**\n\n"
                "외부 사전 출원 평가 서비스가 보고서 생성 완료를 웹훅으로 알리면,\n"
                "MinIO에서 `report.json`을 가져와 `pre-{case_id}` 벡터스토어에 인덱싱합니다.\n"
                "이후 해당 케이스 ID로 챗봇을 바로 사용할 수 있습니다.\n\n"
                "**외부 연동 플로우:**\n"
                "1. 외부 시스템이 MinIO에 `report.json` 업로드\n"
                "2. `POST /webhook/report-complete` 호출 → 자동 인덱싱\n"
                "3. `POST /cases/{case_id}/chat` 으로 챗봇 사용\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /webhook/report-complete` | 보고서 완료 알림 수신 + MinIO 인덱싱 |\n"
                "| `POST /cases/{case_id}/chat` | 사전평가 보고서 기반 챗봇 |\n"
                "| `POST /cases/{case_id}/search` | 벡터스토어 직접 검색 |\n"
                "| `GET /vectorstore/status` | 전체 사전 출원 벡터스토어 목록 |\n"
                "| `GET /vectorstore/{patent_id}/status` | 특정 특허 벡터스토어 상태 |"
            ),
        },
        {
            "name": "insights",
            "description": (
                "**🟢 [외부 공개] Portfolio AI Insights**\n\n"
                "`ai-insights` 앱의 포트폴리오 인사이트 생성 API를 같은 FastAPI 앱/포트에서 제공합니다.\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /api/v1/portfolio/insights` | 포트폴리오 추이·분포·유지/포기 데이터를 3개 한국어 인사이트로 생성 |"
            ),
        },
        # ── 🔧 내부 운영 API ──────────────────────────────────────────────────
        {
            "name": "chatbot",
            "description": (
                "**🔧 [내부 운영] 데이터·인프라·Vectorstore 관리**\n\n"
                "배포 파이프라인, 운영팀, 백오피스에서 사용하는 API입니다.\n\n"
                "| 그룹 | 엔드포인트 |\n"
                "|------|----------|\n"
                "| 특허 데이터 조회 | `/patents`, `/patents/{id}`, `/patents/{id}/chunks` |\n"
                "| 저장소 연결 확인 | `/minio/status`, `/minio/sync`, `/qdrant/status` |\n"
                "| Vectorstore 상태 | `/vectorstore/status`, `/vectorstore/patent/status`, `/vectorstore/wiki/status` |\n"
                "| Blue-Green 색인 | `/bluegreen/status`, `/bluegreen/refresh` (특허 전용, API 트리거) |\n"
                "| 전처리 파이프라인 | `/preprocess/run`, `/preprocess/status` |\n"
                "| Wiki 감사 | `/wiki-audit/run`, `/wiki-audit/apply` |\n"
                "| 인덱스 재생성 | `/patent-chat/reindex`, `/patent-chat/global/reindex` (레거시 호환) |\n"
                "| Visual 색인 | `/visual-vectorstore/status`, `/refresh`, `/search` |"
            ),
        },
        {
            "name": "wiki",
            "description": (
                "**🔧 [내부 운영] Wiki 품질 감사 · 분야별 Vectorstore 관리**\n\n"
                "특허 데이터를 기술 분야별로 분류하고 품질을 감사합니다. "
                "사람이 검토·승인한 wiki 데이터만 챗봇 근거로 사용됩니다.\n\n"
                "**Wiki 벡터스토어**: 1시간마다 자동 Blue-Green 교체\n\n"
                "지원 분야: `반도체_전자`, `소프트웨어_IT`, `스마트_팩토리`, `특허출원_절차`\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /audit` | 데이터 품질 감사 실행 |\n"
                "| `GET /audit-review` | 감사 결과 사람 검토용 Markdown |\n"
                "| `POST /audit-apply` | 검토 결과 적용 + vectorstore 갱신 |\n"
                "| `POST /audit-auto-refresh` | 자동 감사·제외·vectorstore 재빌드 |\n"
                "| `GET /topics` | 분야별 vectorstore 현황 |\n"
                "| `POST /topics/refresh` | 분야별 vectorstore 전체 재빌드 |"
            ),
        },
        {
            "name": "system",
            "description": "🟢 서비스 헬스체크 · 루트 확인 (외부 공개)",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router)
app.include_router(re_eval_router)
app.include_router(patent_chat_router)
app.include_router(wiki_router)
app.include_router(pre_eval_router)
app.include_router(streaming_router)
app.include_router(insights_router)
app.include_router(admin_router)

if STATIC_ROOT.exists():
    app.mount("/ui/static", StaticFiles(directory=str(STATIC_ROOT)), name="ui_static")

if DATA_ROOT.exists():
    app.mount("/files/data", StaticFiles(directory=str(DATA_ROOT)), name="data_files")

if PATENTS_ROOT.exists():
    app.mount("/files/patents", StaticFiles(directory=str(PATENTS_ROOT)), name="patent_files")

if BUSINESS_ROOT.exists():
    app.mount("/files/business", StaticFiles(directory=str(BUSINESS_ROOT)), name="business_files")


if PRE_EVAL_ROOT.exists():
    app.mount("/files/pre-eval", StaticFiles(directory=str(PRE_EVAL_ROOT)), name="pre_eval_files")

if SHARED_DATA_ROOT.exists():
    app.mount("/files/shared", StaticFiles(directory=str(SHARED_DATA_ROOT)), name="shared_data_files")


@app.get("/", tags=["system"], summary="챗봇 API 루트")
def root() -> dict[str, str]:
    return {
        "service": "skipa-chatbot-api",
        "ui": "/ui",
        "chat": "/chat",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/ui", tags=["system"], summary="챗봇 테스트 UI")
def ui() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/chat", tags=["system"], summary="특허 챗봇 테스트 UI")
def chat() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/health", tags=["system"], summary="챗봇 API 헬스체크")
def health() -> dict:
    return {
        "status": "ok",
        "data_root": str(DATA_ROOT),
        "patents_root": str(PATENTS_ROOT),
        "patents_root_exists": PATENTS_ROOT.exists(),
    }
