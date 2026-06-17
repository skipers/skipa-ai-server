from __future__ import annotations

from pre_application_valuation.generation_service import (
    numeric_pre_evaluation_ids,
    output_key_for_pre_evaluation,
    request_from_payload,
)


def test_output_key_for_pre_evaluation_supports_default_and_custom_templates() -> None:
    assert output_key_for_pre_evaluation(42) == "pre-evaluations/42/report.json"
    assert (
        output_key_for_pre_evaluation("abc", "custom/{preEvaluationId}/result.json")
        == "custom/abc/result.json"
    )


def test_numeric_pre_evaluation_ids_extracts_only_report_keys() -> None:
    keys = [
        "pre-evaluations/1/report.json",
        "/pre-evaluations/9/report.json",
        "pre-evaluations/not-number/report.json",
        "pre-evaluations/3/draft.json",
    ]

    assert numeric_pre_evaluation_ids(keys) == [1, 9]


def test_request_from_payload_maps_backend_field_names() -> None:
    request = request_from_payload(
        {
            "title": "센서 융합 안전 진단",
            "technicalDescription": "센서 데이터를 융합해 이상 상태를 감지한다.",
            "claims": ["센서 데이터를 수집하는 단계"],
            "relatedBusiness": "설비 유지보수",
            "targetCountries": ["KR", "US"],
        }
    )

    assert request.patent_name == "센서 융합 안전 진단"
    assert request.technology_description == "센서 데이터를 융합해 이상 상태를 감지한다."
    assert request.target_countries == ["KR", "US"]

