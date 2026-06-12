"""보고서 산출물 파일명 규칙입니다."""

from __future__ import annotations

import re
from typing import Any


def safe_report_filename_from_result(result: dict[str, Any]) -> str:
    """workflow 결과에서 등록번호를 찾아 ``{등록번호}.json`` 파일명을 반환합니다."""
    return f"{safe_registration_number_from_result(result)}.json"


def safe_registration_number_from_result(result: dict[str, Any]) -> str:
    """workflow 결과에서 파일/디렉터리명으로 안전한 등록번호를 반환합니다."""
    registration_number = _registration_number_from_result(result)
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", registration_number).strip("._")
    return cleaned or "patent"


def _registration_number_from_result(result: dict[str, Any]) -> str:
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    valuation = result.get("valuation") if isinstance(result.get("valuation"), dict) else {}
    report = result.get("report") if isinstance(result.get("report"), dict) else {}
    patent = report.get("patent") if isinstance(report.get("patent"), dict) else {}
    meta = valuation.get("meta") if isinstance(valuation.get("meta"), dict) else {}

    candidates = [
        validation.get("patent_id"),
        patent.get("registration_number"),
        patent.get("patent_id"),
        valuation.get("patent_id"),
        meta.get("registration_number"),
        meta.get("application_number"),
    ]
    for value in candidates:
        text = str(value or "").strip()
        if text and text.lower() != "unknown":
            return text
    return "patent"
