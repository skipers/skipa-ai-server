from __future__ import annotations

from core.schemas import PatentEvaluationInput, normalize_patent_input


def test_normalize_patent_input_accepts_nested_patent_payload() -> None:
    normalized = normalize_patent_input(
        {
            "patent": {
                "meta": {
                    "registration_number": "10-1234567",
                    "title": "센서 융합 안전 진단",
                    "ipc": "G06Q 10/04 (2024.01)",
                    "inventors": "홍길동; 김영희",
                },
                "specification": {
                    "technical_field": "설비 안전 진단",
                    "problem_to_solve": "이상 징후 탐지가 늦다",
                    "solution": "센서 데이터를 융합한다",
                },
                "claims_text": {
                    "1": "센서 데이터를 수집하는 단계",
                    "2": {"type": "종속항", "category": "분석", "text": "이상 점수를 산출하는 단계"},
                },
            }
        }
    )

    assert normalized["patent_id"] == "10-1234567"
    assert normalized["meta"]["title"] == "센서 융합 안전 진단"
    assert normalized["meta"]["ipc"] == ["G06Q10/04"]
    assert normalized["meta"]["inventors"] == ["홍길동", "김영희"]
    assert normalized["claims_text"]["claim_1"]["type"] == "독립항"
    assert "센서 데이터를 융합한다" in normalized["description_summary"]


def test_patent_evaluation_input_validate_reports_missing_core_fields() -> None:
    patent = PatentEvaluationInput.from_dict({"patent_id": "", "meta": {"title": ""}})

    errors = patent.validate()

    assert "patent_id 또는 meta.registration_number가 필요합니다." in errors
    assert "meta.title 또는 title이 필요합니다." in errors
