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
    failed_patent_id: str | None = Field(
        None,
        description="출원 도우미가 참조할 실패특허 케이스 ID. 없으면 채팅이 시작되지 않고 업로드/선택을 요청",
    )
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="후속 질문 맥락용 최근 대화")
    top_k: int = Field(6, ge=1, le=20, description="공식팩 + 선택 실패특허 케이스 근거 검색 개수")
    refresh_index: bool = Field(False, description="질문 전 출원 공식팩 인덱스를 다시 생성")


class PatentApplicationDownloadRequest(BaseModel):
    force: bool = Field(False, description="이미 다운로드한 파일도 다시 다운로드")
    timeout: int = Field(20, ge=3, le=60, description="URL별 다운로드 timeout 초")
    limit: int | None = Field(None, ge=1, le=80, description="이번 실행에서 시도할 URL 개수 제한")
    include_embedded: bool = Field(True, description="웹 페이지 안의 PDF/HWP/DOC/XLS 등 첨부 문서 링크도 따라가서 다운로드")


class PatentApplicationPreprocessRequest(BaseModel):
    refresh_index: bool = Field(True, description="전처리 리포트 생성과 함께 출원 공식팩 vectorstore도 다시 생성")


class PatentApplicationFeedbackRequest(BaseModel):
    title: str = Field("특허 출원 실패/거절 대응 피드백", description="생성할 피드백 리포트 제목")
    patent_id: str | None = Field(None, description="기존 mapped_patent_reports의 특허 ID. 있으면 latest input/report를 연결")
    opinion_text: str | None = Field(None, description="거절의견/의견서/출원 실패 사유 텍스트")
    opinion_file_path: str | None = Field(None, description="서버 로컬 의견서/PDF 경로. data 또는 patent_application pack 하위만 허용")
    source_report_path: str | None = Field(None, description="기존 평가 보고서 JSON/PDF/HTML 경로. 비우면 patent_id의 latest report 사용")
    reviewer: str | None = Field(None, description="검토자")
    notes: str | None = Field(None, description="추가 메모")
    refresh_index: bool = Field(True, description="피드백 생성 후 출원 도우미 vectorstore refresh")


class PatentApplicationFailedCaseCreateRequest(BaseModel):
    case_id: str | None = Field(None, description="직접 지정할 실패특허 케이스 ID. 비우면 제목/시간 기반 자동 생성")
    title: str | None = Field(None, description="실패특허 케이스 제목")
    original_pdf_path: str = Field(..., description="서버 로컬 실패특허 원본 PDF 경로")
    rejection_reason_text: str | None = Field(None, description="거절/실패 사유 텍스트. 선택")
    rejection_file_path: str | None = Field(None, description="서버 로컬 거절의견서/사유서 파일 경로. 선택")
    reviewer: str | None = Field(None, description="등록자/검토자")
    notes: str | None = Field(None, description="케이스 메모")
    refresh_index: bool = Field(True, description="생성 후 해당 실패특허 케이스 전용 vectorstore 갱신")


class PatentApplicationFailedCaseReportSaveRequest(BaseModel):
    title: str | None = Field(None, description="저장할 재평가/피드백 보고서 제목")
    report: dict[str, Any] | None = Field(None, description="특허 재평가 API 결과 JSON")
    report_text: str | None = Field(None, description="보고서 Markdown/요약 텍스트")
    source_report_path: str | None = Field(None, description="이미 생성된 서버 로컬 보고서 파일 경로")
    refresh_index: bool = Field(True, description="보고서 저장 후 해당 실패특허 케이스 전용 vectorstore 갱신")


class PatentApplicationFailedCaseReportGenerateRequest(BaseModel):
    title: str | None = Field(None, description="생성할 실패특허 재평가 보고서 제목")
    enable_market: bool = Field(True, description="KOSIS/시장성 평가 활성화")
    enable_auto: bool = Field(True, description="규칙 기반 자동 점수 활성화")
    enable_llm: bool = Field(True, description="LLM 평가 활성화")
    enable_pdf_metadata_extraction: bool = Field(True, description="PDF 메타데이터 추출 활성화")
    enable_business_rag: bool = Field(True, description="사업화 RAG 분석 활성화")
    enable_similar_analysis: bool = Field(True, description="유사 특허 분석 활성화")
    similar_use_llm: bool = Field(True, description="유사 특허 비교 요약에 LLM 사용")
    rag_top_k: int | None = Field(5, ge=1, le=20, description="사업화 RAG 검색 top_k")
    fail_on_validation_error: bool = Field(True, description="입력 검증 실패 시 보고서 생성 중단")
    enable_human_review: bool = Field(False, description="위험/저신뢰 단계 Human-in-the-loop 중단 활성화")
    refresh_index: bool = Field(True, description="보고서 생성 후 해당 실패특허 케이스 전용 vectorstore 갱신")


class PreprocessRunRequest(BaseModel):
    mode: Literal[
        "normalize_wiki",
        "refresh_vectorstore",
        "auto_audit_refresh",
        "audit",
        "application_preprocess",
        "nightly_reindex",
        "all",
    ] = Field("refresh_vectorstore", description="실행할 전처리/리프레시 작업")
    use_reviewed: bool = Field(True, description="vectorstore refresh 시 승인 데이터만 사용할지 여부")
    refresh_application: bool = Field(True, description="all/application_preprocess 모드에서 출원 공식팩 index도 갱신")


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
