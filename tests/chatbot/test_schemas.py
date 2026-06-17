from __future__ import annotations

import pytest
from pydantic import ValidationError

from chatbot.app.schemas import PreEvalReportCompleteRequest, SearchRequest


def test_pre_eval_report_complete_resolves_case_id_from_legacy_patent_id() -> None:
    request = PreEvalReportCompleteRequest.model_validate({"patent_id": "case-7"})

    assert request.resolved_case_id == "case-7"


def test_pre_eval_report_complete_requires_identifier() -> None:
    with pytest.raises(ValidationError):
        PreEvalReportCompleteRequest.model_validate({})


def test_search_request_bounds_top_k() -> None:
    assert SearchRequest.model_validate({"query": "등록 가능성", "top_k": 3}).top_k == 3
    with pytest.raises(ValidationError):
        SearchRequest.model_validate({"query": "등록 가능성", "top_k": 0})

