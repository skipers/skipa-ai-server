"""Schemas for the prebuilt revaluation report API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportStorageRef(BaseModel):
    """Where the returned report JSON was loaded from."""

    backend: str = Field(..., description="minio 또는 local")
    bucket: str | None = Field(default=None, description="MinIO bucket")
    object_key: str | None = Field(default=None, description="MinIO object key")
    path: str | None = Field(default=None, description="local fallback path")


class StoredReportListItem(BaseModel):
    """미리 저장된 보고서 목록 항목입니다."""

    patent_id: str | None = None
    report_id: str | None = None
    registration_number: str | None = None
    title: str | None = None
    schema_version: str | None = None
    generated_at: str | None = None
    report_url: str
    storage: ReportStorageRef


class StoredReportListResponse(BaseModel):
    """미리 저장된 보고서 목록 응답입니다."""

    reports: list[StoredReportListItem] = Field(default_factory=list)


class StoredReportResponse(BaseModel):
    """미리 저장된 보고서 JSON 응답입니다."""

    patent_id: str | None = None
    report_id: str | None = None
    registration_number: str | None = None
    report: dict[str, Any]
    storage: ReportStorageRef


class PatentToolRequest(BaseModel):
    """특허 JSON 기반 tool 요청입니다."""

    patent: dict[str, Any] = Field(..., description="특허 입력 JSON")


class BusinessRagToolRequest(BaseModel):
    """사업화 RAG tool 요청입니다."""

    patent: dict[str, Any] = Field(..., description="특허 입력 JSON")
    query: str | None = Field(default=None, description="직접 지정할 RAG 질의")
    top_k: int | None = Field(default=5, description="검색 결과 수")


class ReportGenerationRequest(BaseModel):
    """Generate report.json from MinIO parsed.json, local parsed.json, or inline patent JSON."""

    patent: dict[str, Any] | None = Field(default=None, description="직접 전달하는 특허 입력 JSON")
    parsed_object_key: str | None = Field(default=None, alias="parsedObjectKey", description="MinIO parsed.json object key")
    local_path: str | None = Field(default=None, alias="localPath", description="로컬 parsed.json 경로")
    report_id: int | str | None = Field(default=None, alias="reportId", description="백엔드 report ID")
    patent_id: int | str | None = Field(default=None, alias="patentId", description="백엔드 patent ID")
    output_key_template: str | None = Field(
        default=None,
        alias="outputKeyTemplate",
        description="report.json 저장 object key template",
    )
    local_output: bool = Field(default=False, alias="localOutput", description="MinIO 대신 로컬 저장 여부")
    profile: str = Field(default="full", description="quick 또는 full")
    enable_market: bool | None = Field(default=None, alias="enableMarket")
    enable_llm: bool | None = Field(default=None, alias="enableLlm")
    enable_business_rag: bool | None = Field(default=None, alias="enableBusinessRag")
    similar_use_llm: bool | None = Field(default=None, alias="similarUseLlm")
    rag_top_k: int | None = Field(default=None, alias="ragTopK")

    model_config = {"populate_by_name": True}


class ReportGenerationResponse(BaseModel):
    """Generated report.json location and workflow result."""

    status: str | None = None
    report_id: int | str | None = Field(default=None, alias="reportId")
    patent_id: int | str | None = Field(default=None, alias="patentId")
    report_key: str | None = Field(default=None, alias="reportKey")
    source: dict[str, Any]
    storage: dict[str, Any]
    result: dict[str, Any]

    model_config = {"populate_by_name": True}
