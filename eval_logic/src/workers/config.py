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

    report_queue: str = os.getenv("REPORT_GENERATE_QUEUE", "skipa.report.generate")
    patent_extract_queue: str = os.getenv("PATENT_EXTRACT_QUEUE", "skipa.patent-extract")

    backend_base_url: str = os.getenv("BACKEND_INTERNAL_BASE_URL", "").rstrip("/")
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")
    callback_timeout: float = _float_env("BACKEND_CALLBACK_TIMEOUT", 20.0)

    report_profile: str = os.getenv("EVAL_LOGIC_WORKER_PROFILE", "full")
    local_output: bool = _bool_env("EVAL_LOGIC_WORKER_LOCAL_OUTPUT", False)


def load_worker_config() -> WorkerConfig:
    return WorkerConfig()

