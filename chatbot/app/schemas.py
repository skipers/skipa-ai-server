"""Request and response schemas for chatbot Swagger checks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색 또는 질의 문장")
    patent_id: str | None = Field(None, description="특정 특허 폴더만 검색하려면 지정")
    source_types: list[str] | None = Field(
        None,
        description="ORIGINAL_PDF, REPORT_PDF, WIKI 등 source_type 필터",
    )
    top_k: int = Field(5, ge=1, le=50, description="반환할 검색 결과 수")


class SearchHit(BaseModel):
    patent_id: str
    score: float
    excerpt: str
    page_content: str
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    mode: str
    patent_id: str | None
    top_k: int
    hit_count: int
    hits: list[SearchHit]


class AuditApplyRequest(BaseModel):
    audit_id: str | None = Field(None, description="대상 audit_id. 비우면 가장 최근 감사 결과 사용")
    exclude_finding_ids: list[str] | None = Field(
        None,
        description="사람이 최종 제외하기로 확인한 finding_id 목록. null이면 기본 exclude 후보를 모두 제외",
    )
    reviewer: str | None = Field(None, description="검토자 이름 또는 식별자")
    notes: str | None = Field(None, description="검토 메모")
    refresh_vectorstore: bool = Field(True, description="승인 Markdown 저장 후 vectorstore 갱신 여부")
