"""Shared report generation service for API, CLI, and queue workers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.patent_valuation_graph import PatentValuationWorkflow, PatentValuationWorkflowOptions, default_similar_date_from
from apps.api.storage import object_storage
from core.paths import INPUT_SAMPLE_FILE, RESULTS_DIR, SAMPLE_INPUT_DIR
from core.report_payload import frontend_report_payload
from core.report_naming import safe_registration_number_from_result


SERVER_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
DEFAULT_PROFILE = "full"


def default_patent_prefix() -> str:
    return (os.getenv("MINIO_PATENT_PREFIX", "patents").strip("/") or "patents")


def default_input_list_prefix() -> str:
    return f"{default_patent_prefix()}/"


def default_output_key_template() -> str:
    return f"{default_patent_prefix()}/{{patent_id}}/reports/{{report_id}}/report.json"


def default_parsed_object_key_template() -> str:
    return os.getenv(
        "EVAL_LOGIC_PARSED_OBJECT_KEY_TEMPLATE",
        f"{default_patent_prefix()}/{{patent_id}}/parsed.json",
    )


@dataclass(frozen=True)
class InputSource:
    """A local file or MinIO object used as a workflow input."""

    backend: str
    label: str
    path: Path | None = None
    object_key: str | None = None


@dataclass(frozen=True)
class ReportGenerationOptions:
    """Runtime knobs for report generation."""

    profile: str = DEFAULT_PROFILE
    enable_market: bool | None = None
    enable_llm: bool | None = None
    enable_business_rag: bool | None = None
    similar_use_llm: bool | None = None
    rag_top_k: int | None = None
    input_prefix: str | None = None
    output_key_template: str | None = None
    local_output: bool = False


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 최상위 값은 object여야 합니다: {path}")
    return payload


def load_source_json(source: InputSource) -> dict[str, Any]:
    if source.backend == "minio":
        if not source.object_key:
            raise ValueError("MinIO 입력 object key가 없습니다.")
        payload = object_storage.get_json(source.object_key)
        if not isinstance(payload, dict):
            raise ValueError(f"MinIO 입력 JSON을 읽을 수 없습니다: {source.object_key}")
        return payload
    if not source.path:
        raise ValueError("로컬 입력 경로가 없습니다.")
    return load_json(source.path)


def resolve_input_files(input_path: str | None = None) -> list[Path]:
    def parsed_files_in_data_root(root: Path) -> list[Path]:
        files = sorted(root.glob(f"{default_patent_prefix()}/*/parsed.json"))
        if files:
            return files
        return sorted(path for path in root.glob("*/parsed.json") if path.parent.name.startswith("10-"))

    if input_path:
        candidate = Path(input_path)
        if not candidate.exists():
            raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")
        if candidate.is_file():
            return [candidate]
        if candidate.is_dir():
            if (candidate / "parsed.json").exists():
                return [candidate / "parsed.json"]
            files = parsed_files_in_data_root(candidate)
            if not files:
                files = sorted(candidate.glob("*.json"))
            if not files:
                raise FileNotFoundError(f"디렉터리에 JSON 파일이 없습니다: {input_path}")
            return files
        raise ValueError(f"지원하지 않는 입력 경로입니다: {input_path}")

    if INPUT_SAMPLE_FILE.exists():
        return [INPUT_SAMPLE_FILE]

    files = parsed_files_in_data_root(SERVER_DATA_DIR)
    if not files:
        files = sorted(SAMPLE_INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"기본 입력 JSON을 찾을 수 없습니다: {SERVER_DATA_DIR}")
    return files


def input_sources_from_paths(input_path: str | None = None) -> list[InputSource]:
    return [InputSource("local", str(path), path=path) for path in resolve_input_files(input_path)]


def strip_storage_prefix(object_key: str) -> str:
    key = object_key.strip("/")
    storage_prefix = str(getattr(object_storage, "prefix", "") or "").strip("/")
    if storage_prefix and key.startswith(f"{storage_prefix}/"):
        return key[len(storage_prefix) + 1 :]
    return key


def input_prefix_candidates(prefix: str) -> list[str]:
    base_prefix = prefix.lstrip("/")
    storage_prefix = str(getattr(object_storage, "prefix", "") or "").strip("/")
    prefixes = [base_prefix]
    if storage_prefix and not base_prefix.startswith(f"{storage_prefix}/"):
        prefixes.append(f"{storage_prefix}/{base_prefix}")
    return list(dict.fromkeys(prefixes))


def input_sources_from_minio(prefix: str | None = None) -> list[InputSource]:
    if not object_storage.enabled():
        return []

    object_keys: list[str] = []
    for candidate_prefix in input_prefix_candidates(prefix or default_input_list_prefix()):
        object_keys.extend(
            key
            for key in object_storage.list_object_keys(candidate_prefix)
            if key.endswith("/parsed.json")
        )
    return [InputSource("minio", key, object_key=key) for key in sorted(dict.fromkeys(object_keys))]


def resolve_input_sources(
    input_path: str | None = None,
    input_prefix: str | None = None,
) -> list[InputSource]:
    if input_path:
        candidate = Path(input_path)
        if candidate.exists():
            return input_sources_from_paths(input_path)
        if object_storage.enabled():
            return [InputSource("minio", input_path, object_key=input_path.strip("/"))]
        raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")

    if INPUT_SAMPLE_FILE.exists():
        return input_sources_from_paths(str(INPUT_SAMPLE_FILE))

    minio_sources = input_sources_from_minio(input_prefix)
    if minio_sources:
        return minio_sources
    return input_sources_from_paths(None)


def source_from_patent_id(patent_id: int | str, object_key: str | None = None) -> InputSource:
    key = object_key or default_parsed_object_key_template().format(patent_id=patent_id).strip("/")
    return InputSource("minio", key, object_key=key)


def output_path_for_result(
    source_path: Path,
    result: dict[str, Any],
    report_id: int | str | None = None,
) -> Path:
    return RESULTS_DIR / safe_registration_number_from_result(result) / "report.json"


def registration_number_from_result(result: dict[str, Any]) -> str:
    report = result.get("report") if isinstance(result.get("report"), dict) else {}
    patent = report.get("patent") if isinstance(report.get("patent"), dict) else {}
    value = (
        patent.get("registration_number")
        or patent.get("id")
        or ((result.get("validation") or {}).get("patent_id") if isinstance(result.get("validation"), dict) else None)
    )
    if value:
        return str(value)
    return safe_registration_number_from_result(result)


def output_key_for_result(
    source: InputSource,
    result: dict[str, Any],
    template: str | None = None,
    report_id: int | str | None = None,
    patent_id: int | str | None = None,
) -> str:
    registration_number = registration_number_from_result(result)
    resolved_patent_id = patent_id or registration_number
    if not report_id:
        raise ValueError("MinIO report.json 저장에는 report_id가 필요합니다.")

    if source.backend == "minio" and source.object_key:
        source_key = strip_storage_prefix(source.object_key)
        if source_key.endswith("/parsed.json"):
            return f"{source_key.rsplit('/', 1)[0]}/reports/{report_id}/report.json"

    return (template or default_output_key_template()).format(
        registration_number=registration_number,
        patent_id=resolved_patent_id,
        report_id=report_id,
    ).strip("/")


def build_workflow_options(options: ReportGenerationOptions | None = None) -> PatentValuationWorkflowOptions:
    options = options or ReportGenerationOptions()
    is_full = options.profile == "full"

    def choose(value: bool | None, default: bool) -> bool:
        return default if value is None else value

    return PatentValuationWorkflowOptions(
        enable_market=choose(options.enable_market, is_full),
        enable_llm=choose(options.enable_llm, is_full),
        enable_business_rag=choose(options.enable_business_rag, is_full),
        enable_similar_analysis=True,
        similar_use_kipris_crawler=True,
        similar_force_refresh=True,
        similar_max_pages=5,
        similar_max_results=10,
        similar_date_from=default_similar_date_from(),
        similar_date_to="",
        similar_use_llm=choose(options.similar_use_llm, is_full),
        enable_pdf_metadata_extraction=False,
        rag_top_k=options.rag_top_k,
    )


class ReportGenerationService:
    """Generate report.json from parsed patent JSON and store it."""

    def __init__(self, options: ReportGenerationOptions | None = None) -> None:
        self.options = options or ReportGenerationOptions()
        self.workflow_options = build_workflow_options(self.options)

    def generate_from_source(
        self,
        source: InputSource,
        report_id: int | str | None = None,
        patent_id: int | str | None = None,
    ) -> dict[str, Any]:
        return self.generate_from_patent(
            load_source_json(source),
            source=source,
            report_id=report_id,
            patent_id=patent_id,
        )

    def generate_from_patent(
        self,
        patent: dict[str, Any],
        source: InputSource | None = None,
        report_id: int | str | None = None,
        patent_id: int | str | None = None,
    ) -> dict[str, Any]:
        source = source or InputSource("inline", "inline")
        workflow = PatentValuationWorkflow(self.workflow_options)
        result = workflow.run(patent)
        storage = self.save_result(source, result, report_id=report_id, patent_id=patent_id)
        return {
            "status": result.get("status"),
            "report_id": report_id,
            "patent_id": patent_id,
            "source": {
                "backend": source.backend,
                "label": source.label,
                "object_key": source.object_key,
                "path": str(source.path) if source.path else None,
            },
            "storage": storage,
            "report_key": storage.get("object_key") or storage.get("path"),
            "result": result,
        }

    def save_result(
        self,
        source: InputSource,
        result: dict[str, Any],
        report_id: int | str | None = None,
        patent_id: int | str | None = None,
    ) -> dict[str, Any]:
        if object_storage.enabled() and not self.options.local_output:
            object_key = output_key_for_result(
                source,
                result,
                template=self.options.output_key_template,
                report_id=report_id,
                patent_id=patent_id,
            )
            stored = object_storage.put_json(object_key, frontend_report_payload(result))
            if not stored:
                raise RuntimeError("MinIO 결과 저장에 실패했습니다.")
            return stored

        if source.path:
            out_path = output_path_for_result(source.path, result, report_id=report_id)
        else:
            out_path = RESULTS_DIR / safe_registration_number_from_result(result) / "report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as file:
            json.dump(frontend_report_payload(result), file, ensure_ascii=False, indent=2)
        return {"backend": "local", "path": str(out_path)}
