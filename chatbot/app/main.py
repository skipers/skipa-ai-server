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
    title="SKIPA Chatbot API",
    description=(
        "Swagger에서 챗봇 데이터 연결, 특허별 원문/보고서/wiki/index 상태, "
        "그리고 RAG 검색용 query API를 확인하기 위한 FastAPI 앱입니다."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "system", "description": "헬스체크"},
        {"name": "chatbot", "description": "챗봇 데이터/검색 API"},
        {
            "name": "patent-chat",
            "description": "최고 성능 통합 특허 챗봇. LangGraph 의도 라우팅, Hybrid Retrieval, 특허별 wiki gate, 웹검색 보강을 한 경로로 제공합니다.",
        },
        {"name": "agent", "description": "Agent query alias"},
        {"name": "wiki", "description": "Wiki audit API"},
        {"name": "application", "description": "특허 출원 도우미 API"},
        {
            "name": "pre-eval",
            "description": "출원 전 사전평가 챗봇. 특허명·기술설명·청구항을 입력하면 AI가 사전평가 보고서를 생성하고, 보고서 전용 vectorstore로 채팅합니다.",
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
