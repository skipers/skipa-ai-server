"""HTTP client for backend internal callbacks."""

from __future__ import annotations

from typing import Any

import requests

from workers.config import WorkerConfig


def is_backend_conflict(exc: BaseException) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 409


class BackendCallbackClient:
    def __init__(self, config: WorkerConfig) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Api-Key": self.config.internal_api_key,
        }

    def _patch(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.config.backend_base_url:
            raise RuntimeError("BACKEND_INTERNAL_BASE_URL is required for backend callbacks.")
        if not self.config.internal_api_key:
            raise RuntimeError("INTERNAL_API_KEY is required for backend callbacks.")

        url = f"{self.config.backend_base_url}{path}"
        request_kwargs: dict[str, Any] = {
            "headers": self._headers(),
            "timeout": self.config.callback_timeout,
        }
        if payload is not None:
            request_kwargs["json"] = payload
        response = requests.patch(url, **request_kwargs)
        response.raise_for_status()
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            return {"raw": response.text}
        if isinstance(data, dict):
            return data
        return {"success": True, "data": data}

    def complete_report(
        self,
        report_id: int | str,
        report_key: str,
        total_score: float,
        value_grade: str,
    ) -> dict[str, Any]:
        return self._patch(
            f"/internal/reports/{report_id}/report-complete",
            {
                "reportKey": report_key,
                "totalScore": total_score,
                "valueGrade": value_grade,
            },
        )

    def mark_report_embedding_complete(self, report_id: int | str) -> dict[str, Any]:
        return self._patch(f"/internal/reports/{report_id}/embedding-complete")

    def fail_report(self, report_id: int | str, error_message: str) -> dict[str, Any]:
        return self._patch(f"/internal/reports/{report_id}/fail", {"errorMessage": error_message})

    def complete_patent_extract(
        self,
        extract_job_id: int | str,
        parsed_json_key: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return self._patch(
            f"/internal/patent-extract-jobs/{extract_job_id}/complete",
            {
                "parsedJsonKey": parsed_json_key,
                "result": result,
            },
        )

    def fail_patent_extract(self, extract_job_id: int | str, error_message: str) -> dict[str, Any]:
        return self._patch(
            f"/internal/patent-extract-jobs/{extract_job_id}/fail",
            {"errorMessage": error_message},
        )

    def complete_pre_evaluation(self, pre_evaluation_id: int | str, report_key: str) -> dict[str, Any]:
        return self._patch(
            f"/internal/pre-evaluations/{pre_evaluation_id}/complete",
            {"reportKey": report_key},
        )

    def complete_pre_evaluation_report(self, pre_evaluation_id: int | str, report_key: str) -> dict[str, Any]:
        return self._patch(
            f"/internal/pre-evaluations/{pre_evaluation_id}/report-complete",
            {"reportKey": report_key},
        )

    def mark_pre_evaluation_embedding_complete(self, pre_evaluation_id: int | str) -> dict[str, Any]:
        return self._patch(f"/internal/pre-evaluations/{pre_evaluation_id}/embedding-complete")

    def fail_pre_evaluation(self, pre_evaluation_id: int | str, error_message: str) -> dict[str, Any]:
        return self._patch(
            f"/internal/pre-evaluations/{pre_evaluation_id}/fail",
            {"errorMessage": error_message},
        )
