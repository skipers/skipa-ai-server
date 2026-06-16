"""MinIO sync helpers for shared patent data.

The chatbot reads patent data from ``SHARED_PATENT_ROOT``. In Kubernetes that
directory is hydrated from MinIO ``s3://<bucket>/<prefix>/`` so the UI and API
can show the same data that lives in object storage.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_CONSOLE_URL,
    MINIO_ENDPOINT,
    MINIO_PATENT_PREFIX,
    MINIO_REINDEX_AFTER_SYNC,
    MINIO_SECRET_KEY,
    MINIO_WIKI_PREFIX,
    MINIO_WIKI_UPLOAD_ON_WRITE,
    SHARED_PATENT_ROOT,
    WIKI_ROOT,
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _prefix() -> str:
    prefix = MINIO_PATENT_PREFIX.strip("/")
    return f"{prefix}/" if prefix else ""


def _wiki_prefix() -> str:
    prefix = MINIO_WIKI_PREFIX.strip("/")
    return f"{prefix}/" if prefix else ""


def _configured() -> bool:
    return bool(MINIO_ENDPOINT and MINIO_ACCESS_KEY and MINIO_SECRET_KEY and MINIO_BUCKET)


def _masked(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def _local_file_count() -> int:
    if not SHARED_PATENT_ROOT.exists():
        return 0
    return sum(1 for path in SHARED_PATENT_ROOT.rglob("*") if path.is_file())


def _local_wiki_files() -> list[Path]:
    if not WIKI_ROOT.exists():
        return []
    return [path for path in sorted(WIKI_ROOT.rglob("*")) if _is_wiki_data_file(path)]


def _local_wiki_file_count() -> int:
    return len(_local_wiki_files())


def _local_patent_count() -> int:
    if not SHARED_PATENT_ROOT.exists():
        return 0
    return sum(
        1
        for path in SHARED_PATENT_ROOT.iterdir()
        if path.is_dir() and ((path / "parsed.json").exists() or (path / "report.json").exists() or any((path / "reports").glob("*/report.json")))
    )


def _local_total_size() -> int:
    if not SHARED_PATENT_ROOT.exists():
        return 0
    total = 0
    for path in SHARED_PATENT_ROOT.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                pass
    return total


def _local_wiki_total_size() -> int:
    total = 0
    for path in _local_wiki_files():
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def _base_status() -> dict[str, Any]:
    console_url = MINIO_CONSOLE_URL
    if not console_url and MINIO_ENDPOINT:
        console_url = MINIO_ENDPOINT.replace(":9000", ":9001")
    return {
        "configured": _configured(),
        "endpoint": MINIO_ENDPOINT,
        "console_url": console_url,
        "bucket": MINIO_BUCKET,
        "prefix": _prefix(),
        "access_key": _masked(MINIO_ACCESS_KEY),
        "local_root": str(SHARED_PATENT_ROOT),
        "local_exists": SHARED_PATENT_ROOT.exists(),
        "local_patent_count": _local_patent_count(),
        "local_file_count": _local_file_count(),
        "local_size_bytes": _local_total_size(),
        "updated_at": _now(),
    }


def _base_wiki_status() -> dict[str, Any]:
    console_url = MINIO_CONSOLE_URL
    if not console_url and MINIO_ENDPOINT:
        console_url = MINIO_ENDPOINT.replace(":9000", ":9001")
    return {
        "configured": _configured(),
        "endpoint": MINIO_ENDPOINT,
        "console_url": console_url,
        "bucket": MINIO_BUCKET,
        "prefix": _wiki_prefix(),
        "access_key": _masked(MINIO_ACCESS_KEY),
        "local_root": str(WIKI_ROOT),
        "local_exists": WIKI_ROOT.exists(),
        "local_wiki_file_count": _local_wiki_file_count(),
        "local_size_bytes": _local_wiki_total_size(),
        "updated_at": _now(),
    }


def _boto3_client():
    try:
        import boto3
        from botocore.config import Config
    except Exception:
        return None
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
        config=Config(
            connect_timeout=4,
            read_timeout=20,
            retries={"max_attempts": 1},
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def _remote_status_boto3() -> dict[str, Any]:
    client = _boto3_client()
    if client is None:
        raise RuntimeError("boto3 is not installed")
    paginator = client.get_paginator("list_objects_v2")
    object_count = 0
    total_size = 0
    sample_keys: list[str] = []
    for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=_prefix()):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key or key.endswith("/"):
                continue
            object_count += 1
            total_size += int(item.get("Size") or 0)
            if len(sample_keys) < 20:
                sample_keys.append(key)
    return {
        "remote_object_count": object_count,
        "remote_size_bytes": total_size,
        "sample_keys": sample_keys,
        "backend": "boto3",
    }


def _aws_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "AWS_ACCESS_KEY_ID": MINIO_ACCESS_KEY,
            "AWS_SECRET_ACCESS_KEY": MINIO_SECRET_KEY,
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    )
    return env


def _run_aws(args: list[str]) -> subprocess.CompletedProcess[str]:
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError("Neither boto3 nor aws CLI is available")
    return subprocess.run(
        [aws, "--endpoint-url", MINIO_ENDPOINT, *args],
        check=False,
        text=True,
        capture_output=True,
        env=_aws_env(),
        timeout=120,
    )


def _is_wiki_data_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        rel = path.resolve().relative_to(WIKI_ROOT.resolve())
    except Exception:
        return False
    if any(part in {"qdrant", "__pycache__"} for part in rel.parts):
        return False
    if path.name.startswith(".") or path.name == ".DS_Store":
        return False
    return path.suffix.lower() in {".md", ".json", ".jsonl", ".txt"}


def _wiki_object_key(path: Path) -> str:
    rel = path.resolve().relative_to(WIKI_ROOT.resolve())
    return (_wiki_prefix() + rel.as_posix()).lstrip("/")


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown; charset=utf-8"
    if suffix == ".json":
        return "application/json; charset=utf-8"
    if suffix == ".jsonl":
        return "application/x-ndjson; charset=utf-8"
    return "text/plain; charset=utf-8"


def upload_wiki_file_to_minio(path: str | Path, *, force: bool = False) -> dict[str, Any]:
    """Upload one wiki data file to MinIO using the configured wiki prefix."""
    path = Path(path)
    if not force and not MINIO_WIKI_UPLOAD_ON_WRITE:
        return {"status": "skipped", "reason": "MINIO_WIKI_UPLOAD_ON_WRITE=false", "path": str(path)}
    if not _configured():
        return {"status": "skipped", "reason": "MinIO not configured", "path": str(path)}
    if not _is_wiki_data_file(path):
        return {"status": "skipped", "reason": "not a wiki data file", "path": str(path)}

    key = _wiki_object_key(path)
    client = _boto3_client()
    if client is not None:
        try:
            client.upload_file(
                str(path),
                MINIO_BUCKET,
                key,
                ExtraArgs={"ContentType": _content_type(path)},
            )
            return {
                "status": "uploaded",
                "backend": "boto3",
                "bucket": MINIO_BUCKET,
                "object_key": key,
                "path": str(path),
                "size": path.stat().st_size,
            }
        except Exception as exc:
            return {"status": "error", "backend": "boto3", "object_key": key, "path": str(path), "error": str(exc)}

    try:
        result = _run_aws(["s3", "cp", str(path), f"s3://{MINIO_BUCKET}/{key}", "--content-type", _content_type(path)])
    except Exception as exc:
        return {"status": "error", "backend": "aws_cli", "object_key": key, "path": str(path), "error": str(exc)}
    if result.returncode != 0:
        return {"status": "error", "backend": "aws_cli", "object_key": key, "path": str(path), "error": (result.stderr or result.stdout).strip()}
    return {"status": "uploaded", "backend": "aws_cli", "bucket": MINIO_BUCKET, "object_key": key, "path": str(path), "size": path.stat().st_size}


def sync_wiki_data_to_minio() -> dict[str, Any]:
    """Upload existing local wiki data to MinIO under ``MINIO_WIKI_PREFIX``."""
    status = _base_wiki_status()
    if not status["configured"]:
        return {**status, "connected": False, "status": "not_configured", "error": "MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET is not configured"}

    uploaded = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for path in _local_wiki_files():
        result = upload_wiki_file_to_minio(path, force=True)
        if result.get("status") == "uploaded":
            uploaded += 1
        elif result.get("status") == "skipped":
            skipped += 1
        else:
            errors.append(result)
    return {
        **status,
        "connected": not errors,
        "status": "uploaded" if not errors else "completed_with_errors",
        "uploaded_count": uploaded,
        "skipped_count": skipped,
        "error_count": len(errors),
        "errors": errors[:20],
    }


def _remote_wiki_status_boto3() -> dict[str, Any]:
    client = _boto3_client()
    if client is None:
        raise RuntimeError("boto3 is not installed")
    paginator = client.get_paginator("list_objects_v2")
    object_count = 0
    total_size = 0
    sample_keys: list[str] = []
    for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=_wiki_prefix()):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key or key.endswith("/"):
                continue
            object_count += 1
            total_size += int(item.get("Size") or 0)
            if len(sample_keys) < 20:
                sample_keys.append(key)
    return {
        "remote_object_count": object_count,
        "remote_size_bytes": total_size,
        "sample_keys": sample_keys,
        "backend": "boto3",
    }


def wiki_minio_status() -> dict[str, Any]:
    status = _base_wiki_status()
    if not status["configured"]:
        status.update({"connected": False, "status": "not_configured", "error": "MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET is not configured"})
        return status
    try:
        status.update(_remote_wiki_status_boto3())
        status.update({"connected": True, "status": "ok"})
    except Exception as exc:
        status.update({"connected": False, "status": "error", "error": str(exc)})
    return status


def sync_wiki_data_from_minio() -> dict[str, Any]:
    """Download MinIO ``wiki/`` data into local ``WIKI_ROOT`` without deleting local files."""
    status = _base_wiki_status()
    if not status["configured"]:
        return {**status, "connected": False, "sync_status": "skipped", "error": "MinIO not configured"}
    client = _boto3_client()
    if client is None:
        return {**status, "connected": False, "sync_status": "failed", "error": "boto3 not installed"}

    downloaded = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=_wiki_prefix()):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key or key.endswith("/"):
                continue
            rel = key[len(_wiki_prefix()):] if key.startswith(_wiki_prefix()) else key
            target = WIKI_ROOT / rel
            if any(part in {"qdrant", "__pycache__"} for part in target.parts):
                skipped += 1
                continue
            remote_size = int(item.get("Size") or 0)
            try:
                if target.exists() and target.stat().st_size == remote_size:
                    skipped += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                client.download_file(MINIO_BUCKET, key, str(target))
                downloaded += 1
            except Exception as exc:
                errors.append({"object_key": key, "target": str(target), "error": str(exc)})
    return {
        **status,
        "connected": not errors,
        "sync_status": "synced" if not errors else "completed_with_errors",
        "downloaded_count": downloaded,
        "skipped_count": skipped,
        "error_count": len(errors),
        "errors": errors[:20],
    }


def _remote_status_aws() -> dict[str, Any]:
    result = _run_aws(
        [
            "s3api",
            "list-objects-v2",
            "--bucket",
            MINIO_BUCKET,
            "--prefix",
            _prefix(),
            "--query",
            "[length(Contents[]), sum(Contents[].Size)]",
            "--output",
            "text",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "aws list failed").strip())
    parts = (result.stdout or "").strip().split()
    object_count = int(parts[0]) if parts and parts[0] != "None" else 0
    total_size = int(float(parts[1])) if len(parts) > 1 and parts[1] != "None" else 0
    sample = _run_aws(["s3", "ls", f"s3://{MINIO_BUCKET}/{_prefix()}", "--recursive"])
    sample_keys = []
    if sample.returncode == 0:
        for line in (sample.stdout or "").splitlines()[:20]:
            sample_keys.append(line.split(maxsplit=3)[-1] if line.split(maxsplit=3) else line)
    return {
        "remote_object_count": object_count,
        "remote_size_bytes": total_size,
        "sample_keys": sample_keys,
        "backend": "aws_cli",
    }


def minio_patent_status() -> dict[str, Any]:
    status = _base_status()
    if not status["configured"]:
        status.update({"connected": False, "status": "not_configured", "error": "MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET is not configured"})
        return status
    try:
        try:
            remote = _remote_status_boto3()
        except Exception as boto_exc:
            remote = _remote_status_aws()
            remote["boto3_error"] = str(boto_exc)
        status.update(remote)
        status.update({"connected": True, "status": "ok"})
    except Exception as exc:
        status.update(
            {
                "connected": False,
                "status": "error",
                "error": str(exc),
                "hint": "If you run the server on your laptop, port-forward MinIO and set MINIO_ENDPOINT=http://127.0.0.1:19000. Inside Kubernetes, use http://skipa-minio:9000.",
            }
        )
    return status


def _sync_boto3() -> dict[str, Any]:
    client = _boto3_client()
    if client is None:
        raise RuntimeError("boto3 is not installed")
    SHARED_PATENT_ROOT.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    total = 0
    paginator = client.get_paginator("list_objects_v2")
    prefix = _prefix()
    for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=prefix):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            if not key or key.endswith("/"):
                continue
            total += 1
            rel_key = key[len(prefix) :] if prefix and key.startswith(prefix) else key
            target = SHARED_PATENT_ROOT / rel_key
            target.parent.mkdir(parents=True, exist_ok=True)
            remote_size = int(item.get("Size") or 0)
            if target.exists() and target.stat().st_size == remote_size:
                skipped += 1
                continue
            client.download_file(MINIO_BUCKET, key, str(target))
            downloaded += 1
    return {"backend": "boto3", "remote_object_count": total, "downloaded_count": downloaded, "skipped_count": skipped}


def _sync_aws() -> dict[str, Any]:
    SHARED_PATENT_ROOT.mkdir(parents=True, exist_ok=True)
    result = _run_aws(["s3", "sync", f"s3://{MINIO_BUCKET}/{_prefix()}", str(SHARED_PATENT_ROOT), "--no-progress"])
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "aws sync failed").strip())
    uploaded_lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
    return {"backend": "aws_cli", "sync_output_count": len(uploaded_lines), "sync_output_preview": uploaded_lines[:20]}


def fetch_pre_application_report_from_minio(patent_id: str) -> dict[str, Any]:
    """MinIO에서 사전 출원 특허 보고서(report.json)를 가져옵니다.

    탐색 경로 우선순위:
    1. pre-evaluations/{case_id}/report.json
    2. {MINIO_PATENT_PREFIX}/{case_id}/report.json
    3. {MINIO_PATENT_PREFIX}/{case_id}/reports/{case_id}/report.json
    4. pre_application/{case_id}/report.json
    5. {case_id}/report.json

    반환: { "found": bool, "patent_id": str, "case_id": str, "report": dict | None,
             "source_key": str | None, "error": str | None }
    """
    if not _configured():
        return {"found": False, "patent_id": patent_id, "case_id": patent_id, "report": None, "error": "MinIO not configured"}

    client = _boto3_client()
    if client is None:
        return {"found": False, "patent_id": patent_id, "case_id": patent_id, "report": None, "error": "boto3 not installed"}

    prefix = _prefix().strip("/")
    candidates = [
        f"pre-evaluations/{patent_id}/report.json",
        f"{prefix}/{patent_id}/report.json" if prefix else f"{patent_id}/report.json",
        f"{prefix}/{patent_id}/reports/{patent_id}/report.json" if prefix else f"{patent_id}/reports/{patent_id}/report.json",
        f"pre_application/{patent_id}/report.json",
        f"{patent_id}/report.json",
    ]

    import io
    import json as _json

    for key in candidates:
        key = key.lstrip("/")
        try:
            obj = client.get_object(Bucket=MINIO_BUCKET, Key=key)
            body = obj["Body"].read()
            report = _json.loads(body.decode("utf-8"))
            return {
                "found": True,
                "patent_id": patent_id,
                "case_id": patent_id,
                "report": report,
                "source_key": key,
                "error": None,
            }
        except Exception:
            continue

    return {
        "found": False,
        "patent_id": patent_id,
        "case_id": patent_id,
        "report": None,
        "source_key": None,
        "error": f"report.json not found in MinIO for case_id={patent_id} (tried: {candidates})",
    }


def sync_patent_data_from_minio(*, rebuild_index: bool | None = None) -> dict[str, Any]:
    status_before = minio_patent_status()
    if not status_before.get("configured"):
        return {**status_before, "sync_status": "skipped"}
    if not status_before.get("connected"):
        return {**status_before, "sync_status": "failed"}

    try:
        try:
            sync_result = _sync_boto3()
        except Exception as boto_exc:
            sync_result = _sync_aws()
            sync_result["boto3_error"] = str(boto_exc)
        result: dict[str, Any] = {
            "status": "synced",
            "sync_status": "synced",
            "minio": minio_patent_status(),
            "sync": sync_result,
        }
        should_rebuild = MINIO_REINDEX_AFTER_SYNC if rebuild_index is None else rebuild_index
        if should_rebuild:
            from .shared_data import build_all_patent_vectorstores
            from .visual_data import build_missing_patent_visual_indexes

            result["patent_indexes"] = build_all_patent_vectorstores()
            result["shared_index"] = {"status": "skipped", "reason": "per_patent_only"}
            result["shared_visual_index"] = build_missing_patent_visual_indexes(force=False)
        return result
    except Exception as exc:
        return {
            **_base_status(),
            "connected": False,
            "status": "error",
            "sync_status": "failed",
            "error": str(exc),
        }
