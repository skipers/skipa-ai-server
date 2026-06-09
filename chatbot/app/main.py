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

from .config import BUSINESS_ROOT, DATA_ROOT, MINIO_SYNC_ON_STARTUP, PATENT_APPLICATION_ROOT, PATENTS_ROOT, PRE_EVAL_ROOT, SHARED_DATA_ROOT
from .routers.pre_eval import router as pre_eval_router
from .routers.chatbot import (
    agent_router,
    application_router,
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
        "## SKIPA 특허 챗봇 · 출원 도우미 · 사전평가 통합 API\n\n"
        "### 주요 API (신규 연동 시 사용)\n"
        "| 태그 | 설명 | 대표 엔드포인트 |\n"
        "|------|------|-----------------|\n"
        "| **patent-chat** | 특허 챗봇 답변 | `POST /api/v1/patent-chat/chat` |\n"
        "| **application** | 특허 출원 도우미 | `POST /api/v1/application/chat` |\n"
        "| **pre-eval** | 출원 전 사전평가 | `POST /api/v1/pre-eval/evaluate` |\n\n"
        "### 운영 API\n"
        "| 태그 | 설명 |\n"
        "|------|------|\n"
        "| **chatbot** | 데이터 조회·MinIO·Qdrant·Vectorstore·Blue-Green 관리 |\n"
        "| **wiki** | Wiki 데이터 감사·승인·분야별 관리 |\n"
        "| **agent** | patent-chat alias (내부 호환용) |\n"
    ),
    version="1.0.0",
    openapi_tags=[
        # ── 주요 사용자 대면 API ──────────────────────────────────────────────
        {
            "name": "patent-chat",
            "description": (
                "**[주요 API] 특허 챗봇 답변 생성**\n\n"
                "LangGraph 의도 라우팅 → Qdrant Hybrid Retrieval → OpenAI 답변 생성 파이프라인을 사용합니다.\n\n"
                "- **특허 선택 채팅**: `POST /chat` — `patent_id` 지정 시 해당 특허 원문·보고서 우선 검색\n"
                "- **전체 특허 채팅**: `POST /global/chat` — 전체 특허 DB에서 관련 근거 탐색\n"
                "- **인덱스 재생성**: 특허 데이터 추가·수정 후 `/reindex` 호출\n\n"
                "신규 연동 시 이 태그의 API를 사용하세요."
            ),
        },
        {
            "name": "application",
            "description": (
                "**[주요 API] 특허 출원 도우미**\n\n"
                "공식 출원 자료팩과 실패특허 케이스를 기반으로 출원 절차·거절 사유 대응·재심사 전략을 안내합니다.\n\n"
                "- **채팅**: `POST /chat` — 출원 절차 질문 답변\n"
                "- **실패특허 업로드**: `POST /failed-patents/upload` — PDF 업로드 후 케이스 전용 vectorstore 생성\n"
                "- **보고서 생성**: `POST /failed-patents/{case_id}/report/generate` — AI 재평가 보고서 생성"
            ),
        },
        {
            "name": "pre-eval",
            "description": (
                "**[주요 API] 출원 전 사전평가**\n\n"
                "발명 정보(특허명·기술 설명·청구항)를 입력하면 AI가 권리성·시장성·사업성을 사전 진단하고 "
                "평가 보고서 전용 vectorstore 기반 챗봇을 제공합니다.\n\n"
                "- **평가 실행**: `POST /evaluate`\n"
                "- **케이스 채팅**: `POST /cases/{case_id}/chat`"
            ),
        },
        # ── 운영 · 관리 API ───────────────────────────────────────────────────
        {
            "name": "wiki",
            "description": (
                "**Wiki 감사 · 분야별 Vectorstore 관리**\n\n"
                "특허 데이터를 기술 분야별로 분류하고 품질을 감사합니다. "
                "사람이 검토·승인한 wiki 데이터만 챗봇 근거로 사용됩니다.\n\n"
                "- 지원 분야: `반도체_전자`, `소프트웨어_IT`, `스마트_팩토리`, `특허출원_절차`\n"
                "- **감사 흐름**: `POST /audit` → 사람 검토 → `POST /audit-apply` → vectorstore 갱신\n"
                "- **자동 갱신**: `POST /audit-auto-refresh` — 저품질 데이터 자동 제외 후 vectorstore 재빌드"
            ),
        },
        {
            "name": "chatbot",
            "description": (
                "**데이터 조회 · 인프라 관리 API**\n\n"
                "특허 데이터 조회, MinIO 동기화, Qdrant 연결 확인, "
                "Vectorstore Blue-Green 관리, 전처리 파이프라인 실행을 담당합니다.\n\n"
                "| 그룹 | 엔드포인트 |\n"
                "|------|----------|\n"
                "| 특허 데이터 | `/patents`, `/patents/{id}`, `/patents/{id}/chunks` |\n"
                "| 저장소 연결 | `/minio/status`, `/minio/sync`, `/qdrant/status` |\n"
                "| Vectorstore | `/vectorstore/status`, `/vectorstore/full-rebuild` |\n"
                "| Blue-Green | `/bluegreen/status`, `/bluegreen/refresh` |\n"
                "| 전처리 | `/preprocess/run`, `/preprocess/status` |\n"
                "| Wiki 감사 | `/wiki-audit/run`, `/wiki-audit/apply` |"
            ),
        },
        {
            "name": "system",
            "description": "서비스 헬스체크 · 루트 확인",
        },
        # ── 내부 호환용 (Alias) ───────────────────────────────────────────────
        {
            "name": "agent",
            "description": (
                "**[내부 alias] patent-chat API 경로 별칭**\n\n"
                "`/api/v1/agent/*` 는 `/api/v1/patent-chat/*` 와 동일한 핸들러에 연결됩니다. "
                "신규 개발 시 `patent-chat` 태그의 API를 사용하세요."
            ),
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
app.include_router(application_router)
app.include_router(pre_eval_router)

if STATIC_ROOT.exists():
    app.mount("/ui/static", StaticFiles(directory=str(STATIC_ROOT)), name="ui_static")

if DATA_ROOT.exists():
    app.mount("/files/data", StaticFiles(directory=str(DATA_ROOT)), name="data_files")

if PATENTS_ROOT.exists():
    app.mount("/files/patents", StaticFiles(directory=str(PATENTS_ROOT)), name="patent_files")

if BUSINESS_ROOT.exists():
    app.mount("/files/business", StaticFiles(directory=str(BUSINESS_ROOT)), name="business_files")

if PATENT_APPLICATION_ROOT.exists():
    app.mount("/files/application", StaticFiles(directory=str(PATENT_APPLICATION_ROOT)), name="application_files")

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
        "patent_application_root": str(PATENT_APPLICATION_ROOT),
        "patent_application_root_exists": PATENT_APPLICATION_ROOT.exists(),
    }
