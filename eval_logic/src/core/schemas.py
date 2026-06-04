"""특허 가치 평가 입력/출력 스키마입니다.

이 모듈은 현재 프로토타입 JSON 파일과 실제 AI 서버에서 호출할 서비스 로직
사이의 경계 역할을 합니다. 가져온 프로토타입 데이터에는 선택적인 수집
블록이 많기 때문에 입력 스키마는 의도적으로 유연하게 두었습니다. 반대로
출력 스키마는 보고서 생성, API 응답, 향후 의사결정 보조 에이전트가 같은
필드명을 안정적으로 사용할 수 있도록 더 엄격하게 정의합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Literal


ScoreDimension = Literal["기술성", "권리성", "시장성", "사업성", "unknown"]
ScoreMethod = Literal["auto", "auto_kosis", "llm", "error"]
StepStatus = Literal["success", "skipped", "fallback", "error"]
PATENT_INPUT_SCHEMA_VERSION = "patent-input/v1"
PATENT_VALUATION_OUTPUT_SCHEMA_VERSION = "patent-valuation-output/v1"


def _as_dict(value: Any) -> dict[str, Any]:
    """값이 딕셔너리이면 그대로 반환하고, 아니면 빈 딕셔너리를 반환합니다.

    프로토타입 입력은 여러 스크립트에서 만들어졌기 때문에 선택 섹션의 존재나
    타입이 항상 안정적이지 않습니다. 여기서 정규화하면 서비스 코드 곳곳에서
    잘못된 중첩 값을 반복해서 방어하지 않아도 됩니다.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """값이 리스트이면 그대로 반환하고, 아니면 빈 리스트를 반환합니다."""
    return value if isinstance(value, list) else []


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text == "-" else text


def _string_list(value: Any) -> list[str]:
    """문자열/리스트 혼용 입력을 비어 있지 않은 문자열 리스트로 통일합니다."""
    if isinstance(value, list):
        items = value
    elif value in (None, "", "-"):
        items = []
    else:
        text = str(value).replace("\n", ",").replace(";", ",")
        items = text.split(",")
    result: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _classification_list(value: Any) -> list[str]:
    """IPC/CPC 코드를 'G06Q10/04'처럼 비교 가능한 형태로 정규화합니다."""
    result: list[str] = []
    for item in _string_list(value):
        text = re.sub(r"\s*\(\d{4}(?:\.\d+)?\)\s*$", "", item).strip()
        text = re.sub(r"^([A-Z]\d{2}[A-Z])\s+", r"\1", text)
        if text and text not in result:
            result.append(text)
    return result


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, "", "-"):
            return None
        return int(str(value).replace(",", "").strip())
    except Exception:
        return None


def _normalize_claims(value: Any) -> dict[str, dict[str, Any]]:
    """청구항 입력을 {claim_n: {type, category, text, ...}} 구조로 통일합니다."""
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for idx, (key, raw) in enumerate(value.items(), 1):
        claim_key = str(key) if str(key).startswith("claim_") else f"claim_{idx}"
        if isinstance(raw, dict):
            text = _clean_text(raw.get("text"))
            if not text:
                continue
            item = {
                "type": _clean_text(raw.get("type")) or "미분류",
                "category": _clean_text(raw.get("category")) or "기타",
                "text": text,
            }
            depends_on = _int_or_none(raw.get("depends_on"))
            if depends_on is not None:
                item["depends_on"] = depends_on
        else:
            text = _clean_text(raw)
            if not text:
                continue
            item = {
                "type": "독립항" if not normalized else "종속항",
                "category": "기타",
                "text": text,
            }
        normalized[claim_key] = item
    return normalized


def normalize_patent_input(data: dict[str, Any]) -> dict[str, Any]:
    """모든 API/서비스가 공유하는 표준 특허 입력 JSON으로 정규화합니다.

    허용 입력:
    - 표준 특허 JSON
    - {"patent": {...}}
    - {"patent_data": {...}}
    - PDF 추출 결과의 {"normalized_patent": {...}}

    반환 구조의 핵심 필드는 ``patent_id``, ``meta``, ``claims_text``,
    ``description_summary``, ``specification``, ``legal``입니다.
    """
    if not isinstance(data, dict):
        return {}
    if isinstance(data.get("patent"), dict):
        data = data["patent"]
    elif isinstance(data.get("patent_data"), dict):
        data = data["patent_data"]
    elif isinstance(data.get("normalized_patent"), dict):
        data = data["normalized_patent"]

    raw = dict(data)
    meta = _as_dict(raw.get("meta"))
    legal = _as_dict(raw.get("legal"))
    specification = _as_dict(raw.get("specification"))
    claims_text = _normalize_claims(raw.get("claims_text"))

    patent_id = _clean_text(raw.get("patent_id") or meta.get("registration_number") or meta.get("application_number"))
    title = _clean_text(meta.get("title") or raw.get("title"))
    description_summary = _clean_text(raw.get("description_summary"))
    if not description_summary:
        summary_parts = [
            specification.get("technical_field"),
            specification.get("problem_to_solve"),
            specification.get("solution"),
            specification.get("advantageous_effects"),
        ]
        description_summary = "\n".join(_clean_text(part) for part in summary_parts if _clean_text(part))

    total_claims = _int_or_none(meta.get("total_claims"))
    if total_claims is None and claims_text:
        total_claims = len(claims_text) + len(_string_list(meta.get("deleted_claims")))

    normalized_meta = dict(meta)
    normalized_meta.update(
        {
            "title": title,
            "registration_number": _clean_text(meta.get("registration_number") or patent_id),
            "application_number": _clean_text(meta.get("application_number")),
            "application_date": _clean_text(meta.get("application_date")),
            "registration_date": _clean_text(meta.get("registration_date") or legal.get("registration_date")),
            "publication_number": _clean_text(meta.get("publication_number")),
            "publication_date": _clean_text(meta.get("publication_date")),
            "legal_status": _clean_text(meta.get("legal_status") or legal.get("legal_status")),
            "assignee": _string_list(meta.get("assignee")),
            "inventors": _string_list(meta.get("inventors")),
            "agent": _string_list(meta.get("agent")),
            "ipc": _classification_list(meta.get("ipc")),
            "cpc": _classification_list(meta.get("cpc")),
            "prior_art_cited": _string_list(meta.get("prior_art_cited")),
            "deleted_claims": [
                item for item in (_int_or_none(value) for value in _string_list(meta.get("deleted_claims"))) if item is not None
            ],
            "keywords": _string_list(meta.get("keywords")),
        }
    )
    if total_claims is not None:
        normalized_meta["total_claims"] = total_claims

    normalized = dict(raw)
    normalized["schema_version"] = PATENT_INPUT_SCHEMA_VERSION
    normalized["patent_id"] = patent_id
    normalized["meta"] = {key: value for key, value in normalized_meta.items() if value not in (None, "", [], {})}
    normalized["claims_text"] = claims_text
    normalized["description_summary"] = description_summary
    normalized["specification"] = {
        key: value for key, value in specification.items() if value not in (None, "", [], {})
    }
    normalized["legal"] = {key: value for key, value in legal.items() if value not in (None, "", [], {})}
    if raw.get("source_pdf") or raw.get("patent_pdf_path") or raw.get("patent_pdf"):
        normalized["source_pdf"] = _clean_text(raw.get("source_pdf") or raw.get("patent_pdf_path") or raw.get("patent_pdf"))
    return normalized


@dataclass(slots=True)
class PatentEvaluationInput:
    """특허 1건의 가치 평가 요청에 대한 정규화된 입력입니다.

    서비스 레벨 필수 필드:
    - ``patent_id``: 추적과 출력 파일명에 사용할 고유 특허 식별자입니다.
    - ``meta.title``: 사람이 읽을 수 있는 발명 명칭입니다.

    중요한 선택 블록:
    - ``description_summary``와 ``claims_text``는 LLM/청구항 기반 평가에 사용됩니다.
    - ``market_data``는 KOSIS 산업 성장률을 결정하는 데 도움을 줍니다.
    - ``kipris_data``는 피인용, 패밀리, 심판 이력 신호를 제공할 수 있습니다.

    ``raw``는 기존 점수 계산 함수들이 원래 프로토타입 구조를 계속 사용할 수
    있도록 보존합니다. 내부 구현은 점진적으로 타입 기반 구조로 이동합니다.
    """

    patent_id: str
    title: str
    meta: dict[str, Any] = field(default_factory=dict)
    claims_text: dict[str, Any] = field(default_factory=dict)
    description_summary: str = ""
    market_data: dict[str, Any] = field(default_factory=dict)
    kipris_data: dict[str, Any] = field(default_factory=dict)
    specification: dict[str, Any] = field(default_factory=dict)
    legal: dict[str, Any] = field(default_factory=dict)
    source_pdf: str | None = None
    business_query: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatentEvaluationInput":
        """프로토타입 특허 JSON 딕셔너리에서 정규화된 입력 객체를 만듭니다."""
        data = normalize_patent_input(data)
        meta = _as_dict(data.get("meta"))
        return cls(
            patent_id=str(data.get("patent_id") or meta.get("registration_number") or ""),
            title=str(meta.get("title") or data.get("title") or ""),
            meta=meta,
            claims_text=_as_dict(data.get("claims_text")),
            description_summary=str(data.get("description_summary") or ""),
            market_data=_as_dict(data.get("market_data")),
            kipris_data=_as_dict(data.get("kipris_data")),
            specification=_as_dict(data.get("specification")),
            legal=_as_dict(data.get("legal")),
            source_pdf=(
                str(data.get("source_pdf") or data.get("patent_pdf_path") or data.get("patent_pdf") or "")
                or None
            ),
            business_query=str(data.get("business_query") or "") or None,
            raw=dict(data),
        )

    def validate(self) -> list[str]:
        """즉시 예외를 발생시키지 않고 검증 오류 목록을 반환합니다.

        서비스는 이 결과를 보고 즉시 실패할지, 일부 평가만 계속할지 결정할 수
        있습니다. 현재는 제목/식별자 누락을 요청 오류로 보고, 청구항이나 시장
        필드 누락은 관련 단계의 fallback으로 처리합니다.
        """
        errors: list[str] = []
        if not self.patent_id:
            errors.append("patent_id 또는 meta.registration_number가 필요합니다.")
        if not self.title:
            errors.append("meta.title 또는 title이 필요합니다.")
        return errors

    def to_legacy_dict(self) -> dict[str, Any]:
        """기존 프로토타입 점수 계산 함수와 호환되는 딕셔너리를 반환합니다."""
        data = dict(self.raw)
        data.setdefault("patent_id", self.patent_id)
        data.setdefault("meta", self.meta)
        data.setdefault("claims_text", self.claims_text)
        data.setdefault("description_summary", self.description_summary)
        if self.market_data:
            data.setdefault("market_data", self.market_data)
        if self.kipris_data:
            data.setdefault("kipris_data", self.kipris_data)
        if self.specification:
            data.setdefault("specification", self.specification)
        if self.legal:
            data.setdefault("legal", self.legal)
        if self.source_pdf:
            data.setdefault("source_pdf", self.source_pdf)
        if self.business_query:
            data.setdefault("business_query", self.business_query)
        return data


@dataclass(slots=True)
class CollectedEvidence:
    """평가 전후에 수집한 보조 자료의 표준 중간 모델입니다.

    PDF 원문에서 추출한 메타데이터, 제품 사업화 현황 RAG 추정 결과, 단계별
    오류를 한 곳에 모읍니다. 이 객체는 향후 FastAPI 응답, 보고서 생성기,
    에이전트 워크플로우가 같은 구조를 공유하도록 하는 중간 산출물입니다.
    """

    patent_metadata: dict[str, Any] | None = None
    business_use: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "patent_metadata": self.patent_metadata,
            "business_use": self.business_use,
            "sources": self.sources,
            "errors": self.errors,
        }
        return {key: value for key, value in data.items() if value not in (None, [], {})}


@dataclass(slots=True)
class ScoreItem:
    """1~5점 척도의 평가 항목 1개를 표현합니다."""

    item: str
    dim: str
    score: int
    method: str
    basis: str = ""
    reason: str = ""
    summary: str = ""
    confidence: str = ""
    kipris_evidence: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    strategy: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScoreItem":
        """auto/LLM 원본 점수 딕셔너리를 하나의 서비스 스키마로 정규화합니다."""
        try:
            score = int(data.get("score", 3))
        except Exception:
            score = 3
        return cls(
            item=str(data.get("item") or ""),
            dim=str(data.get("dim") or "unknown"),
            score=max(1, min(5, score)),
            method=str(data.get("method") or "unknown"),
            basis=str(data.get("basis") or ""),
            reason=str(data.get("reason") or ""),
            summary=str(data.get("summary") or ""),
            confidence=str(data.get("confidence") or ""),
            kipris_evidence=str(data.get("kipris_evidence") or ""),
            sources=[s for s in _as_list(data.get("sources")) if isinstance(s, dict)],
            strategy=str(data.get("strategy")) if data.get("strategy") else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """보고서 생성기가 소비하는 JSON 구조로 직렬화합니다."""
        data: dict[str, Any] = {
            "item": self.item,
            "dim": self.dim,
            "score": self.score,
            "method": self.method,
        }
        if self.basis:
            data["basis"] = self.basis
        if self.reason:
            data["reason"] = self.reason
        if self.summary:
            data["summary"] = self.summary
        if self.confidence:
            data["confidence"] = self.confidence
        if self.kipris_evidence:
            data["kipris_evidence"] = self.kipris_evidence
        if self.sources:
            data["sources"] = self.sources
        if self.strategy:
            data["strategy"] = self.strategy
        return data


@dataclass(slots=True)
class EvaluationStepResult:
    """파이프라인 단계 1개의 실행 메타데이터입니다."""

    name: str
    status: StepStatus
    elapsed_seconds: float
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }
        if self.message:
            data["message"] = self.message
        if self.error:
            data["error"] = self.error
        return data


@dataclass(slots=True)
class PatentEvaluationOutput:
    """특허 가치 평가 실행 1건의 표준 출력입니다."""

    patent_id: str
    title: str
    meta: dict[str, Any] = field(default_factory=dict)
    legal: dict[str, Any] = field(default_factory=dict)
    auto_scores: list[ScoreItem] = field(default_factory=list)
    llm_scores: list[ScoreItem] = field(default_factory=list)
    market_growth: dict[str, Any] | None = None
    llm_sources: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    steps: list[EvaluationStepResult] = field(default_factory=list)
    input_file: str | None = None
    kipris_competition: dict[str, Any] = field(default_factory=dict)

    def all_scores(self) -> list[ScoreItem]:
        """보고서에 사용할 순서로 auto 점수와 LLM 점수를 반환합니다."""
        return [*self.auto_scores, *self.llm_scores]

    def to_dict(self) -> dict[str, Any]:
        """기존 보고서 생성기와 호환되는 출력 JSON 구조로 직렬화합니다."""
        result: dict[str, Any] = {
            "schema_version": PATENT_VALUATION_OUTPUT_SCHEMA_VERSION,
            "patent_id": self.patent_id,
            "title": self.title,
            "meta": self.meta,
            "legal": self.legal,
            "auto_scores": [score.to_dict() for score in self.auto_scores],
            "llm_scores": [score.to_dict() for score in self.llm_scores],
            "llm_sources": self.llm_sources,
            "evidence": self.evidence,
            "market_growth": self.market_growth,
            "summary": {
                **self.summary,
                "steps": [step.to_dict() for step in self.steps],
            },
        }
        if self.kipris_competition:
            result["kipris_competition"] = self.kipris_competition
        if self.input_file:
            result["input_file"] = self.input_file
        return result