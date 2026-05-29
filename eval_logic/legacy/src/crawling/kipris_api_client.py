"""
Small KIPRIS Plus API client for similar-patent enrichment.

The public KIPRIS Plus patent/utility endpoints are XML-first and their item
field names can differ by operation. This client keeps raw responses available
while also exposing a best-effort normalized shape for downstream analysis.

Environment:
    KIPRIS_API_KEY=...  # KIPRIS Plus ServiceKey
"""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from core.paths import ROOT_DIR

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")

BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"
CITING_BASE_URL = "http://plus.kipris.or.kr/openapi/rest/CitingService"


def compact_patent_number(value: str | None) -> str:
    """Keep only letters/numbers for API matching and cache filenames."""
    return re.sub(r"[^0-9A-Za-z]", "", value or "")


def normalize_application_number(value: str | None) -> str:
    """KIPRIS domestic APIs usually expect application numbers without hyphens."""
    compact = compact_patent_number(value)
    if compact.startswith("KR"):
        compact = compact[2:]
    return compact


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _element_to_obj(elem: ET.Element) -> Any:
    children = list(elem)
    if not children:
        return (elem.text or "").strip()

    grouped: dict[str, list[Any]] = {}
    for child in children:
        grouped.setdefault(_strip_namespace(child.tag), []).append(_element_to_obj(child))

    result: dict[str, Any] = {}
    for key, values in grouped.items():
        result[key] = values[0] if len(values) == 1 else values
    return result


def parse_xml(text: str) -> dict[str, Any]:
    root = ET.fromstring(text)
    return {_strip_namespace(root.tag): _element_to_obj(root)}


def iter_values(obj: Any) -> list[Any]:
    if isinstance(obj, dict):
        values: list[Any] = []
        for value in obj.values():
            values.extend(iter_values(value))
        return values
    if isinstance(obj, list):
        values = []
        for value in obj:
            values.extend(iter_values(value))
        return values
    return [obj]


def find_first(obj: Any, keys: tuple[str, ...]) -> str:
    """Recursively find the first non-empty value for any likely field name."""
    normalized = {k.lower().replace("_", "").replace("-", "") for k in keys}

    def walk(value: Any) -> str:
        if isinstance(value, dict):
            for key, child in value.items():
                clean_key = key.lower().replace("_", "").replace("-", "")
                if clean_key in normalized:
                    if isinstance(child, (str, int, float)) and str(child).strip():
                        return str(child).strip()
                    nested = walk(child)
                    if nested:
                        return nested
            for child in value.values():
                nested = walk(child)
                if nested:
                    return nested
        elif isinstance(value, list):
            for child in value:
                nested = walk(child)
                if nested:
                    return nested
        return ""

    return walk(obj)


def find_all_by_key(obj: Any, keys: tuple[str, ...]) -> list[str]:
    normalized = {k.lower().replace("_", "").replace("-", "") for k in keys}
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                clean_key = key.lower().replace("_", "").replace("-", "")
                if clean_key in normalized and isinstance(child, (str, int, float)):
                    text = str(child).strip()
                    if text:
                        found.append(text)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return list(dict.fromkeys(found))


def sanitize_error(value: Any) -> str:
    text = str(value)
    text = re.sub(r"ServiceKey=[^&\\s)'\\\"]+", "ServiceKey=***", text)
    return re.sub(r"accessKey=[^&\\s)'\\\"]+", "accessKey=***", text)


def get_items(obj: Any) -> list[dict[str, Any]]:
    """Return likely response item dictionaries from a KIPRIS XML/JSON object."""
    items: list[dict[str, Any]] = []

    def walk(value: Any, parent_key: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"item", "items"}:
                    if isinstance(child, list):
                        items.extend(v for v in child if isinstance(v, dict))
                    elif isinstance(child, dict):
                        items.append(child)
                walk(child, key)
        elif isinstance(value, list):
            for child in value:
                walk(child, parent_key)

    walk(obj)
    if items:
        return items
    return [obj] if isinstance(obj, dict) else []


def get_citing_info_records(obj: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() == "citinginfo":
                    if isinstance(child, list):
                        records.extend(item for item in child if isinstance(item, dict))
                    elif isinstance(child, dict):
                        records.append(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return records


def count_citing_documents(obj: Any) -> int:
    records = get_citing_info_records(obj)
    if not records:
        return 0
    application_numbers = []
    for record in records:
        app_no = find_first(record, ("ApplicationNumber", "applicationNumber", "출원번호"))
        if app_no:
            application_numbers.append(normalize_application_number(app_no))
    return len(set(application_numbers)) if application_numbers else len(records)


@dataclass
class KiprisApiClient:
    service_key: str | None = None
    base_url: str = BASE_URL
    timeout: int = 20
    sleep_seconds: float = 0.2

    def __post_init__(self) -> None:
        if self.service_key is None:
            self.service_key = os.environ.get("KIPRIS_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.service_key)

    def request(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.service_key:
            raise RuntimeError("KIPRIS_API_KEY 환경변수가 설정되어 있지 않습니다.")
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("KIPRIS API 호출에는 requests 패키지가 필요합니다. pip install requests") from exc

        url = f"{self.base_url}/{operation}"
        request_params = {k: v for k, v in params.items() if v not in (None, "")}
        request_params["ServiceKey"] = self.service_key

        response = requests.get(url, params=request_params, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.sleep_seconds)

        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type or request_params.get("type") == "json":
            try:
                data = response.json()
            except json.JSONDecodeError:
                pass
            else:
                self._raise_for_api_error(data)
                return data
        data = parse_xml(response.text)
        self._raise_for_api_error(data)
        return data

    def _raise_for_api_error(self, data: dict[str, Any]) -> None:
        result_code = find_first(data, ("resultCode",))
        result_msg = find_first(data, ("resultMsg",))
        if result_code and result_code not in {"00"}:
            raise RuntimeError(f"KIPRIS API error {result_code}: {result_msg or '-'}")

    def citing_request(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.service_key:
            raise RuntimeError("KIPRIS_API_KEY 환경변수가 설정되어 있지 않습니다.")
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("KIPRIS API 호출에는 requests 패키지가 필요합니다. pip install requests") from exc

        url = f"{CITING_BASE_URL}/{operation}"
        request_params = {k: v for k, v in params.items() if v not in (None, "")}
        request_params["accessKey"] = self.service_key

        response = requests.get(url, params=request_params, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.sleep_seconds)

        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type or request_params.get("type") == "json":
            try:
                data = response.json()
            except json.JSONDecodeError:
                pass
            else:
                self._raise_for_citing_api_error(data)
                return data
        data = parse_xml(response.text)
        self._raise_for_citing_api_error(data)
        return data

    def _raise_for_citing_api_error(self, data: dict[str, Any]) -> None:
        result_code = find_first(data, ("resultCode",))
        result_msg = find_first(data, ("resultMsg",))
        if result_code and result_code not in {"00"}:
            raise RuntimeError(f"KIPRIS CitingService error {result_code}: {result_msg or '-'}")

    def advanced_search(
        self,
        *,
        invention_title: str = "",
        abstract: str = "",
        ipc_number: str = "",
        application_date: str = "",
        page_no: int = 1,
        num_rows: int = 10,
    ) -> dict[str, Any]:
        params = {
            "inventionTitle": invention_title,
            "astrtCont": abstract,
            "ipcNumber": ipc_number,
            "applicationDate": application_date,
            "patent": "true",
            "utility": "false",
            "pageNo": page_no,
            "numOfRows": num_rows,
        }
        return self.request("getAdvancedSearch", params)

    def bibliography_detail(self, application_number: str) -> dict[str, Any]:
        return self.request(
            "getBibliographyDetailInfoSearch",
            {"applicationNumber": normalize_application_number(application_number)},
        )

    def bibliography_summary(self, application_number: str) -> dict[str, Any]:
        return self.request(
            "getBibliographySumryInfoSearch",
            {"applicationNumber": normalize_application_number(application_number)},
        )

    def optional_operation(self, operation: str, application_number: str) -> dict[str, Any]:
        return self.request(operation, {"applicationNumber": normalize_application_number(application_number)})

    def citing_info(self, application_number: str) -> dict[str, Any]:
        return self.citing_request(
            "citingInfo",
            {"standardCitationApplicationNumber": normalize_application_number(application_number)},
        )

    def find_application_by_title(self, title: str) -> str:
        if not title:
            return ""
        data = self.advanced_search(invention_title=title, num_rows=3)
        for item in get_items(data):
            app_no = find_first(item, ("applicationNumber", "applicationNo", "applno", "출원번호"))
            if app_no:
                return normalize_application_number(app_no)
        return ""

    def fetch_patent_bundle(
        self,
        *,
        application_number: str = "",
        title: str = "",
        extra_operations: list[str] | None = None,
    ) -> dict[str, Any]:
        app_no = normalize_application_number(application_number)
        errors: list[str] = []
        raw: dict[str, Any] = {}

        if not app_no and title:
            try:
                app_no = self.find_application_by_title(title)
            except Exception as exc:
                errors.append(f"title_search: {sanitize_error(exc)}")

        if app_no:
            for name, operation in [
                ("bibliography_detail", self.bibliography_detail),
                ("bibliography_summary", self.bibliography_summary),
                ("citing_info", self.citing_info),
            ]:
                try:
                    raw[name] = operation(app_no)
                except Exception as exc:
                    errors.append(f"{name}: {sanitize_error(exc)}")

            for operation_name in extra_operations or []:
                try:
                    raw[operation_name] = self.optional_operation(operation_name, app_no)
                except Exception as exc:
                    errors.append(f"{operation_name}: {sanitize_error(exc)}")
        else:
            errors.append("application_number_not_found")

        citation_count = count_citing_documents(raw["citing_info"]) if "citing_info" in raw else None

        return {
            "application_number": app_no,
            "raw": raw,
            "citation_count": citation_count,
            "errors": errors,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }


def normalize_patent_detail(candidate: dict[str, Any], bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge candidate data and KIPRIS raw bundle into one stable schema."""
    bundle = bundle or {}
    raw = bundle.get("raw", {})
    merged_sources = [candidate, raw]

    def first(keys: tuple[str, ...], fallback: Any = "") -> str:
        for source in merged_sources:
            value = find_first(source, keys)
            if value:
                return value
        return str(fallback or "")

    title = first(("inventionTitle", "title", "발명명칭"), candidate.get("title") or candidate.get("발명명칭"))
    application_number = first(
        ("applicationNumber", "applicationNo", "applno", "출원번호"),
        bundle.get("application_number") or candidate.get("application_number") or candidate.get("출원번호"),
    )
    patent_no = first(
        ("registrationNumber", "registerNumber", "publicationNumber", "patentNumber", "patent_no", "등록번호"),
        candidate.get("patent_no"),
    )
    applicant = first(("applicantName", "applicant", "출원인"), candidate.get("applicant") or candidate.get("출원인"))
    abstract = first(("abstract", "astrtCont", "summary", "요약"), candidate.get("abstract") or candidate.get("요약"))
    legal_status = first(("registerStatus", "legalStatus", "등록상태"), candidate.get("legal_status") or candidate.get("등록상태"))

    ipc_values = find_all_by_key(raw, ("ipcNumber", "ipcCode", "ipc")) or []
    candidate_ipc = candidate.get("ipc") or candidate.get("IPC") or candidate.get("ipc_code")
    if candidate_ipc:
        if isinstance(candidate_ipc, list):
            ipc_values.extend(str(v) for v in candidate_ipc)
        else:
            ipc_values.extend(part.strip() for part in re.split(r"[,;]+", str(candidate_ipc)))
    ipc_values = [v for v in dict.fromkeys(v.strip() for v in ipc_values if v and len(v.strip()) >= 3)]

    claim_texts = find_all_by_key(raw, ("claim", "claimText", "claims", "청구항"))
    citation_count = bundle.get("citation_count")
    citation_count = citation_count if citation_count not in (None, "") else first(
        (
            "citationCount",
            "citedCount",
            "citedByCount",
            "forwardCitationCount",
            "citedPatentCount",
            "피인용수",
            "피인용횟수",
        ),
        candidate.get("citation_count"),
    )

    return {
        "rank": candidate.get("rank"),
        "patent_no": patent_no or candidate.get("patent_no", ""),
        "application_number": normalize_application_number(application_number),
        "title": title,
        "applicant": applicant,
        "inventors": find_all_by_key(raw, ("inventorName", "inventor", "발명자")),
        "application_date": first(("applicationDate", "출원일자"), candidate.get("application_date")),
        "registration_date": first(("registrationDate", "등록일자"), candidate.get("registration_date")),
        "publication_date": first(("publicationDate", "공개일자"), candidate.get("publication_date")),
        "legal_status": legal_status,
        "ipc": ipc_values,
        "abstract": abstract,
        "claims": claim_texts,
            "citation_count": citation_count if citation_count not in (None, "") else None,
        "similarity_basis": candidate.get("similarity_basis") or candidate.get("유사도") or "",
        "source_candidate": candidate,
        "source_api": {
            "status": "success" if raw else "fallback",
            "errors": [sanitize_error(error) for error in bundle.get("errors", [])],
            "fetched_at": bundle.get("fetched_at"),
        },
    }


def cache_path(cache_dir: Path, identifier: str) -> Path:
    safe_name = compact_patent_number(identifier) or "unknown"
    return cache_dir / f"{safe_name}.json"
