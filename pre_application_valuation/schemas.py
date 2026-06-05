"""Schemas for pre-application idea/patent valuation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PreApplicationValuationRequest(BaseModel):
    """Lightweight text input collected before patent filing."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    patent_name: str = Field(..., alias="patentName", description="특허명")
    technology_description: str = Field(..., alias="technologyDescription", description="기술 설명")
    claims: list[str] = Field(default_factory=list, description="청구항")
    related_business: str = Field(default="", alias="relatedBusiness", description="관련 사업")
    target_countries: list[str] = Field(default_factory=list, alias="targetCountries", description="출원 예정 국가")

    @field_validator("patent_name", "technology_description")
    @classmethod
    def _required_text(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("필수 텍스트 입력이 비어 있습니다.")
        return text

    @field_validator("claims", mode="before")
    @classmethod
    def _normalize_claims(cls, value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            parts = value.replace("\r\n", "\n").split("\n")
        elif isinstance(value, list):
            parts = value
        else:
            parts = [value]
        return [str(item).strip() for item in parts if str(item).strip()]

    @field_validator("target_countries", mode="before")
    @classmethod
    def _normalize_countries(cls, value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            raw_items = value.replace("\n", ",").replace(";", ",").split(",")
        elif isinstance(value, list):
            raw_items = value
        else:
            raw_items = [value]
        countries: list[str] = []
        for item in raw_items:
            text = str(item).strip()
            if text and text not in countries:
                countries.append(text)
        return countries

    @field_validator("related_business", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str:
        return str(value or "").strip()


class SavedValuationResponse(BaseModel):
    """API wrapper that reports where the result JSON was saved."""

    status: str
    output_path: str
    result: dict[str, Any]
