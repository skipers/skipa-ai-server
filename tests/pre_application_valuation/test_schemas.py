from __future__ import annotations

import pytest
from pydantic import ValidationError

from pre_application_valuation.schemas import PreApplicationValuationRequest


def test_request_accepts_backend_aliases_and_normalizes_lists() -> None:
    request = PreApplicationValuationRequest.model_validate(
        {
            "patentName": "  AI 기반 불량 검출 시스템  ",
            "technologyDescription": " 이미지 기반으로 제조 불량을 탐지한다. ",
            "claims": "1. 이미지 수집\n\n2. 결함 분류",
            "relatedBusiness": " 스마트팩토리 ",
            "targetCountries": "KR, US; JP\nKR",
        }
    )

    assert request.patent_name == "AI 기반 불량 검출 시스템"
    assert request.technology_description == "이미지 기반으로 제조 불량을 탐지한다."
    assert request.claims == ["1. 이미지 수집", "2. 결함 분류"]
    assert request.related_business == "스마트팩토리"
    assert request.target_countries == ["KR", "US", "JP"]


def test_request_rejects_empty_required_text() -> None:
    with pytest.raises(ValidationError):
        PreApplicationValuationRequest.model_validate(
            {
                "patentName": " ",
                "technologyDescription": "설명",
            }
        )

