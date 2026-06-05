# -*- coding: utf-8 -*-

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnswerScope(str, Enum):
    PATENT_LOCAL = "PATENT_LOCAL"
    PATENT_WEB = "PATENT_WEB"
    BUSINESS = "BUSINESS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class SourceType(str, Enum):
    ORIGINAL_PDF = "ORIGINAL_PDF"
    REPORT_PDF = "REPORT_PDF"
    BUSINESS_DOC = "BUSINESS_DOC"
    WEB = "WEB"


class ChatRequest(BaseModel):
    patent_id: Optional[str] = Field(
        default=None,
        description="특허 상세 화면에서 전달되는 현재 특허 ID. 특허 개별 질문에는 필수입니다.",
    )
    question: str
    user_id: Optional[str] = None
    chat_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="최근 대화 내역. 후속 질문에서 이전 특허/검색 결과 맥락을 복원하는 데 사용합니다.",
    )
    context_patent_id: Optional[str] = Field(
        default=None,
        description="프론트엔드가 기억한 현재 대화 기준 특허 ID.",
    )


class FeedbackRequest(BaseModel):
    question: str
    answer: Optional[str] = None
    rating: str
    reason: Optional[str] = None
    user_id: Optional[str] = None
    patent_id: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ReindexRequest(BaseModel):
    patent_id: str
    force_rebuild: bool = True


class BusinessReindexRequest(BaseModel):
    force_rebuild: bool = True


class SourceCard(BaseModel):
    label: str
    title: Optional[str] = None
    source_type: str
    page_no: Optional[int] = None
    url: Optional[str] = None
    chunk_id: str
    snippet: str
    document_type: Optional[str] = None


class Metrics(BaseModel):
    scope: str
    patent_id: Optional[str] = None
    local_context_count: int = 0
    web_context_count: int = 0
    confidence_score: float = 0.0
    vector_ms: int = 0
    bm25_ms: int = 0
    retrieval_ms: int = 0
    web_search_ms: int = 0
    llm_ms: int = 0
    total_ms: int = 0


class ChatResponse(BaseModel):
    answer: str
    source_cards: List[SourceCard] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
