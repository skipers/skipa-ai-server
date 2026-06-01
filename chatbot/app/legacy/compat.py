"""Compatibility helpers for the restored rag.zip pipeline.

The original chatbot expected each patent folder to contain flat files such as
``meta.json`` and ``original.pdf``. The current project stores the same logical
data in the unified ``data/mapped_patent_reports`` layout. These helpers let the
legacy RAG engine read the new layout without rewriting or duplicating data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _relative_or_absolute(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def _extract_input_meta(input_json: Path) -> dict[str, Any]:
    data = _read_json(input_json)
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    report_valuation = result.get("valuation") if isinstance(result.get("valuation"), dict) else {}
    merged: dict[str, Any] = {}
    for source in (validation, report_valuation, meta, data):
        if isinstance(source, dict):
            for key in (
                "patent_id",
                "title",
                "registration_number",
                "application_number",
                "registration_date",
                "application_date",
                "publication_number",
                "publication_date",
                "legal_status",
                "ipc",
                "cpc",
                "keywords",
                "assignee",
                "inventors",
            ):
                value = source.get(key)
                if value not in (None, "", []):
                    merged.setdefault(key, value)
    return merged


def load_compatible_patent_meta(patent_dir: Path) -> dict[str, Any]:
    """Load either legacy metadata or the current manifest-based metadata."""

    for name in ("meta.json", "metadata.json"):
        path = patent_dir / name
        if path.exists():
            meta = _read_json(path)
            if meta:
                return meta

    manifest_path = patent_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"meta.json, metadata.json, or manifest.json not found under: {patent_dir}")

    manifest = _read_json(manifest_path)
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    input_json = Path(paths.get("latest_input") or patent_dir / "original" / "input" / "latest.json")
    report_json = Path(paths.get("latest_report_json") or patent_dir / "reports" / "json" / "latest.json")
    original_pdf = Path(paths.get("latest_original_pdf") or patent_dir / "original" / "pdf" / "latest.pdf")
    if not input_json.is_absolute():
        input_json = patent_dir / input_json
    if not report_json.is_absolute():
        report_json = patent_dir / report_json
    if not original_pdf.is_absolute():
        original_pdf = patent_dir / original_pdf

    extracted = _extract_input_meta(input_json)
    report_meta = _extract_input_meta(report_json)
    patent_id = str(manifest.get("patent_id") or extracted.get("patent_id") or report_meta.get("patent_id") or patent_dir.name)
    title = manifest.get("title") or extracted.get("title") or report_meta.get("title") or patent_id

    meta: dict[str, Any] = {
        **report_meta,
        **extracted,
        "patent_id": patent_id,
        "title": title,
        "registration_number": extracted.get("registration_number") or report_meta.get("registration_number") or patent_id,
        "application_number": extracted.get("application_number") or report_meta.get("application_number"),
        "source_manifest": str(manifest_path),
    }

    if original_pdf.exists():
        original_rel = _relative_or_absolute(original_pdf, patent_dir)
        meta["original_pdf"] = original_rel
        meta["public_original_pdf"] = original_rel
    elif (patent_dir / "extracted" / "all_chunks.jsonl").exists():
        meta["original_pdf"] = ""

    if report_json.exists():
        meta["source_report_json"] = str(report_json)

    report_pdf = patent_dir / "reports" / "pdf" / "latest.pdf"
    if report_pdf.exists():
        report_rel = _relative_or_absolute(report_pdf, patent_dir)
        meta["report_pdf"] = report_rel
        meta["public_report_pdf"] = report_rel

    return meta


def has_current_source_files(patent_dir: Path) -> bool:
    """Return whether the unified folder has raw inputs that can be re-extracted."""

    return (patent_dir / "original" / "pdf" / "latest.pdf").exists() or (
        patent_dir / "reports" / "json" / "latest.json"
    ).exists()
