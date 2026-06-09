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

    registration_number: str
    report_id: str | None = None
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

    registration_number: str
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
