"""특허 평가 전 보조 자료 수집 서비스입니다.

``src/document_processing`` 아래의 PDF 메타데이터 추출 기능과
``src/business_rag`` 아래의 RAG 기반 사업화 현황 추정 기능을 현재 평가
파이프라인에 연결합니다.

로컬 개발 환경에 PDF/RAG 전용 의존성이 아직 설치되지 않은 경우에도 기본
가치 평가 서비스가 그대로 실행될 수 있도록, 무거운 모듈은 실행 시점에
지연 import합니다.
"""

from __future__ import annotations

import time
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from core.paths import SAMPLE_PATENT_DOCUMENT_DIR
from core.schemas import CollectedEvidence, EvaluationStepResult, normalize_patent_input


@dataclass(slots=True)
class EvidenceCollectionOptions:
    """보조 자료 수집 단계의 실행 옵션입니다."""

    enable_pdf_metadata_extraction: bool = True
    enable_business_rag: bool = False
    rag_top_k: int | None = None


def _first_text(*values: Any) -> str:
    """후보 값 중 첫 번째 비어 있지 않은 문자열을 반환합니다."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text != "-":
            return text
    return ""


def _split_people(value: Any) -> list[str]:
    """특허권자/발명자처럼 쉼표 또는 줄바꿈으로 들어온 값을 리스트로 바꿉니다."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip() and str(item).strip() != "-"]
    text = _first_text(value)
    if not text:
        return []
    normalized = text.replace("\n", ",").replace(";", ",")
    return [part.strip() for part in normalized.split(",") if part.strip() and part.strip() != "-"]


def _split_values(value: Any) -> list[str]:
    """선행기술 문헌처럼 여러 구분자가 섞인 문자열을 리스트로 바꿉니다."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip() and str(item).strip() != "-"]
    text = _first_text(value)
    if not text:
        return []
    normalized = text.replace("\n", ",").replace(";", ",")
    return [part.strip() for part in normalized.split(",") if part.strip() and part.strip() != "-"]


def _normalize_date(value: Any) -> str:
    """한국 특허공보 날짜 문자열을 API 입력용 YYYY-MM-DD로 정규화합니다."""
    text = _first_text(value)
    if not text:
        return ""
    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text


def _normalize_classification_codes(value: Any) -> list[str]:
    """IPC/CPC 값을 API 샘플과 비슷한 코드 리스트로 정리합니다."""
    codes = []
    for item in _split_values(value):
        cleaned = re.sub(r"\s*\(\d{4}(?:\.\d+)?\)\s*$", "", item).strip()
        cleaned = re.sub(r"^([A-Z]\d{2}[A-Z])\s+", r"\1", cleaned)
        if cleaned and cleaned not in codes:
            codes.append(cleaned)
    return codes


def _build_description_summary(abstract: str, description: dict[str, Any]) -> str:
    """LLM 평가가 바로 사용할 수 있도록 초록과 명세서 핵심 섹션을 합칩니다."""
    parts: list[str] = []
    if abstract:
        parts.append(f"[요약] {abstract}")
    labels = [
        ("technical_field", "기술분야"),
        ("problem_to_solve", "해결과제"),
        ("solution", "해결수단"),
        ("advantageous_effects", "발명의 효과"),
    ]
    for key, label in labels:
        value = _first_text(description.get(key))
        if value:
            parts.append(f"[{label}] {value}")
    summary = "\n".join(parts).strip()
    if len(summary) > 6000:
        return summary[:6000].rstrip() + "..."
    return summary


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return None


def _deep_merge_missing(base: dict[str, Any], additions: dict[str, Any]) -> dict[str, Any]:
    """기존 입력 값을 우선 보존하면서 비어 있는 필드만 보강합니다."""
    merged = dict(base)
    for key, value in additions.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_missing(merged[key], value)
        elif key not in merged or merged.get(key) in (None, "", [], {}):
            merged[key] = value
    return merged


class PatentMetadataExtractionService:
    """특허 PDF 원문에서 메타데이터를 추출하고 평가 입력 형태로 정규화합니다."""

    def __init__(self) -> None:
        self._module: ModuleType | None = None

    def extract_from_pdf(self, pdf_path: str | Path) -> dict[str, Any]:
        path = self._resolve_pdf_path(pdf_path)
        module = self._get_module()

        raw_result = module.parse_patent(path)
        raw_meta = raw_result.get("meta") or {}
        title = _first_text(raw_meta.get("발명의_명칭"))
        abstract = _first_text(raw_meta.get("요약"))

        keywords: list[str] = []
        brief_summary: dict[str, Any] = {}
        if hasattr(module, "extract_keywords"):
            keywords = module.extract_keywords(title, abstract)
        if hasattr(module, "make_brief_summary"):
            brief_summary = module.make_brief_summary(title, abstract)

        normalized = self._normalize(raw_meta, raw_result, keywords, brief_summary)
        return {
            "source_pdf": str(path),
            "raw": raw_result,
            "keywords": keywords,
            "brief_summary": brief_summary,
            "normalized_patent": normalized,
        }

    def _get_module(self) -> ModuleType:
        if self._module is None:
            from document_processing import patent_pdf_extractor

            self._module = patent_pdf_extractor
        return self._module

    def _resolve_pdf_path(self, pdf_path: str | Path) -> Path:
        path = Path(pdf_path).expanduser()
        if path.exists():
            return path.resolve()

        candidate = SAMPLE_PATENT_DOCUMENT_DIR / path
        if candidate.exists():
            return candidate.resolve()

        raise FileNotFoundError(f"특허 PDF 파일을 찾을 수 없습니다: {pdf_path}")

    def _normalize(
        self,
        meta: dict[str, Any],
        raw_result: dict[str, Any],
        keywords: list[str],
        brief_summary: dict[str, Any],
    ) -> dict[str, Any]:
        claim_count = _safe_int(meta.get("청구항_수"))
        registration_number = _first_text(meta.get("등록번호"))
        application_number = _first_text(meta.get("출원번호"))
        title = _first_text(meta.get("발명의_명칭"))
        abstract = _first_text(meta.get("요약"))
        claims = raw_result.get("claims") if isinstance(raw_result.get("claims"), dict) else {}
        description = raw_result.get("description") if isinstance(raw_result.get("description"), dict) else {}
        claims_text = claims.get("claims_text") if isinstance(claims.get("claims_text"), dict) else {}
        deleted_claims = claims.get("deleted_claims") if isinstance(claims.get("deleted_claims"), list) else []

        normalized: dict[str, Any] = {
            "patent_id": registration_number or application_number,
            "meta": {
                "title": title,
                "registration_number": registration_number,
                "registration_date": _normalize_date(meta.get("등록일자")),
                "application_number": application_number,
                "application_date": _normalize_date(meta.get("출원일자")),
                "publication_number": _first_text(meta.get("공개번호")),
                "publication_date": _normalize_date(meta.get("공개일자")),
                "legal_status": "등록" if registration_number else "",
                "assignee": _split_people(meta.get("특허권자")),
                "inventors": _split_people(meta.get("발명자")),
                "agent": _split_people(meta.get("대리인")),
                "examiner": _first_text(meta.get("심사관")),
                "ipc": _normalize_classification_codes(meta.get("국제특허분류(IPC)")),
                "cpc": _normalize_classification_codes(meta.get("CPC특허분류")),
                "prior_art_cited": _split_values(meta.get("선행기술조사문헌")),
                "total_claims": claim_count,
                "deleted_claims": deleted_claims,
                "keywords": keywords,
            },
            "description_summary": _build_description_summary(abstract, description),
            "claims_text": claims_text,
            "specification": {
                "claims_raw_text": _first_text(claims.get("claims_raw_text")),
                "description_text": _first_text(description.get("description_text")),
                "technical_field": _first_text(description.get("technical_field")),
                "background_art": _first_text(description.get("background_art")),
                "problem_to_solve": _first_text(description.get("problem_to_solve")),
                "solution": _first_text(description.get("solution")),
                "advantageous_effects": _first_text(description.get("advantageous_effects")),
                "implementation": _first_text(description.get("implementation")),
            },
            "legal": {
                "registration_date": _normalize_date(meta.get("등록일자")),
                "notice_date": _normalize_date(meta.get("공고일자")),
                "examination_request_date": _normalize_date(meta.get("심사청구일자")),
            },
            "source_pdf": raw_result.get("filename"),
        }
        normalized["specification"] = {
            key: value
            for key, value in normalized["specification"].items()
            if value not in (None, "", [], {})
        }
        if brief_summary:
            normalized["brief_summary"] = brief_summary
        return normalized


class BusinessUseRagService:
    """RAG 인덱스를 이용해 특허 관련 제품 사업화 현황을 추정합니다."""

    def estimate(self, patent: dict[str, Any], query: str | None = None, top_k: int | None = None) -> dict[str, Any]:
        rag_engine = self._load_rag_engine()
        rag_query = query or self._build_query(patent)
        if not rag_query:
            raise ValueError("사업화 현황 추정을 위한 질의를 만들 수 없습니다.")

        kwargs: dict[str, Any] = {}
        if top_k is not None:
            kwargs["top_k"] = top_k
        result = rag_engine.ask(rag_query, **kwargs)
        return {
            "query": rag_query,
            "answer": result.get("answer"),
            "commercialization_status": result.get("commercialization_status"),
            "applied_business_service": result.get("applied_business_service") or "",
            "business_application_history": result.get("business_application_history") or "",
            "customers_partners": result.get("customers_partners") or "",
            "market_outlook": result.get("market_outlook") or "",
            "summary": result.get("summary") or "",
            "commercialization_signals": result.get("commercialization_signals"),
            "sources": result.get("sources") or [],
            "raw": result,
        }

    def _load_rag_engine(self) -> ModuleType:
        from business_rag import rag_engine

        return rag_engine

    def _build_query(self, patent: dict[str, Any]) -> str:
        meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
        title = _first_text(meta.get("title"), patent.get("title"))
        summary = _first_text(patent.get("description_summary"))
        if title and summary:
            return f"{title} 기술의 제품 사업화 현황, 적용 제품, 시장 활용 가능성은? 핵심 설명: {summary[:500]}"
        if title:
            return f"{title} 특허 기술의 제품 사업화 현황과 적용 제품은?"
        return ""


class EvidenceCollectionService:
    """PDF 메타데이터 추출과 RAG 사업화 추정을 평가 파이프라인 앞단에 통합합니다."""

    def __init__(self, options: EvidenceCollectionOptions | None = None) -> None:
        self.options = options or EvidenceCollectionOptions()
        self.metadata_extractor = PatentMetadataExtractionService()
        self.business_rag = BusinessUseRagService()

    def collect(self, data: dict[str, Any]) -> tuple[dict[str, Any], CollectedEvidence, list[EvaluationStepResult]]:
        patent = normalize_patent_input(data)
        evidence = CollectedEvidence()
        steps: list[EvaluationStepResult] = []

        if self.options.enable_pdf_metadata_extraction:
            self._collect_pdf_metadata(patent, evidence, steps)
        else:
            steps.append(EvaluationStepResult("pdf_metadata", "skipped", 0, "PDF 메타데이터 추출 단계 비활성화"))

        if self.options.enable_business_rag:
            self._collect_business_use(patent, evidence, steps)
        else:
            steps.append(EvaluationStepResult("business_rag", "skipped", 0, "사업화 현황 RAG 단계 비활성화"))

        return patent, evidence, steps

    def _collect_pdf_metadata(
        self,
        patent: dict[str, Any],
        evidence: CollectedEvidence,
        steps: list[EvaluationStepResult],
    ) -> None:
        start = time.time()
        pdf_path = patent.get("source_pdf") or patent.get("patent_pdf_path") or patent.get("patent_pdf")
        if not pdf_path:
            steps.append(EvaluationStepResult("pdf_metadata", "skipped", time.time() - start, "PDF 원문 경로 없음"))
            return

        try:
            result = self.metadata_extractor.extract_from_pdf(str(pdf_path))
            patent.update(_deep_merge_missing(patent, result["normalized_patent"]))
            evidence.patent_metadata = result
            steps.append(
                EvaluationStepResult(
                    "pdf_metadata",
                    "success",
                    time.time() - start,
                    "PDF 원문 메타데이터 추출 및 입력 보강 완료",
                )
            )
        except Exception as exc:
            message = f"PDF 메타데이터 추출 실패: {exc}"
            evidence.errors.append(message)
            steps.append(EvaluationStepResult("pdf_metadata", "error", time.time() - start, message, str(exc)))

    def _collect_business_use(
        self,
        patent: dict[str, Any],
        evidence: CollectedEvidence,
        steps: list[EvaluationStepResult],
    ) -> None:
        start = time.time()
        try:
            result = self.business_rag.estimate(
                patent,
                query=patent.get("business_query"),
                top_k=self.options.rag_top_k,
            )
            evidence.business_use = result
            evidence.sources.extend([source for source in result.get("sources", []) if isinstance(source, dict)])
            steps.append(
                EvaluationStepResult(
                    "business_rag",
                    "success",
                    time.time() - start,
                    "제품 사업화 현황 RAG 추정 완료",
                )
            )
        except Exception as exc:
            message = f"사업화 현황 RAG 추정 실패: {exc}"
            evidence.errors.append(message)
            steps.append(EvaluationStepResult("business_rag", "error", time.time() - start, message, str(exc)))
