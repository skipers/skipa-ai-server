"""Report generation worker implementation."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.report_generation_service import (
    ReportGenerationOptions,
    ReportGenerationService,
    source_from_patent_id,
)
from apps.api.storage import object_storage
from workers.backend_client import BackendCallbackClient, is_backend_conflict
from workers.config import WorkerConfig, load_worker_config
from workers.rabbitmq import RabbitWorker
from workers.vectorstore_hooks import index_patent_report_from_minio

LOGGER = logging.getLogger(__name__)


def _normalize_value_grade(value: Any, total_score: float | None = None) -> str:
    grade = str(value or "").strip().upper()
    if grade.startswith("S"):
        return "S"
    if grade.startswith("A"):
        return "A"
    if grade.startswith("B"):
        return "B"
    if grade.startswith("C"):
        return "C"
    if grade.startswith("D"):
        return "D"

    score = float(total_score or 0.0)
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _score_from_report(report: dict[str, Any]) -> float:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    score_100 = summary.get("overall_score_out_of_100")
    if isinstance(score_100, (int, float)):
        return round(max(0.0, min(100.0, float(score_100))), 2)

    score_5 = summary.get("overall_score")
    if isinstance(score_5, (int, float)):
        return round(max(0.0, min(100.0, float(score_5) / 5 * 100)), 2)

    evaluation = report.get("evaluation") if isinstance(report.get("evaluation"), dict) else {}
    dimensions = evaluation.get("dimensions") if isinstance(evaluation.get("dimensions"), dict) else {}
    dimension_scores = [
        float(data["score_out_of_100"])
        for data in dimensions.values()
        if isinstance(data, dict) and isinstance(data.get("score_out_of_100"), (int, float))
    ]
    if dimension_scores:
        return round(sum(dimension_scores) / len(dimension_scores), 2)
    return 0.0


def _metrics_from_workflow_result(workflow_result: dict[str, Any]) -> tuple[float, str]:
    report = workflow_result.get("report") if isinstance(workflow_result.get("report"), dict) else {}
    if not report and isinstance(workflow_result.get("summary"), dict):
        report = workflow_result

    total_score = _score_from_report(report)
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    value_grade = _normalize_value_grade(summary.get("overall_grade"), total_score)
    return total_score, value_grade


def _report_callback_metrics(generation_result: dict[str, Any]) -> tuple[float, str]:
    workflow_result = generation_result.get("result") if isinstance(generation_result.get("result"), dict) else {}
    return _metrics_from_workflow_result(workflow_result)


def _report_object_key_candidates(patent_id: int | str, report_id: int | str) -> list[str]:
    patent_prefix = (os.getenv("MINIO_PATENT_PREFIX", "patents").strip("/") or "patents")
    key = f"{patent_prefix}/{patent_id}/reports/{report_id}/report.json"
    prefix = str(getattr(object_storage, "prefix", "") or "").strip("/")
    candidates = [key]
    if prefix and not key.startswith(f"{prefix}/"):
        candidates.append(f"{prefix}/{key}")
    return candidates


def _read_existing_report(patent_id: int | str, report_id: int | str) -> tuple[str, dict[str, Any]] | None:
    if not object_storage.enabled():
        return None
    for object_key in _report_object_key_candidates(patent_id, report_id):
        try:
            payload = object_storage.get_json(object_key)
        except Exception:
            continue
        if isinstance(payload, dict):
            return object_key, payload
    return None


def _require(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None or value == "":
        raise ValueError(f"REPORT_GENERATE payload missing required field: {field}")
    return value


class ReportGenerateHandler:
    def __init__(self, config: WorkerConfig | None = None) -> None:
        self.config = config or load_worker_config()
        self.backend = BackendCallbackClient(self.config)

    def __call__(self, payload: dict[str, Any]) -> None:
        message_type = payload.get("type")
        if message_type != "REPORT_GENERATE":
            raise ValueError(f"Unsupported report message type: {message_type}")

        report_id = _require(payload, "reportId")
        patent_id = _require(payload, "patentId")
        parsed_object_key = payload.get("parsedObjectKey") or payload.get("objectKey")
        source = source_from_patent_id(patent_id, object_key=parsed_object_key)

        try:
            existing = _read_existing_report(patent_id, report_id)
            if existing:
                report_key, workflow_result = existing
                total_score, value_grade = _metrics_from_workflow_result(workflow_result)
                LOGGER.info(
                    "Reusing existing report reportId=%s patentId=%s key=%s totalScore=%s valueGrade=%s",
                    report_id,
                    patent_id,
                    report_key,
                    total_score,
                    value_grade,
                )
            else:
                service = ReportGenerationService(
                    ReportGenerationOptions(
                        profile=self.config.report_profile,
                        local_output=self.config.local_output,
                    )
                )
                result = service.generate_from_source(source, report_id=report_id, patent_id=patent_id)
                report_key = result.get("report_key")
                if not report_key:
                    raise RuntimeError("Report generation did not return a report_key.")
                total_score, value_grade = _report_callback_metrics(result)
        except Exception as exc:
            LOGGER.exception("Report generation failed reportId=%s patentId=%s", report_id, patent_id)
            try:
                self.backend.fail_report(report_id, str(exc))
            except Exception as callback_exc:
                if is_backend_conflict(callback_exc):
                    LOGGER.warning("Report fail callback conflicted reportId=%s", report_id)
                    return
                LOGGER.exception("Report fail callback failed reportId=%s", report_id)
                raise
            return

        try:
            self.backend.complete_report(report_id, str(report_key), total_score, value_grade)
        except Exception as exc:
            if is_backend_conflict(exc):
                LOGGER.warning("Report report-complete callback conflicted reportId=%s", report_id)
            else:
                LOGGER.exception("Report report-complete callback failed reportId=%s", report_id)
                raise

        try:
            index_patent_report_from_minio(
                str(report_key),
                patent_id=patent_id,
                enabled=self.config.enable_report_vectorstore_index,
                strict=self.config.report_vectorstore_strict,
            )
        except Exception as exc:
            LOGGER.exception("Report vectorstore indexing failed reportId=%s patentId=%s", report_id, patent_id)
            raise

        try:
            self.backend.mark_report_embedding_complete(report_id)
        except Exception as exc:
            if is_backend_conflict(exc):
                LOGGER.warning("Report embedding-complete callback conflicted reportId=%s", report_id)
            else:
                LOGGER.exception("Report embedding-complete callback failed reportId=%s", report_id)
                raise
        LOGGER.info(
            "Completed report generation and embedding reportId=%s patentId=%s key=%s totalScore=%s valueGrade=%s",
            report_id,
            patent_id,
            report_key,
            total_score,
            value_grade,
        )


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_worker_config()
    RabbitWorker(config, config.report_queue, ReportGenerateHandler(config)).run_forever()


if __name__ == "__main__":
    run()
