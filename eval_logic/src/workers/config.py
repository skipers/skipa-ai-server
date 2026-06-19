"""Worker runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.env import load_runtime_env

load_runtime_env()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WorkerConfig:
    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_port: int = _int_env("RABBITMQ_PORT", 5672)
    rabbitmq_username: str = os.getenv("RABBITMQ_USERNAME", "guest")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    rabbitmq_virtual_host: str = os.getenv("RABBITMQ_VIRTUAL_HOST", "/")
    rabbitmq_heartbeat: int = _int_env("RABBITMQ_HEARTBEAT", 600)
    rabbitmq_blocked_connection_timeout: float = _float_env("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", 300.0)
    prefetch_count: int = _int_env("WORKER_PREFETCH_COUNT", 1)
    requeue_on_callback_failure: bool = _bool_env("WORKER_REQUEUE_ON_CALLBACK_FAILURE", True)
    worker_max_attempts: int = _int_env("WORKER_MAX_ATTEMPTS", 3)
    report_max_attempts: int = _int_env("REPORT_WORKER_MAX_ATTEMPTS", _int_env("WORKER_MAX_ATTEMPTS", 3))
    patent_extract_max_attempts: int = _int_env("PATENT_EXTRACT_WORKER_MAX_ATTEMPTS", _int_env("WORKER_MAX_ATTEMPTS", 3))
    pre_evaluation_max_attempts: int = _int_env("PRE_EVALUATION_MAX_ATTEMPTS", _int_env("WORKER_MAX_ATTEMPTS", 3))

    report_queue: str = os.getenv("REPORT_GENERATE_QUEUE", "skipa.report.generate")
    patent_extract_queue: str = os.getenv("PATENT_EXTRACT_QUEUE", "skipa.patent-extract")
    pre_evaluation_queue: str = os.getenv("PRE_EVALUATION_GENERATE_QUEUE", "skipa.pre-evaluation.generate")
    report_dlq: str = os.getenv(
        "REPORT_GENERATE_DLQ",
        f"{os.getenv('REPORT_GENERATE_QUEUE', 'skipa.report.generate')}.dlq",
    )
    patent_extract_dlq: str = os.getenv(
        "PATENT_EXTRACT_DLQ",
        f"{os.getenv('PATENT_EXTRACT_QUEUE', 'skipa.patent-extract')}.dlq",
    )
    pre_evaluation_dlq: str = os.getenv(
        "PRE_EVALUATION_GENERATE_DLQ",
        f"{os.getenv('PRE_EVALUATION_GENERATE_QUEUE', 'skipa.pre-evaluation.generate')}.dlq",
    )

    backend_base_url: str = os.getenv("BACKEND_INTERNAL_BASE_URL", "").rstrip("/")
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")
    callback_timeout: float = _float_env("BACKEND_CALLBACK_TIMEOUT", 20.0)

    report_profile: str = os.getenv("EVAL_LOGIC_WORKER_PROFILE", "full")
    local_output: bool = _bool_env("EVAL_LOGIC_WORKER_LOCAL_OUTPUT", False)
    pre_evaluation_local_output: bool = _bool_env("PRE_EVALUATION_WORKER_LOCAL_OUTPUT", False)
    pre_evaluation_output_key_template: str = os.getenv(
        "PRE_EVALUATION_REPORT_OBJECT_KEY_TEMPLATE",
        "pre-evaluations/{pre_evaluation_id}/report.json",
    )
    enable_report_vectorstore_index: bool = _bool_env("ENABLE_REPORT_VECTORSTORE_INDEX", True)
    report_vectorstore_strict: bool = _bool_env("REPORT_VECTORSTORE_STRICT", False)
    enable_pre_evaluation_vectorstore_index: bool = _bool_env("ENABLE_PRE_EVALUATION_VECTORSTORE_INDEX", True)
    pre_evaluation_vectorstore_strict: bool = _bool_env("PRE_EVALUATION_VECTORSTORE_STRICT", False)


def load_worker_config() -> WorkerConfig:
    return WorkerConfig()
