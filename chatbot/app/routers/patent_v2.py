"""외부 공개 특허별 API — 프론트엔드 연결용.

엔드포인트 3개만 노출:
  GET  /api/v2/patents                     특허 목록 (드롭다운)
  GET  /api/v2/patents/{patent_id}/report  특허 평가 보고서
  POST /api/v2/patents/{patent_id}/chat    특허별 챗봇 답변
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..agents.graph import run_chat_agent
from ..config import SHARED_DATA_ROOT
from ..store import list_patents

router = APIRouter(prefix="/api/v2/patents", tags=["patents-v2"])


# ── 스키마 ──────────────────────────────────────────────────────

class PatentSummary(BaseModel):
    patent_id: str
    title:     str
    score:     int | None   = Field(None, description="100점 만점 종합 점수")
    grade:     str | None   = Field(None, description="S/A/B+/B/C 등급")


class PatentListResponse(BaseModel):
    count: int
    items: list[PatentSummary]


class ChatMessage(BaseModel):
    role:    str = Field(..., description="'user' 또는 'assistant'")
    content: str


class ChatRequest(BaseModel):
    question:     str                  = Field(..., min_length=1, description="사용자 질문")
    chat_history: list[ChatMessage]    = Field(default_factory=list, description="직전 대화 (최대 10턴)")


class SourceCard(BaseModel):
    title:       str | None = None
    source_type: str
    snippet:     str
    page_no:     int | None = None
    url:         str | None = None


class ChatResponse(BaseModel):
    answer:  str
    sources: list[SourceCard] = Field(default_factory=list)


# ── 헬퍼 ──────────────────────────────────────────────────────

def _patent_root() -> Path:
    return Path(SHARED_DATA_ROOT) if SHARED_DATA_ROOT else Path("data/patent")


def _load_report(patent_id: str) -> dict:
    path = _patent_root() / patent_id / "report.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"report.json not found: {patent_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_from_report(patent_id: str, title: str) -> PatentSummary:
    try:
        rep  = _load_report(patent_id).get("report") or {}
        s1   = rep.get("section_1_summary") or {}
        score = s1.get("overall_score_out_of_100")
        grade = s1.get("overall_grade")
        title = (rep.get("patent") or {}).get("title") or title
    except Exception:
        score = grade = None
    return PatentSummary(patent_id=patent_id, title=title, score=score, grade=grade)


# ── 엔드포인트 ──────────────────────────────────────────────────

@router.get(
    "",
    response_model=PatentListResponse,
    summary="특허 목록",
    description="프론트엔드 드롭다운용 특허 목록. 점수·등급 포함.",
)
def get_patents() -> PatentListResponse:
    raw = list_patents()
    items = [_summary_from_report(p["patent_id"], p.get("title") or p["patent_id"]) for p in raw]
    return PatentListResponse(count=len(items), items=items)


@router.get(
    "/{patent_id}/report",
    summary="특허 평가 보고서",
    description="해당 특허의 평가 보고서(report.json) 전체를 반환합니다.",
)
def get_report(patent_id: str) -> dict[str, Any]:
    return _load_report(patent_id)


@router.post(
    "/{patent_id}/chat",
    response_model=ChatResponse,
    summary="특허별 챗봇 답변",
    description=(
        "선택한 특허를 기준으로 원문·보고서·wiki 근거를 검색해 답변합니다.\n\n"
        "`chat_history`를 전달하면 후속 질문 컨텍스트가 유지됩니다."
    ),
)
def chat(patent_id: str, req: ChatRequest) -> ChatResponse:
    history = [{"role": m.role, "content": m.content} for m in req.chat_history[-10:]]
    result  = run_chat_agent(req.question, patent_id=patent_id, chat_history=history)

    sources = []
    for card in (result.get("source_cards") or []):
        sources.append(SourceCard(
            title       = card.get("display_title") or card.get("title"),
            source_type = card.get("source_type", ""),
            snippet     = (card.get("snippet") or "")[:400],
            page_no     = card.get("page_no"),
            url         = card.get("url"),
        ))

    return ChatResponse(answer=result.get("answer") or "", sources=sources)
