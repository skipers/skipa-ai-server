"""Async report generation service for pre-application valuations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .schemas import PreApplicationValuationRequest
from .service import evaluate_pre_application
from .storage import save_result


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def default_output_key_template() -> str:
    return os.getenv(
        "PRE_EVALUATION_REPORT_OBJECT_KEY_TEMPLATE",
        "pre-evaluations/{pre_evaluation_id}/report.json",
    )


@dataclass(frozen=True)
class PreApplicationGenerationOptions:
    """Runtime knobs for pre-application report generation."""

    output_key_template: str | None = None
    local_output: bool = _bool_env("PRE_EVALUATION_WORKER_LOCAL_OUTPUT", False)


class PreApplicationGenerationService:
    """Generate, store, and describe a pre-application valuation report."""

    def __init__(self, options: PreApplicationGenerationOptions | None = None) -> None:
        self.options = options or PreApplicationGenerationOptions()

    def generate_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        pre_evaluation_id = _require(payload, "preEvaluationId")
        request = request_from_payload(payload)
        return self.generate(request, pre_evaluation_id=pre_evaluation_id, user_id=payload.get("userId"))

    def generate(
        self,
        request: PreApplicationValuationRequest,
        *,
        pre_evaluation_id: int | str,
        user_id: int | str | None = None,
    ) -> dict[str, Any]:
        report = evaluate_pre_application(request)
        report.setdefault("metadata", {})
        report["metadata"]["pre_evaluation_id"] = pre_evaluation_id
        if user_id is not None:
            report["metadata"]["user_id"] = user_id
        report["metadata"]["storage_policy"] = (
            "local_json_development" if self.options.local_output else "minio_object_key"
        )

        storage = self.save_report(report, pre_evaluation_id=pre_evaluation_id)
        report.setdefault("artifacts", {})
        report["artifacts"].update(storage)
        return {
            "status": "success",
            "pre_evaluation_id": pre_evaluation_id,
            "user_id": user_id,
            "report_key": storage.get("object_key") or storage.get("path"),
            "storage": storage,
            "report": report,
        }

    def save_report(self, report: dict[str, Any], *, pre_evaluation_id: int | str) -> dict[str, Any]:
        if not self.options.local_output:
            object_storage = _object_storage()
            if object_storage.enabled():
                object_key = output_key_for_pre_evaluation(
                    pre_evaluation_id,
                    self.options.output_key_template,
                )
                stored = object_storage.put_json(object_key, report)
                if not stored:
                    raise RuntimeError("MinIO 사전 평가 보고서 저장에 실패했습니다.")
                return stored
            raise RuntimeError("MinIO object storage is required unless PRE_EVALUATION_WORKER_LOCAL_OUTPUT=1.")

        output_path = save_result(report)
        return {"backend": "local", "path": str(output_path)}


def request_from_payload(payload: dict[str, Any]) -> PreApplicationValuationRequest:
    return PreApplicationValuationRequest.model_validate({
        "patent_name": payload.get("patentName") or payload.get("title"),
        "technology_description": payload.get("technologyDescription") or payload.get("technicalDescription"),
        "claims": payload.get("claims") or [],
        "related_business": payload.get("relatedBusiness") or "",
        "target_countries": payload.get("targetCountries") or [],
    })


def output_key_for_pre_evaluation(pre_evaluation_id: int | str, template: str | None = None) -> str:
    return (template or default_output_key_template()).format(
        pre_evaluation_id=pre_evaluation_id,
        preEvaluationId=pre_evaluation_id,
    ).strip("/")


def _require(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None or value == "":
        raise ValueError(f"PRE_EVALUATION_GENERATE payload missing required field: {field}")
    return value


def _object_storage() -> Any:
    try:
        from apps.api.storage import object_storage
    except Exception as exc:
        raise RuntimeError("eval_logic object storage adapter is required for MinIO output.") from exc
    return object_storage
