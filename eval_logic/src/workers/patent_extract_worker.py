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


def _clean_text(value: Any) -> str | None:
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
    meta = parsed.get("meta") if isinstance(parsed.get("meta"), dict) else {}
    title = _clean_text(meta.get("발명의_명칭"))
    abstract = _clean_text(meta.get("요약"))
    keywords = parsed.get("keywords")
    if not isinstance(keywords, list):
        from document_processing.patent_pdf_extractor import extract_keywords

        keywords = extract_keywords(title or "", abstract or "")
    brief = parsed.get("brief_summary")
    if not isinstance(brief, dict):
        from document_processing.patent_pdf_extractor import make_brief_summary

        brief = make_brief_summary(title or "", abstract or "")

    application_date = _date(meta.get("출원일자"))
    ipc_codes = _code_list(meta.get("국제특허분류(IPC)"))
    cpc_codes = _code_list(meta.get("CPC특허분류"))
    overview = _clean_text(brief.get("개요")) or abstract
    core_content = _clean_text(brief.get("핵심_내용")) or abstract
    result = {
        "title": title,
        "applicationNumber": _clean_text(meta.get("출원번호")),
        "registrationNumber": _clean_text(meta.get("등록번호")),
        "publicationNumber": _clean_text(meta.get("공개번호")),
        "announcementNumber": _clean_text(meta.get("공고번호")),
        "applicationDate": application_date,
        "registrationDate": _date(meta.get("등록일자")),
        "publicationDate": _date(meta.get("공개일자")),
        "announcementDate": _date(meta.get("공고일자")),
        "ipcCodes": ipc_codes,
        "cpcCodes": cpc_codes,
        "applicant": _clean_text(meta.get("특허권자")),
        "inventor": _join_names(meta.get("발명자")),
        "expiryDate": _expiry_date(application_date),
        "citationCount": None,
        "examinationClaimCount": _int_or_none(meta.get("청구항_수")),
        "managementNumber": None,
        "businessField": None,
        "techField": None,
        "relatedProducts": [],
        "filingCountry": "KR",
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
                from document_processing.patent_pdf_extractor import parse_patent

                parsed = parse_patent(pdf_path)
                if parsed.get("error"):
                    raise RuntimeError(str(parsed["error"]))
                result = map_patent_extract_result(parsed)
            self.backend.complete_patent_extract(extract_job_id, result)
            LOGGER.info("Completed patent extraction extractJobId=%s objectKey=%s", extract_job_id, object_key)
        except Exception as exc:
            LOGGER.exception("Patent extraction failed extractJobId=%s objectKey=%s", extract_job_id, object_key)
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
