"""Page router source restoration."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["pages"])


@router.get("/chat")
def chat_page() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parents[1] / "static" / "index.html")
