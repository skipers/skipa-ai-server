"""Patent PDF extraction worker implementation."""

from __future__ import annotations

import logging
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.storage import object_storage
from workers.backend_client import BackendCallbackClient
from workers.config import WorkerConfig, load_worker_config
from workers.rabbitmq import RabbitWorker

LOGGER = logging.getLogger(__name__)

PATENT_EXTRACT_RESULT_FIELDS = (
    "title",
    "applicationNumber",
    "registrationNumber",
    "publicationNumber",
    "announcementNumber",
    "applicationDate",
    "registrationDate",
    "publicationDate",
    "announcementDate",
    "ipcCodes",
    "cpcCodes",
    "applicant",
    "inventor",
    "expiryDate",
    "citationCount",
    "examinationClaimCount",
    "managementNumber",
    "businessField",
    "techField",
    "relatedProducts",
    "filingCountry",
    "isJointApplication",
    "jointApplicant",
    "initialDepartment",
    "keywords",
    "summary",
)


def _require(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None or value == "":
        raise ValueError(f"PATENT_EXTRACT payload missing required field: {field}")
    return value


def parsed_object_key_for_pdf(object_key: str) -> str:
    key = str(object_key or "").strip("/")
    if not key:
        raise ValueError("PATENT_EXTRACT payload missing required field: objectKey")
    parent = key.rsplit("/", 1)[0] if "/" in key else ""
    return f"{parent}/parsed.json" if parent else "parsed.json"


def _clean_text(value: Any) -> str | None:
    if isinstance(value, list):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
        return text or None
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    return text


def _first_code(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return _clean_text(values[0])
    return _clean_text(values)


def _code_list(values: Any) -> list[str]:
    if isinstance(values, list):
        return [text for item in values if (text := _clean_text(item))]
    text = _clean_text(values)
    return [text] if text else []


def _join_names(values: Any) -> str | None:
    if isinstance(values, list):
        return ", ".join(str(item) for item in values if _clean_text(item)) or None
    return _clean_text(values)


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return None


def _list_or_codes(*values: Any) -> list[str]:
    for value in values:
        codes = _code_list(value)
        if codes:
            return codes
    return []


def _country_from_identifier(identifier: str | None) -> str:
    text = (identifier or "").strip().upper()
    if text.startswith("US"):
        return "US"
    if text.startswith("EP"):
        return "EP"
    if text.startswith("CN"):
        return "CN"
    if text.startswith("JP"):
        return "JP"
    if text.startswith("TW"):
        return "TW"
    return "KR"


def _int_or_none(value: Any) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r"\d+", text.replace(",", ""))
    return int(match.group(0)) if match else None


def _date(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    korean = re.match(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if korean:
        year, month, day = korean.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    normalized = text.replace(".", "-").replace("/", "-")
    iso = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", normalized)
    if iso:
        year, month, day = iso.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return text


def _expiry_date(application_date: str | None) -> str | None:
    if not application_date:
        return None
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", application_date)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year) + 20:04d}-{month}-{day}"


def map_patent_extract_result(parsed: dict[str, Any]) -> dict[str, Any]:
    raw = parsed.get("raw") if isinstance(parsed.get("raw"), dict) else parsed
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    normalized = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    normalized_meta = normalized.get("meta") if isinstance(normalized.get("meta"), dict) else {}

    title = _first_text(meta.get("발명의_명칭"), normalized_meta.get("title"), parsed.get("title"))
    abstract = _first_text(meta.get("요약"), normalized.get("description_summary"), parsed.get("summary"))
    keywords = parsed.get("keywords") or normalized_meta.get("keywords") or raw.get("keywords")
    if not isinstance(keywords, list):
        from document_processing.patent_pdf_extractor import extract_keywords

        keywords = extract_keywords(title or "", abstract or "")
    brief = parsed.get("brief_summary") or normalized.get("brief_summary") or raw.get("brief_summary")
    if not isinstance(brief, dict):
        from document_processing.patent_pdf_extractor import make_brief_summary

        brief = make_brief_summary(title or "", abstract or "")

    application_number = _first_text(meta.get("출원번호"), normalized_meta.get("application_number"))
    registration_number = _first_text(
        meta.get("등록번호"),
        normalized_meta.get("registration_number"),
        normalized.get("patent_id"),
    )
    application_date = _date(_first_text(meta.get("출원일자"), normalized_meta.get("application_date")))
    ipc_codes = _list_or_codes(meta.get("국제특허분류(IPC)"), normalized_meta.get("ipc"))
    cpc_codes = _list_or_codes(meta.get("CPC특허분류"), normalized_meta.get("cpc"))
    overview = _clean_text(brief.get("개요")) or abstract
    core_content = _clean_text(brief.get("핵심_내용")) or abstract
    result = {
        "title": title,
        "applicationNumber": application_number,
        "registrationNumber": registration_number,
        "publicationNumber": _first_text(meta.get("공개번호"), normalized_meta.get("publication_number")),
        "announcementNumber": _first_text(meta.get("공고번호"), normalized_meta.get("announcement_number")),
        "applicationDate": application_date,
        "registrationDate": _date(_first_text(meta.get("등록일자"), normalized_meta.get("registration_date"))),
        "publicationDate": _date(_first_text(meta.get("공개일자"), normalized_meta.get("publication_date"))),
        "announcementDate": _date(
            _first_text(
                meta.get("공고일자"),
                normalized.get("legal", {}).get("notice_date") if isinstance(normalized.get("legal"), dict) else None,
            )
        ),
        "ipcCodes": ipc_codes,
        "cpcCodes": cpc_codes,
        "applicant": _first_text(meta.get("특허권자"), normalized_meta.get("assignee")),
        "inventor": _join_names(meta.get("발명자") or normalized_meta.get("inventors")),
        "expiryDate": _expiry_date(application_date),
        "citationCount": None,
        "examinationClaimCount": _int_or_none(meta.get("청구항_수") or normalized_meta.get("total_claims")),
        "managementNumber": None,
        "businessField": None,
        "techField": None,
        "relatedProducts": [],
        "filingCountry": _country_from_identifier(registration_number or application_number),
        "isJointApplication": False,
        "jointApplicant": None,
        "initialDepartment": None,
        "keywords": keywords,
        "summary": abstract or overview or core_content,
    }
    return {field: result.get(field) for field in PATENT_EXTRACT_RESULT_FIELDS}


class PatentExtractHandler:
    def __init__(self, config: WorkerConfig | None = None) -> None:
        self.config = config or load_worker_config()
        self.backend = BackendCallbackClient(self.config)

    def __call__(self, payload: dict[str, Any]) -> None:
        message_type = payload.get("type")
        if message_type != "PATENT_EXTRACT":
            raise ValueError(f"Unsupported patent extract message type: {message_type}")

        extract_job_id = _require(payload, "extractJobId")
        object_key = _require(payload, "objectKey")

        try:
            with tempfile.TemporaryDirectory(prefix=f"patent-extract-{extract_job_id}-") as tmp_dir:
                pdf_path = Path(tmp_dir) / "patent.pdf"
                downloaded = object_storage.download_file(str(object_key), pdf_path)
                if not downloaded or not pdf_path.exists():
                    raise RuntimeError(f"MinIO PDF 다운로드에 실패했습니다: {object_key}")
                from services.evidence_collection_service import PatentMetadataExtractionService

                parsed = PatentMetadataExtractionService().extract_from_pdf(pdf_path)
                raw = parsed.get("raw") if isinstance(parsed.get("raw"), dict) else {}
                if raw.get("error"):
                    raise RuntimeError(str(raw["error"]))
                parsed_object_key = parsed_object_key_for_pdf(str(object_key))
                stored = object_storage.put_json(parsed_object_key, parsed)
                if not stored:
                    raise RuntimeError(f"MinIO parsed.json 저장에 실패했습니다: {parsed_object_key}")
                result = map_patent_extract_result(parsed)
                parsed_json_key = stored.get("object_key") or parsed_object_key
            self.backend.complete_patent_extract(extract_job_id, parsed_json_key, result)
            LOGGER.info(
                "Completed patent extraction extractJobId=%s objectKey=%s parsedObjectKey=%s",
                extract_job_id,
                object_key,
                parsed_object_key,
            )
        except Exception as exc:
            LOGGER.exception(
                "Patent extraction failed extractJobId=%s objectKey=%s",
                extract_job_id,
                object_key,
            )
            try:
                self.backend.fail_patent_extract(extract_job_id, str(exc))
            except Exception:
                LOGGER.exception("Patent extract fail callback failed extractJobId=%s", extract_job_id)
                raise


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_worker_config()
    RabbitWorker(config, config.patent_extract_queue, PatentExtractHandler(config)).run_forever()


if __name__ == "__main__":
    run()
