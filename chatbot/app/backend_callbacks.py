"""Backend internal API callbacks used by async integration workers."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import BACKEND_CALLBACK_TIMEOUT, BACKEND_INTERNAL_BASE_URL, INTERNAL_API_KEY


class BackendCallbackError(RuntimeError):
    """Raised when a backend internal callback fails."""

    def __init__(self, message: str, *, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def callbacks_configured() -> bool:
    return bool(BACKEND_INTERNAL_BASE_URL and INTERNAL_API_KEY)


def _internal_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not BACKEND_INTERNAL_BASE_URL:
        raise BackendCallbackError("BACKEND_INTERNAL_BASE_URL is not configured")
    if not INTERNAL_API_KEY:
        raise BackendCallbackError("INTERNAL_API_KEY is not configured")

    url = f"{BACKEND_INTERNAL_BASE_URL}{path}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"X-Internal-Api-Key": INTERNAL_API_KEY}
    if payload is not None:
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=BACKEND_CALLBACK_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise BackendCallbackError(
            f"Backend callback failed: {method} {path} HTTP {exc.code}",
            status_code=exc.code,
            response_body=detail,
        ) from exc
    except (OSError, URLError, TimeoutError) as exc:
        raise BackendCallbackError(f"Backend callback failed: {method} {path}: {exc}") from exc

    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def mark_report_complete(
    report_id: int | str,
    *,
    report_key: str,
    total_score: float,
    value_grade: str,
) -> dict[str, Any]:
    return _internal_request(
        "PATCH",
        f"/internal/reports/{report_id}/report-complete",
        {
            "reportKey": report_key,
            "totalScore": total_score,
            "valueGrade": value_grade,
        },
    )


def mark_report_embedding_complete(report_id: int | str) -> dict[str, Any]:
    return _internal_request("PATCH", f"/internal/reports/{report_id}/embedding-complete")


def mark_report_failed(report_id: int | str, error_message: str) -> dict[str, Any]:
    return _internal_request(
        "PATCH",
        f"/internal/reports/{report_id}/fail",
        {"errorMessage": error_message},
    )


def mark_pre_evaluation_report_complete(pre_evaluation_id: int | str, *, report_key: str) -> dict[str, Any]:
    return _internal_request(
        "PATCH",
        f"/internal/pre-evaluations/{pre_evaluation_id}/report-complete",
        {"reportKey": report_key},
    )


def mark_pre_evaluation_embedding_complete(pre_evaluation_id: int | str) -> dict[str, Any]:
    return _internal_request("PATCH", f"/internal/pre-evaluations/{pre_evaluation_id}/embedding-complete")


def mark_pre_evaluation_failed(pre_evaluation_id: int | str, error_message: str) -> dict[str, Any]:
    return _internal_request(
        "PATCH",
        f"/internal/pre-evaluations/{pre_evaluation_id}/fail",
        {"errorMessage": error_message},
    )
