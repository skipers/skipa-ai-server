"""Request and response schemas for chatbot Swagger checks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색 또는 질의 문장")
    patent_id: str | None = Field(None, description="특정 특허 폴더만 검색하려면 지정")
    source_types: list[str] | None = Field(
        None,
        description="ORIGINAL_PDF, REPORT_PDF, WIKI 등 source_type 필터",
    )
    top_k: int = Field(5, ge=1, le=50, description="반환할 검색 결과 수")


class ChatRequest(BaseModel):
    patent_id: str | None = Field(None, description="특허 상세 화면에서 전달되는 현재 특허 ID")
    question: str = Field(..., min_length=1, description="사용자 질문")
    user_id: str | None = Field(None, description="질문자 식별자")
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")
    context_patent_id: str | None = Field(None, description="프론트엔드가 기억한 현재 대화 기준 특허 ID")


class PatentApplicationChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="특허 출원 도우미 질문")
    user_id: str | None = Field(None, description="질문자 식별자")
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")
    top_k: int = Field(6, ge=1, le=20, description="공식팩 근거 검색 개수")
    refresh_index: bool = Field(False, description="질문 전 출원 공식팩 인덱스를 다시 생성")


class PatentApplicationDownloadRequest(BaseModel):
    force: bool = Field(False, description="이미 다운로드한 파일도 다시 다운로드")
    timeout: int = Field(20, ge=3, le=60, description="URL별 다운로드 timeout 초")
    limit: int | None = Field(None, ge=1, le=80, description="이번 실행에서 시도할 URL 개수 제한")


class FeedbackRequest(BaseModel):
    question: str
    answer: str | None = None
    rating: str
    reason: str | None = None
    user_id: str | None = None
    patent_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ReindexRequest(BaseModel):
    patent_id: str
    force_rebuild: bool = Field(True, description="기존 FAISS가 있어도 전처리/인덱스를 다시 생성")
    refresh_reviewed_vectorstore: bool = Field(
        False,
        description="레거시 FAISS 재생성 후 사람 승인 데이터 기반 local vectorstore도 함께 갱신",
    )


class BusinessReindexRequest(BaseModel):
    force_rebuild: bool = Field(True, description="기존 FAISS가 있어도 다시 생성")
    refresh_reviewed_vectorstore: bool = Field(
        False,
        description="레거시 FAISS 재생성 후 사람 승인 데이터 기반 local vectorstore도 함께 갱신",
    )


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


class AnswerSourceCard(BaseModel):
    label: str
    title: str | None = None
    source_type: str
    page_no: int | None = None
    url: str | None = None
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    query: str
    patent_id: str | None
    answer: str
    source_cards: list[AnswerSourceCard] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class AuditApplyRequest(BaseModel):
    audit_id: str | None = Field(None, description="대상 audit_id. 비우면 가장 최근 감사 결과 사용")
    exclude_finding_ids: list[str] | None = Field(
        None,
        description="사람이 최종 제외하기로 확인한 finding_id 목록. null이면 기본 exclude 후보를 모두 제외",
    )
    reviewer: str | None = Field(None, description="검토자 이름 또는 식별자")
    notes: str | None = Field(None, description="검토 메모")
    refresh_vectorstore: bool = Field(True, description="승인 Markdown 저장 후 vectorstore 갱신 여부")


class WikiAgentRunRequest(BaseModel):
    mode: Literal["audit", "review", "apply", "auto_refresh", "refresh", "status"] = Field(
        "audit",
        description="실행할 Wiki LangGraph agent mode",
    )
    audit_id: str | None = Field(None, description="review/apply 대상 audit_id. 비우면 최신 감사 사용")
    exclude_finding_ids: list[str] | None = Field(
        None,
        description="apply mode에서 제외할 finding_id 목록. null이면 기본 exclude 후보 제외",
    )
    reviewer: str | None = Field(None, description="검토자 이름 또는 식별자")
    notes: str | None = Field(None, description="검토 메모")
    refresh_vectorstore: bool | None = Field(
        None,
        description="audit/apply 후 vectorstore 갱신 여부. null이면 mode별 기본값 사용",
    )
