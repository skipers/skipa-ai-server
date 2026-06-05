"""Agent API router source restoration."""

from __future__ import annotations

from fastapi import APIRouter

from ..agents.graph import run_chat_agent
from ..schemas import AnswerResponse, SearchRequest, SearchResponse
from ..store import search_chunks


router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/answer", response_model=AnswerResponse)
def answer(request: SearchRequest) -> dict:
    return run_chat_agent(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )


@router.post("/query", response_model=SearchResponse)
def query(request: SearchRequest) -> dict:
    return search_chunks(
        request.query,
        patent_id=request.patent_id,
        source_types=set(request.source_types or []) or None,
        top_k=request.top_k,
    )
