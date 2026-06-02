"""FastAPI entrypoint for chatbot Swagger checks."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BUSINESS_ROOT, DATA_ROOT, PATENT_APPLICATION_ROOT, PATENTS_ROOT
from .routers.chatbot import (
    agent_router,
    application_router,
    legacy_rag_router,
    patent_chat_router,
    rag_router,
    router as chatbot_router,
    wiki_router,
)


STATIC_ROOT = Path(__file__).resolve().parent / "static"

app = FastAPI(
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
