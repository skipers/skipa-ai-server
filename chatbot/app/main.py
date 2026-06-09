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

from .config import BUSINESS_ROOT, DATA_ROOT, MINIO_SYNC_ON_STARTUP, PATENTS_ROOT, PRE_EVAL_ROOT, SHARED_DATA_ROOT
from .routers.pre_eval import router as pre_eval_router
from .routers.chatbot import (
    agent_router,
    legacy_rag_router,
    patent_chat_router,
    rag_router,
    router as chatbot_router,
    wiki_router,
)

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# 환경변수 REINDEX_INTERVAL_SECONDS 로 조정 가능 (기본 3600 = 1시간)
_REINDEX_INTERVAL = int(os.environ.get("REINDEX_INTERVAL_SECONDS", "3600"))
# 앱 시작 후 첫 실행까지 대기 시간 (기본 60초, 빠른 확인을 위해 단축 가능)
_REINDEX_INITIAL_DELAY = int(os.environ.get("REINDEX_INITIAL_DELAY_SECONDS", "60"))


def _next_run_iso() -> str:
    return (datetime.now(KST) + timedelta(seconds=_REINDEX_INTERVAL)).replace(microsecond=0).isoformat()


async def _bluegreen_reindex_loop() -> None:
    """blue-green 글로벌 색인 교체 루프.

    - 시작 후 _REINDEX_INITIAL_DELAY 초 대기 → 첫 실행
    - 이후 _REINDEX_INTERVAL 초(기본 1시간)마다 반복
    - 실행 함수: bluegreen_refresh_global() — 글로벌 patent·wiki 컬렉션만 교체
    - 전체 재인덱싱(application pack 등)은 /preprocess/run?mode=nightly_reindex 로 수동 실행
    """
    logger.info(
        "blue-green reindex 스케줄러 시작 — 초기 대기 %d초 후 첫 실행, 이후 %d초 간격",
        _REINDEX_INITIAL_DELAY, _REINDEX_INTERVAL,
    )
    await asyncio.sleep(_REINDEX_INITIAL_DELAY)
    while True:
        try:
            from .vectorstore import bluegreen_refresh_global
            logger.info("blue-green reindex 시작")
            result = bluegreen_refresh_global()
            logger.info(
                "blue-green reindex 완료: patent_color=%s wiki_color=%s patent_docs=%s wiki_docs=%s",
                result.get("global_patent", {}).get("active_color"),
                result.get("global_wiki", {}).get("active_color"),
                result.get("patent_doc_count"),
                result.get("wiki_doc_count"),
            )
        except Exception as exc:
            logger.error("blue-green reindex 실패: %s", exc, exc_info=True)
        await asyncio.sleep(_REINDEX_INTERVAL)


@asynccontextmanager
async def lifespan(application: FastAPI):
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
    task = asyncio.create_task(_bluegreen_reindex_loop())
    logger.info(
        "blue-green reindex 스케줄러 등록 (초기 대기 %ds → 이후 %ds 간격)",
        _REINDEX_INITIAL_DELAY, _REINDEX_INTERVAL,
    )
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


STATIC_ROOT = Path(__file__).resolve().parent / "static"

app = FastAPI(
    lifespan=lifespan,
    title="SKIPA AI Chatbot API",
    description=(
        "## SKIPA 특허 챗봇 · 사전평가 통합 API\n\n"
        "### 🟢 외부 공개 API (프론트엔드·외부 서비스 연동)\n"
        "| 태그 | 설명 | 대표 엔드포인트 |\n"
        "|------|------|-----------------|\n"
        "| **patent-chat** | 특허 챗봇 답변·검색·피드백 | `POST /api/v1/patent-chat/chat` |\n"
        "| **pre-eval** | 출원 전 사전평가 실행·케이스 채팅 | `POST /api/v1/pre-eval/evaluate` |\n\n"
        "### 🔧 내부 운영 API (백오피스·배포 파이프라인 전용)\n"
        "| 태그 | 설명 |\n"
        "|------|------|\n"
        "| **chatbot** | MinIO·Qdrant·Vectorstore·Blue-Green·전처리 관리 |\n"
        "| **wiki** | Wiki 품질 감사·승인·분야별 Vectorstore 관리 |\n\n"
        "> ℹ️ `agent` 태그 엔드포인트는 내부 alias로 Swagger에서 숨겨져 있습니다.\n"
        "> Mermaid 다이어그램, legacy 엔진 상태 등 내부 전용 엔드포인트도 숨겨져 있습니다.\n"
    ),
    version="1.0.0",
    openapi_tags=[
        # ── 🟢 외부 공개 API ──────────────────────────────────────────────────
        {
            "name": "patent-chat",
            "description": (
                "**🟢 [외부 공개] 특허 챗봇 답변·검색·피드백**\n\n"
                "LangGraph 의도 라우팅 → Qdrant Hybrid Retrieval → OpenAI 답변 생성 파이프라인입니다. "
                "프론트엔드 및 외부 서비스에서 직접 호출하세요.\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /chat` | 특허 선택 채팅 — `patent_id` 지정 시 해당 특허 우선 검색 |\n"
                "| `POST /global/chat` | 전체 특허 DB 채팅 — 특허 미선택 시 사용 |\n"
                "| `GET /patents` | 특허 목록 (드롭다운용) |\n"
                "| `GET /patent-summary-cards` | 특허 요약 카드 |\n"
                "| `POST /query` | RAG 근거 검색만 (답변 없음) |\n"
                "| `POST /feedback` | 답변 피드백 저장 |\n"
                "| `GET /page-image` | PDF 페이지 이미지 렌더링 |"
            ),
        },
        {
            "name": "pre-eval",
            "description": (
                "**🟢 [외부 공개] 출원 전 사전평가**\n\n"
                "발명 정보(특허명·기술 설명·청구항)를 입력하면 AI가 권리성·시장성·사업성을 사전 진단하고 "
                "평가 보고서 전용 vectorstore 기반 챗봇을 제공합니다.\n\n"
                "| 엔드포인트 | 설명 |\n"
                "|------------|------|\n"
                "| `POST /evaluate` | 사전평가 실행 및 보고서 생성 |\n"
                "| `GET /cases` | 평가 이력 목록 |\n"
                "| `GET /cases/{id}` | 특정 케이스 상태 |\n"
                "| `GET /cases/{id}/report` | 평가 보고서 조회 |\n"
                "| `POST /cases/{id}/chat` | 평가 보고서 기반 채팅 |\n"
                "| `POST /cases/{id}/search` | 평가 vectorstore 직접 검색 |"
            ),
        },
        # ── 🔧 내부 운영 API ──────────────────────────────────────────────────
        {
            "name": "chatbot",
            "description": (
                "**🔧 [내부 운영] 데이터·인프라·Vectorstore 관리**\n\n"
                "배포 파이프라인, 운영팀, 백오피스에서 사용하는 API입니다. "
                "프론트엔드에서 직접 호출하지 않습니다.\n\n"
                "| 그룹 | 엔드포인트 |\n"
                "|------|----------|\n"
                "| 특허 데이터 조회 | `/patents`, `/patents/{id}`, `/patents/{id}/chunks` |\n"
                "| 저장소 연결 확인 | `/minio/status`, `/minio/sync`, `/qdrant/status` |\n"
                "| Vectorstore 관리 | `/vectorstore/status`, `/vectorstore/full-rebuild` |\n"
                "| Blue-Green 색인 | `/bluegreen/status`, `/bluegreen/refresh` |\n"
                "| 전처리 파이프라인 | `/preprocess/run`, `/preprocess/status` |\n"
                "| Wiki 감사 | `/wiki-audit/run`, `/wiki-audit/apply` |\n"
                "| 인덱스 재생성 | `/api/v1/patent-chat/reindex`, `/global/reindex` |\n"
                "| Visual 색인 | `/visual-vectorstore/status`, `/refresh`, `/search` |"
            ),
        },
        {
            "name": "wiki",
            "description": (
                "**🔧 [내부 운영] Wiki 품질 감사 · 분야별 Vectorstore 관리**\n\n"
                "특허 데이터를 기술 분야별로 분류하고 품질을 감사합니다. "
                "사람이 검토·승인한 wiki 데이터만 챗봇 근거로 사용됩니다.\n\n"
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
app.include_router(patent_chat_router)
app.include_router(rag_router)
app.include_router(legacy_rag_router)
app.include_router(agent_router)
app.include_router(wiki_router)
app.include_router(pre_eval_router)

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
