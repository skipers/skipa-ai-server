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


def _seconds_until_midnight_kst() -> float:
    """현재 시각부터 다음 KST 자정까지 남은 초."""
    now = datetime.now(KST)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (midnight - now).total_seconds()


async def _nightly_reindex_loop() -> None:
    """매일 00:00 KST 에 nightly_reindex_all 을 실행하는 백그라운드 태스크."""
    while True:
        wait = _seconds_until_midnight_kst()
        logger.info("nightly reindex 스케줄: %.0f초 후 (다음 KST 자정)", wait)
        await asyncio.sleep(wait)
        try:
            from .vectorstore import nightly_reindex_all
            logger.info("nightly reindex 시작")
            result = nightly_reindex_all()
            logger.info("nightly reindex 완료: status=%s", result.get("status"))
        except Exception as exc:
            logger.error("nightly reindex 실패: %s", exc)


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
    task = asyncio.create_task(_nightly_reindex_loop())
    logger.info("nightly reindex 스케줄러 시작 (매일 00:00 KST)")
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
