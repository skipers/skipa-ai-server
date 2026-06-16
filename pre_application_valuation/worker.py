"""RabbitMQ worker for pre-application valuation report generation."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

server_root = Path(__file__).resolve().parents[1]
eval_src = server_root / "eval_logic" / "src"
for path in (server_root, eval_src):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from pre_application_valuation.generation_service import (
    PreApplicationGenerationOptions,
    PreApplicationGenerationService,
)
from workers.backend_client import BackendCallbackClient, is_backend_conflict
from workers.config import WorkerConfig, load_worker_config
from workers.rabbitmq import RabbitWorker
from workers.vectorstore_hooks import index_pre_evaluation_report_from_minio

LOGGER = logging.getLogger(__name__)


def _require(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None or value == "":
        raise ValueError(f"PRE_EVALUATION_GENERATE payload missing required field: {field}")
    return value


class PreEvaluationGenerateHandler:
    def __init__(self, config: WorkerConfig | None = None) -> None:
        self.config = config or load_worker_config()
        self.backend = BackendCallbackClient(self.config)
        self.service = PreApplicationGenerationService(
            PreApplicationGenerationOptions(
                output_key_template=self.config.pre_evaluation_output_key_template,
                local_output=self.config.pre_evaluation_local_output,
            )
        )

    def __call__(self, payload: dict[str, Any]) -> None:
        message_type = payload.get("type")
        if message_type != "PRE_EVALUATION_GENERATE":
            raise ValueError(f"Unsupported pre-evaluation message type: {message_type}")

        pre_evaluation_id = _require(payload, "preEvaluationId")

        try:
            result = self.service.generate_from_payload(payload)
            report_key = result.get("report_key")
            if not report_key:
                raise RuntimeError("Pre-evaluation generation did not return a report_key.")
        except Exception as exc:
            LOGGER.exception("Pre-evaluation generation failed preEvaluationId=%s", pre_evaluation_id)
            raise RuntimeError("Pre-evaluation generation failed") from exc

        try:
            self.backend.complete_pre_evaluation_report(pre_evaluation_id, str(report_key))
        except Exception as exc:
            if is_backend_conflict(exc):
                LOGGER.warning("Pre-evaluation report-complete callback conflicted preEvaluationId=%s", pre_evaluation_id)
            else:
                LOGGER.exception("Pre-evaluation report-complete callback failed preEvaluationId=%s", pre_evaluation_id)
                raise

        try:
            index_pre_evaluation_report_from_minio(
                str(report_key),
                pre_evaluation_id=pre_evaluation_id,
                enabled=self.config.enable_pre_evaluation_vectorstore_index,
                strict=self.config.pre_evaluation_vectorstore_strict,
            )
        except Exception as exc:
            LOGGER.exception("Pre-evaluation vectorstore indexing failed preEvaluationId=%s", pre_evaluation_id)
            raise

        try:
            self.backend.mark_pre_evaluation_embedding_complete(pre_evaluation_id)
        except Exception as exc:
            if is_backend_conflict(exc):
                LOGGER.warning(
                    "Pre-evaluation embedding-complete callback conflicted preEvaluationId=%s",
                    pre_evaluation_id,
                )
            else:
                LOGGER.exception("Pre-evaluation embedding-complete callback failed preEvaluationId=%s", pre_evaluation_id)
                raise
        LOGGER.info(
            "Completed pre-evaluation generation and embedding preEvaluationId=%s key=%s",
            pre_evaluation_id,
            report_key,
        )


class PreEvaluationRetryExhaustedHandler:
    def __init__(self, config: WorkerConfig | None = None) -> None:
        self.config = config or load_worker_config()
        self.backend = BackendCallbackClient(self.config)

    def __call__(self, payload: dict[str, Any], exc: BaseException, attempts: int) -> None:
        try:
            pre_evaluation_id = _require(payload, "preEvaluationId")
        except ValueError:
            LOGGER.exception("Pre-evaluation retry exhausted but payload has no preEvaluationId")
            return

        LOGGER.error(
            "Marking pre-evaluation failed after %s attempts preEvaluationId=%s error=%s",
            attempts,
            pre_evaluation_id,
            _error_message(exc),
        )
        try:
            self.backend.fail_pre_evaluation(pre_evaluation_id, _error_message(exc))
        except Exception as callback_exc:
            if is_backend_conflict(callback_exc):
                LOGGER.warning("Pre-evaluation fail callback conflicted preEvaluationId=%s", pre_evaluation_id)
                return
            LOGGER.exception("Pre-evaluation fail callback failed preEvaluationId=%s", pre_evaluation_id)
            raise


def pre_evaluation_rabbit_worker(config: WorkerConfig) -> RabbitWorker:
    max_attempts = config.pre_evaluation_max_attempts if config.pre_evaluation_max_attempts > 0 else None
    return RabbitWorker(
        config,
        config.pre_evaluation_queue,
        PreEvaluationGenerateHandler(config),
        max_attempts=max_attempts,
        on_retry_exhausted=PreEvaluationRetryExhaustedHandler(config),
    )


def _error_message(exc: BaseException) -> str:
    cause = exc.__cause__
    if cause is None:
        return str(exc)
    return f"{exc}: {cause}"


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_worker_config()
    pre_evaluation_rabbit_worker(config).run_forever()


if __name__ == "__main__":
    run()
