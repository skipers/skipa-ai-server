"""Request and response schemas for chatbot Swagger checks."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatHistoryItem(BaseModel):
    """Minimal chat history item accepted by public chat APIs."""

    role: Literal["user", "assistant", "system"] | None = Field(
        None,
        description="메시지 작성 주체. UI 대화 이력을 그대로 넘길 때 사용",
    )
    content: str | None = Field(None, description="메시지 본문")
    question: str | None = Field(None, description="이전 사용자 질문")
    query: str | None = Field(None, description="이전 검색/질의 문장")
    answer: str | None = Field(None, description="이전 챗봇 답변")
    patent_id: str | None = Field(None, description="이전 대화가 참조한 특허 또는 케이스 ID")
    resolved_patent_id: str | None = Field(None, description="이전 턴에서 확정된 특허 또는 케이스 ID")
    source_card_patent_ids: list[str] | None = Field(None, description="이전 답변 근거 카드의 특허 ID 목록")
    metrics: dict[str, Any] | None = Field(None, description="이전 응답 metrics")


class ReEvalChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chat_history": [],
                    "question": "이 특허에 대해서 자세하게 알려줘",
                    "user_id": "user-1",
                }
            ]
        }
    )

    chat_history: list[ChatHistoryItem] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")
    question: str = Field(..., min_length=1, description="사용자 질문")
    user_id: str | None = Field(None, description="질문자 식별자. 없으면 생략 가능")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색 또는 질의 문장")
    patent_id: str | None = Field(None, description="특정 특허 폴더만 검색하려면 지정")
    source_types: list[str] | None = Field(
        None,
        description="ORIGINAL_PDF, REPORT_PDF, WIKI 등 source_type 필터",
    )
    top_k: int = Field(5, ge=1, le=50, description="반환할 검색 결과 수")


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "patent_id": "10-2142205",
                    "question": "이 특허에 대해서 자세하게 알려줘",
                    "user_id": "user-1",
                    "chat_history": [],
                }
            ]
        }
    )

    patent_id: str | None = Field(None, description="재평가 특허 ID. 특허 상세/보고서 채팅이면 전달")
    question: str = Field(..., min_length=1, description="사용자 질문")
    user_id: str | None = Field(None, description="질문자 식별자. 없으면 생략 가능")
    chat_history: list[ChatHistoryItem] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")


class PreEvalReportCompleteRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"case_id": "12"}, {"patent_id": "12"}]}
    )

    case_id: str | None = Field(None, min_length=1, description="백엔드가 부여한 사전평가 케이스 ID")
    patent_id: str | None = Field(None, min_length=1, description="레거시 필드. 들어오면 case_id처럼 처리")

    @model_validator(mode="after")
    def require_case_identifier(self) -> "PreEvalReportCompleteRequest":
        if not (self.case_id or self.patent_id):
            raise ValueError("case_id 또는 patent_id 중 하나는 필요합니다.")
        return self

    @property
    def resolved_case_id(self) -> str:
        return str(self.case_id or self.patent_id or "").strip()


class PreEvalReportCompleteResponse(BaseModel):
    status: Literal["indexed"]
    case_id: str | None = None
    patent_id: str
    collection: str
    document_count: int
    source_key: str | None = None
    indexed_at: str


class PreEvalChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chat_history": [],
                    "question": "이 사전평가 보고서의 주요 리스크를 알려줘",
                    "user_id": "user-1",
                }
            ]
        }
    )

    question: str = Field(..., min_length=1, description="사전평가 보고서에 대해 물어볼 질문")
    user_id: str | None = Field(None, description="질문자 식별자. 없으면 생략 가능")
    chat_history: list[ChatHistoryItem] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")
    top_k: int = Field(8, ge=1, le=50, description="검색에 사용할 보고서 청크 수")


class PreprocessRunRequest(BaseModel):
    mode: Literal[
        "normalize_wiki",
        "refresh_vectorstore",
        "auto_audit_refresh",
        "audit",
        "visual_index",
        "nightly_reindex",
        "shared_index",
        "all",
    ] = Field(
        "refresh_vectorstore",
        description=(
            "실행할 전처리/리프레시 작업. shared_index: PROJECT_ROOT/data/ 특허 색인, "
            "visual_index: 신규 특허 원본 PDF의 표/도면/이미지만 Qdrant에 증분 색인"
        ),
    )
    use_reviewed: bool = Field(True, description="vectorstore refresh 시 승인 데이터만 사용할지 여부")


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
    force_rebuild: bool = Field(True, description="기존 인덱스가 있어도 Qdrant 인덱스를 다시 생성")
    refresh_reviewed_vectorstore: bool = Field(
        False,
        description="사람 승인 데이터 기반 Qdrant vectorstore도 함께 갱신",
    )


class BusinessReindexRequest(BaseModel):
    force_rebuild: bool = Field(True, description="기존 인덱스가 있어도 Qdrant 인덱스를 다시 생성")
    refresh_reviewed_vectorstore: bool = Field(
        False,
        description="사람 승인 데이터 기반 Qdrant vectorstore도 함께 갱신",
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
    display_title: str | None = None
    source_type: str
    page_no: int | None = None
    url: str | None = None
    location_label: str | None = None
    source_path: str | None = None
    match_terms: list[str] = Field(default_factory=list)
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    query: str
    patent_id: str | None
    answer: str
    source_cards: list[AnswerSourceCard] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class PublicAnswerSourceCard(BaseModel):
    """Source card shape returned by public chat APIs.

    Internal retrieval metadata is intentionally omitted so backend chat logs can
    persist `source_cards` directly without storing debug payloads.
    """

    label: str
    title: str | None = None
    display_title: str | None = None
    source_type: str
    page_no: int | None = None
    url: str | None = None
    location_label: str | None = None
    source_path: str | None = None
    match_terms: list[str] = Field(default_factory=list)
    snippet: str


class PublicChatResponse(BaseModel):
    query: str
    patent_id: str | None
    answer: str
    source_cards: list[PublicAnswerSourceCard] = Field(default_factory=list)
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
