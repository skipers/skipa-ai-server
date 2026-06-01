"""중앙 특허 데이터 저장소 헬퍼입니다.

보고서 생성 로직과 챗봇이 같은 ``data/mapped_patent_reports/<patent_id>``
트리를 바라보도록 특허별 입력, 원문 PDF, 보고서 JSON, 위키 폴더를 관리합니다.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import PATENT_DATA_DIR
from core.schemas import normalize_patent_input


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(value: str, fallback: str = "patent") -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(value or "")).strip("._")
    return cleaned or fallback


def _safe_patent_id(value: Any) -> str:
    return _safe_name(str(value or "patent"), fallback="patent")


def patent_id_from_payload(payload: dict[str, Any] | None) -> str:
    patent = normalize_patent_input(payload or {})
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    return _safe_patent_id(
        patent.get("patent_id")
        or meta.get("registration_number")
        or meta.get("application_number")
        or "patent"
    )


def title_from_payload(payload: dict[str, Any] | None) -> str | None:
    patent = normalize_patent_input(payload or {})
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    title = patent.get("title") or meta.get("title")
    return str(title) if title else None


def patent_workspace(patent_id: str) -> Path:
    return PATENT_DATA_DIR / _safe_patent_id(patent_id)


def ensure_patent_workspace(patent_id: str) -> dict[str, Path]:
    root = patent_workspace(patent_id)
    paths = {
        "root": root,
        "original": root / "original",
        "original_input": root / "original" / "input",
        "original_pdf": root / "original" / "pdf",
        "reports": root / "reports",
        "report_json": root / "reports" / "json",
        "wiki": root / "wiki",
        "extracted": root / "extracted",
        "index": root / "index",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def register_patent_workspace(patent_id: str, title: str | None = None) -> dict[str, str]:
    workspace = ensure_patent_workspace(patent_id)
    manifest_path = _update_manifest(
        _safe_patent_id(patent_id),
        title=title,
        paths={
            "patent_dir": str(workspace["root"]),
            "original": str(workspace["original"]),
            "latest_input": str(workspace["original_input"] / "latest.json"),
            "latest_original_pdf": str(workspace["original_pdf"] / "latest.pdf"),
            "latest_report_json": str(workspace["report_json"] / "latest.json"),
            "wiki": str(workspace["wiki"]),
            "extracted": str(workspace["extracted"]),
            "index": str(workspace["index"]),
            "reports": str(workspace["reports"]),
        },
        event={"type": "workspace_registered"},
    )
    return {"patent_id": _safe_patent_id(patent_id), "patent_dir": str(workspace["root"]), "manifest_path": manifest_path}


def _write_json(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _update_manifest(
    patent_id: str,
    *,
    title: str | None = None,
    paths: dict[str, str] | None = None,
    event: dict[str, Any] | None = None,
) -> str:
    workspace = ensure_patent_workspace(patent_id)
    manifest_path = workspace["root"] / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest.setdefault("patent_id", patent_id)
    if title:
        manifest["title"] = title
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    manifest_paths = manifest.setdefault("paths", {})
    if isinstance(manifest_paths, dict):
        manifest_paths.update(paths or {})
    if event:
        history = manifest.setdefault("history", [])
        if isinstance(history, list):
            history.append({"at": manifest["updated_at"], **event})
            del history[:-50]
    return _write_json(manifest_path, manifest)


def save_patent_input(
    payload: dict[str, Any],
    *,
    source_name: str = "input.json",
    kind: str = "upload",
    timestamp: str | None = None,
) -> dict[str, str]:
    patent_id = patent_id_from_payload(payload)
    title = title_from_payload(payload)
    workspace = ensure_patent_workspace(patent_id)
    stamp = timestamp or _timestamp()
    stem = _safe_name(Path(source_name).stem, fallback="input")
    kind_name = _safe_name(kind, fallback="input")
    input_path = workspace["original_input"] / f"{stamp}_{kind_name}_{stem}.json"
    latest_path = workspace["original_input"] / "latest.json"
    _write_json(input_path, payload)
    _write_json(latest_path, payload)
    manifest_path = _update_manifest(
        patent_id,
        title=title,
        paths={
            "patent_dir": str(workspace["root"]),
            "latest_input": str(latest_path),
            "wiki": str(workspace["wiki"]),
            "reports": str(workspace["reports"]),
        },
        event={"type": "input_saved", "path": str(input_path), "kind": kind_name},
    )
    return {
        "patent_id": patent_id,
        "patent_dir": str(workspace["root"]),
        "input_path": str(input_path),
        "latest_input_path": str(latest_path),
        "manifest_path": manifest_path,
    }


def save_original_pdf(
    source_pdf: str | Path,
    patent: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> dict[str, str]:
    source_path = Path(source_pdf)
    patent_id = patent_id_from_payload(patent)
    title = title_from_payload(patent)
    workspace = ensure_patent_workspace(patent_id)
    stamp = timestamp or _timestamp()
    safe_name = _safe_name(source_path.name, fallback="patent.pdf")
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    dest = workspace["original_pdf"] / f"{stamp}_{safe_name}"
    if source_path.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != dest.resolve():
            shutil.copy2(source_path, dest)
    latest_path = workspace["original_pdf"] / "latest.pdf"
    if dest.exists() and dest.resolve() != latest_path.resolve():
        shutil.copy2(dest, latest_path)
    manifest_path = _update_manifest(
        patent_id,
        title=title,
        paths={
            "patent_dir": str(workspace["root"]),
            "latest_original_pdf": str(latest_path if latest_path.exists() else dest),
            "wiki": str(workspace["wiki"]),
            "reports": str(workspace["reports"]),
        },
        event={"type": "original_pdf_saved", "path": str(dest)},
    )
    return {
        "patent_id": patent_id,
        "patent_dir": str(workspace["root"]),
        "original_pdf_path": str(dest),
        "latest_original_pdf_path": str(latest_path if latest_path.exists() else dest),
        "manifest_path": manifest_path,
    }


def patent_id_from_report_result(result: dict[str, Any]) -> str:
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    valuation = result.get("valuation") if isinstance(result.get("valuation"), dict) else {}
    return _safe_patent_id(
        validation.get("patent_id")
        or valuation.get("patent_id")
        or patent_id_from_payload(result.get("patent_data") if isinstance(result.get("patent_data"), dict) else {})
    )


def title_from_report_result(result: dict[str, Any]) -> str | None:
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    valuation = result.get("valuation") if isinstance(result.get("valuation"), dict) else {}
    title = validation.get("title") or valuation.get("title")
    return str(title) if title else None


def save_report_result(
    job_id: str,
    result: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> dict[str, str]:
    patent_id = patent_id_from_report_result(result)
    title = title_from_report_result(result)
    workspace = ensure_patent_workspace(patent_id)
    stamp = timestamp or _timestamp()
    safe_job_id = _safe_name(job_id, fallback="job")
    report_path = workspace["report_json"] / f"{stamp}_{safe_job_id}.json"
    latest_path = workspace["report_json"] / "latest.json"
    saved = {
        "job_id": job_id,
        "saved_at": datetime.now().isoformat(),
        "result": result,
    }
    _write_json(report_path, saved)
    _write_json(latest_path, saved)
    manifest_path = _update_manifest(
        patent_id,
        title=title,
        paths={
            "patent_dir": str(workspace["root"]),
            "latest_report_json": str(latest_path),
            "wiki": str(workspace["wiki"]),
            "reports": str(workspace["reports"]),
        },
        event={"type": "report_saved", "path": str(report_path), "job_id": job_id},
    )
    return {
        "patent_id": patent_id,
        "patent_dir": str(workspace["root"]),
        "report_json_path": str(report_path),
        "latest_report_json_path": str(latest_path),
        "manifest_path": manifest_path,
    }
