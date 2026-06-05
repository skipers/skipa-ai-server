"""간단한 인메모리 보고서 Job 저장소입니다.

개발 단계에서 Swagger UI로 Job 기반 API를 테스트하기 위한 구현입니다. 실제
서비스에서는 Redis, DB, Celery/RQ 같은 영속 저장소와 작업 큐로 교체하는
것이 좋습니다.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any
from uuid import uuid4


_LOCK = Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def create_job(kind: str, request_payload: dict[str, Any]) -> str:
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "request": request_payload,
            "result": None,
            "errors": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    return job_id


def set_running(job_id: str) -> None:
    update_job(job_id, {"status": "running"})


def set_completed(job_id: str, result: dict[str, Any]) -> None:
    status = "completed" if not result.get("errors") else "partial_success"
    update_job(job_id, {"status": status, "result": result, "errors": result.get("errors") or []})


def set_failed(job_id: str, error: str) -> None:
    update_job(job_id, {"status": "failed", "errors": [error]})


def update_job(job_id: str, values: dict[str, Any]) -> None:
    with _LOCK:
        if job_id not in _JOBS:
            raise KeyError(job_id)
        _JOBS[job_id].update(values)
        _JOBS[job_id]["updated_at"] = datetime.now().isoformat()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None
