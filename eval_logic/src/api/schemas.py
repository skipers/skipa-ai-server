"""특허 의사결정 API 요청/응답 스키마입니다."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PatentDecisionOptionsRequest(BaseModel):
    """agentic workflow 실행 옵션입니다."""

    enable_market: bool = Field(default=True, description="KOSIS 시장 성장률 조회 활성화")
    enable_auto: bool = Field(default=True, description="규칙 기반 자동 점수 활성화")
    enable_llm: bool = Field(default=False, description="LLM 43개 항목 평가 활성화")
    enable_pdf_metadata_extraction: bool = Field(default=True, description="PDF 메타데이터 추출 활성화")
    enable_business_rag: bool = Field(default=False, description="제품/사업화 RAG 분석 활성화")
    enable_similar_analysis: bool = Field(default=True, description="유사 특허 분석 활성화")
    similar_use_llm: bool = Field(default=False, description="유사 특허 비교 요약에 LLM 사용")
    rag_top_k: int | None = Field(default=None, description="RAG 검색 top_k")
    fail_on_validation_error: bool = Field(default=True, description="검증 오류 시 workflow 중단")
    enable_human_review: bool = Field(default=False, description="위험/저신뢰 단계에서 Human-in-the-loop 중단 활성화")
    human_review_low_score_threshold: float = Field(default=2.8, description="사람 검토를 요청할 종합 평균 점수 기준")
    human_review_low_confidence_labels: list[str] = Field(
        default_factory=lambda: ["low", "medium"],
        description="사람 검토를 요청할 의사결정 confidence 값",
    )


class PatentReportRequest(BaseModel):
    """서비스용 특허 유지/포기 보고서 생성 요청입니다.

    외부 서비스 API에서는 RAG, LLM, KOSIS/KIPRIS 등 내부 도구 사용 여부를
    옵션으로 노출하지 않고 기본 workflow를 실행합니다.
    """

    patent: dict[str, Any] = Field(..., description="특허 입력 JSON")


class PatentDecisionRequest(BaseModel):
    """개발/디버그용 특허 유지/포기 의사결정 요청입니다."""

    patent_data: dict[str, Any] = Field(..., description="특허 입력 JSON")
    options: PatentDecisionOptionsRequest = Field(default_factory=PatentDecisionOptionsRequest)


class PatentDecisionResponse(BaseModel):
    """특허 유지/포기 의사결정 응답입니다."""

    status: str
    workflow_type: str
    elapsed_seconds: float
    validation: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    valuation: dict[str, Any] | None = None
    similar_analysis: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    human_reviews: list[dict[str, Any]] = Field(default_factory=list)
    human_review_pending: dict[str, Any] | None = None
    interrupts: list[dict[str, Any]] = Field(default_factory=list)
    node_trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ReportJobResponse(BaseModel):
    """보고서 생성 Job 생성 응답입니다."""

    job_id: str
    status: str
    message: str
    status_url: str
    result_url: str
    input_path: str | None = None
    output_path: str | None = None


class ReportJobStatusResponse(BaseModel):
    """보고서 생성 Job 상태 응답입니다."""

    job_id: str
    status: str
    current_node: str | None = None
    progress: int = 0
    node_trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ReportJobResultResponse(BaseModel):
    """보고서 생성 Job 결과 응답입니다."""

    job_id: str
    status: str
    decision: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    workflow: dict[str, Any] | None = None
    artifacts: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


class PatentToolRequest(BaseModel):
    """특허 JSON 기반 tool 요청입니다."""

    patent: dict[str, Any] = Field(..., description="특허 입력 JSON")


class BusinessRagToolRequest(BaseModel):
    """사업화 RAG tool 요청입니다."""

    patent: dict[str, Any] = Field(..., description="특허 입력 JSON")
    query: str | None = Field(default=None, description="직접 지정할 RAG 질의")
    top_k: int | None = Field(default=5, description="검색 결과 수")


class PdfMetadataToolRequest(BaseModel):
    """샘플 PDF 경로 기반 메타데이터 추출 요청입니다."""

    source_pdf: str = Field(..., description="samples/patent_documents 아래 파일명 또는 서버 로컬 경로")
