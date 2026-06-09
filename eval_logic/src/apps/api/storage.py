"""MinIO/S3-compatible storage adapter for eval_logic report JSON."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class StorageObject:
    backend: str
    bucket: str
    object_key: str
    content_type: str | None = None
    etag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "bucket": self.bucket,
            "object_key": self.object_key,
            "content_type": self.content_type,
            "etag": self.etag,
        }


class ObjectStorage:
    def enabled(self) -> bool:
        return False

    def put_json(self, object_key: str, data: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def put_file(self, object_key: str, path: Path, content_type: str | None = None) -> dict[str, Any] | None:
        return None

    def put_fileobj(self, object_key: str, fileobj: BinaryIO, content_type: str | None = None) -> dict[str, Any] | None:
        return None

    def download_file(self, object_key: str, destination: Path) -> dict[str, Any] | None:
        return None

    def get_json(self, object_key: str) -> dict[str, Any] | None:
        return None

    def list_object_keys(self, prefix: str = "") -> list[str]:
        return []


class MinioObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
        access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket = (
            os.getenv("MINIO_REPORT_BUCKET")
            or os.getenv("MINIO_BUCKET")
            or os.getenv("S3_BUCKET")
            or "skipa"
        )
        self.region = os.getenv("MINIO_REGION") or os.getenv("AWS_REGION") or "us-east-1"
        self.prefix = os.getenv("EVAL_LOGIC_OBJECT_PREFIX", "eval-logic").strip("/")
        explicit = os.getenv("EVAL_LOGIC_STORAGE_BACKEND", "").lower() in {"minio", "s3"}
        self._enabled = bool(endpoint and access_key and secret_key) or explicit
        self._client: Any | None = None
        self._error: str | None = None
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key

    def enabled(self) -> bool:
        return self._enabled

    def _boto3_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config
        except Exception as exc:
            self._error = f"boto3 is not installed: {exc}"
            raise RuntimeError(self._error) from exc

        secure = _truthy(os.getenv("MINIO_SECURE")) or self.endpoint.startswith("https://")
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint or None,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            use_ssl=secure,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        return self._client

    def _key(self, object_key: str) -> str:
        key = str(object_key or "").strip("/")
        return f"{self.prefix}/{key}" if self.prefix else key

    def put_json(self, object_key: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        key = self._key(object_key)
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        response = self._boto3_client().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json; charset=utf-8",
        )
        return StorageObject("minio", self.bucket, key, "application/json", response.get("ETag")).to_dict()

    def put_file(self, object_key: str, path: Path, content_type: str | None = None) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        key = self._key(object_key)
        extra_args = {"ContentType": content_type} if content_type else None
        client = self._boto3_client()
        if extra_args:
            client.upload_file(str(path), self.bucket, key, ExtraArgs=extra_args)
        else:
            client.upload_file(str(path), self.bucket, key)
        return StorageObject("minio", self.bucket, key, content_type).to_dict()

    def put_fileobj(self, object_key: str, fileobj: BinaryIO, content_type: str | None = None) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        key = self._key(object_key)
        extra_args = {"ContentType": content_type} if content_type else None
        fileobj.seek(0)
        client = self._boto3_client()
        if extra_args:
            client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra_args)
        else:
            client.upload_fileobj(fileobj, self.bucket, key)
        return StorageObject("minio", self.bucket, key, content_type).to_dict()

    def download_file(self, object_key: str, destination: Path) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        key = str(object_key or "").strip("/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._boto3_client().download_file(self.bucket, key, str(destination))
        return StorageObject("minio", self.bucket, key).to_dict()

    def get_json(self, object_key: str) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        key = str(object_key or "").strip("/")
        response = self._boto3_client().get_object(Bucket=self.bucket, Key=key)
        payload = json.loads(response["Body"].read().decode("utf-8-sig"))
        return payload if isinstance(payload, dict) else None

    def list_object_keys(self, prefix: str = "") -> list[str]:
        if not self.enabled():
            return []
        keys: list[str] = []
        continuation: str | None = None
        client = self._boto3_client()
        while True:
            params: dict[str, Any] = {"Bucket": self.bucket, "Prefix": str(prefix or "").lstrip("/")}
            if continuation:
                params["ContinuationToken"] = continuation
            response = client.list_objects_v2(**params)
            for item in response.get("Contents") or []:
                key = item.get("Key")
                if key:
                    keys.append(str(key))
            if not response.get("IsTruncated"):
                break
            continuation = response.get("NextContinuationToken")
        return keys


object_storage: ObjectStorage = MinioObjectStorage()
