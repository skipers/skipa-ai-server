"""HTTP client for backend internal callbacks."""

from __future__ import annotations

from typing import Any

import requests

from workers.config import WorkerConfig


class BackendCallbackClient:
    def __init__(self, config: WorkerConfig) -> None:
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Api-Key": self.config.internal_api_key,
        }

    def _patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.backend_base_url:
            raise RuntimeError("BACKEND_INTERNAL_BASE_URL is required for backend callbacks.")
        if not self.config.internal_api_key:
            raise RuntimeError("INTERNAL_API_KEY is required for backend callbacks.")

        url = f"{self.config.backend_base_url}{path}"
        response = requests.patch(
            url,
            json=payload,
            headers=self._headers(),
            timeout=self.config.callback_timeout,
        )
        response.raise_for_status()
        data = response.json()
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
            f"/internal/reports/{report_id}/complete",
            {
                "reportKey": report_key,
                "totalScore": total_score,
                "valueGrade": value_grade,
            },
        )

    def fail_report(self, report_id: int | str, error_message: str) -> dict[str, Any]:
        return self._patch(f"/internal/reports/{report_id}/fail", {"errorMessage": error_message})

    def complete_patent_extract(self, extract_job_id: int | str, result: dict[str, Any]) -> dict[str, Any]:
        return self._patch(f"/internal/patent-extract-jobs/{extract_job_id}/complete", {"result": result})

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

    def fail_pre_evaluation(self, pre_evaluation_id: int | str, error_message: str) -> dict[str, Any]:
        return self._patch(
            f"/internal/pre-evaluations/{pre_evaluation_id}/fail",
            {"errorMessage": error_message},
        )
