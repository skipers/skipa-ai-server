"""특허 가치평가 보고서 신뢰도 검증 서비스입니다.

이 모듈은 생성된 보고서를 외부 LLM 호출 없이 결정론적으로 점검합니다.
운영 게이트에서 바로 사용할 수 있도록 근거 커버리지, 수치 무결성,
고점 항목의 근거 충분성, 출처 품질, 사람 검토 필요 여부를 산출합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OFFICIAL_SOURCE_KEYWORDS = (
    "kipris",
    "kosis",
    "dart",
    "go.kr",
    "or.kr",
    "ac.kr",
    "ieee",
    "springer",
    "ncbi",
    "kci",
    "arxiv",
)


@dataclass(slots=True)
class VerificationIssue:
    """보고서 검증 중 발견된 문제 1건입니다."""

    code: str
    severity: str
    message: str
    location: str
    item: str = ""
    dim: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }
        if self.item:
            data["item"] = self.item
        if self.dim:
            data["dim"] = self.dim
        return data


class ReportVerificationService:
    """보고서와 원 평가 결과를 대조하여 신뢰도 요약을 생성합니다."""

    def verify(
        self,
        report: dict[str, Any],
        valuation: dict[str, Any],
        similar_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scores = self._all_scores(valuation)
        report_items = self._report_score_items(report)
        issues: list[VerificationIssue] = []

        metrics = {
            "score_item_count": len(scores),
            "report_score_item_count": len(report_items),
            "source_backed_item_count": 0,
            "low_confidence_item_count": 0,
            "high_score_without_source_count": 0,
            "unsupported_claim_count": 0,
            "contradiction_count": 0,
            "numeric_mismatch_count": 0,
            "official_source_count": 0,
            "total_source_count": 0,
            "similar_analysis_available": bool(similar_analysis),
        }

        if not report:
            issues.append(VerificationIssue(
                "missing_report",
                "critical",
                "생성된 보고서가 없습니다.",
                "report",
            ))
            return self._build_result(metrics, issues)

        if not scores:
            issues.append(VerificationIssue(
                "missing_scores",
                "critical",
                "평가 점수가 생성되지 않아 보고서 신뢰도를 판단할 수 없습니다.",
                "valuation",
            ))

        self._check_item_evidence(scores, metrics, issues)
        self._check_numeric_integrity(report, scores, metrics, issues)
        self._check_reference_quality(report, valuation, similar_analysis, metrics, issues)
        self._check_section_availability(report, valuation, similar_analysis, issues)

        return self._build_result(metrics, issues)

    def _all_scores(self, valuation: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            item
            for item in (valuation.get("auto_scores") or []) + (valuation.get("llm_scores") or [])
            if isinstance(item, dict)
        ]

    def _report_score_items(self, report: dict[str, Any]) -> list[dict[str, Any]]:
        evaluation = report.get("evaluation") or {}
        if isinstance(evaluation.get("dimensions"), list):
            items: list[dict[str, Any]] = []
            for dim_data in evaluation.get("dimensions") or []:
                if isinstance(dim_data, dict):
                    items.extend(item for item in dim_data.get("items") or [] if isinstance(item, dict))
            return items

        section = report.get("section_2_detailed_scores") or {}
        dimensions = section.get("dimensions") or {}
        items = []
        if not isinstance(dimensions, dict):
            return items
        for dim_data in dimensions.values():
            if isinstance(dim_data, dict):
                items.extend(item for item in dim_data.get("items") or [] if isinstance(item, dict))
        return items

    def _check_item_evidence(
        self,
        scores: list[dict[str, Any]],
        metrics: dict[str, Any],
        issues: list[VerificationIssue],
    ) -> None:
        for idx, score in enumerate(scores):
            item = str(score.get("item") or "")
            dim = str(score.get("dim") or "")
            method = str(score.get("method") or "")
            strategy = str(score.get("strategy") or "")
            score_value = self._as_number(score.get("score"))
            sources = [src for src in score.get("sources") or [] if isinstance(src, dict)]
            basis = str(score.get("reason") or score.get("basis") or score.get("summary") or "").strip()
            confidence = str(score.get("confidence") or "").strip()
            location = f"valuation.scores[{idx}]"

            if sources:
                metrics["source_backed_item_count"] += 1
            if confidence == "낮음":
                metrics["low_confidence_item_count"] += 1

            if method == "llm" and strategy != "claims_only" and not sources:
                metrics["unsupported_claim_count"] += 1
                severity = "high" if score_value is not None and score_value >= 4 else "medium"
                issues.append(VerificationIssue(
                    "llm_item_without_source",
                    severity,
                    (
                        "웹/혼합 전략 LLM 평가 항목에 인용 출처가 없습니다."
                        if severity == "high"
                        else "웹/혼합 전략 LLM 평가 항목에 인용 출처가 없어 보수 검토가 필요합니다."
                    ),
                    location,
                    item=item,
                    dim=dim,
                ))

            if score_value is not None and score_value >= 4 and not sources and method != "auto":
                metrics["high_score_without_source_count"] += 1
                issues.append(VerificationIssue(
                    "high_score_without_source",
                    "high",
                    "4점 이상 고평가 항목에 외부 또는 명시 근거 출처가 없습니다.",
                    location,
                    item=item,
                    dim=dim,
                ))

            if not basis:
                metrics["unsupported_claim_count"] += 1
                issues.append(VerificationIssue(
                    "missing_judgment_basis",
                    "medium",
                    "평가 판단 근거 텍스트가 비어 있습니다.",
                    location,
                    item=item,
                    dim=dim,
                ))

    def _check_numeric_integrity(
        self,
        report: dict[str, Any],
        scores: list[dict[str, Any]],
        metrics: dict[str, Any],
        issues: list[VerificationIssue],
    ) -> None:
        expected = self._dimension_averages(scores)
        dimensions = self._report_dimensions_by_name(report)
        if not dimensions:
            issues.append(VerificationIssue(
                "missing_score_dimensions",
                "critical",
                "보고서 상세 점수 섹션의 차원별 점수 구조가 없습니다.",
                "report.evaluation.dimensions",
            ))
            metrics["numeric_mismatch_count"] += 1
            return

        for dim, expected_avg in expected.items():
            report_avg = self._as_number((dimensions.get(dim) or {}).get("average_score"))
            if report_avg is None or abs(report_avg - expected_avg) > 0.01:
                metrics["numeric_mismatch_count"] += 1
                issues.append(VerificationIssue(
                    "dimension_average_mismatch",
                    "high",
                    f"{dim} 평균 점수가 원 평가 결과와 일치하지 않습니다. expected={expected_avg}, report={report_avg}",
                    f"report.evaluation.dimensions.{dim}.average_score",
                    dim=dim,
                ))

        summary_dimensions = self._summary_dimensions_by_name(report)
        if summary_dimensions:
            for dim, expected_avg in expected.items():
                report_avg = self._as_number((summary_dimensions.get(dim) or {}).get("average_score"))
                if report_avg is not None and abs(report_avg - expected_avg) > 0.01:
                    metrics["numeric_mismatch_count"] += 1
                    issues.append(VerificationIssue(
                        "summary_average_mismatch",
                        "medium",
                        f"{dim} 요약 평균 점수가 상세 점수와 일치하지 않습니다.",
                        f"report.summary.dimension_cards.{dim}.average_score",
                        dim=dim,
                    ))

    def _check_reference_quality(
        self,
        report: dict[str, Any],
        valuation: dict[str, Any],
        similar_analysis: dict[str, Any] | None,
        metrics: dict[str, Any],
        issues: list[VerificationIssue],
    ) -> None:
        sources = self._collect_sources(report, valuation, similar_analysis)
        metrics["total_source_count"] = len(sources)
        metrics["official_source_count"] = sum(1 for src in sources if self._is_official_source(src))

        if not sources:
            issues.append(VerificationIssue(
                "missing_references",
                "high",
                "보고서 전체에 검증 가능한 참고 출처가 없습니다.",
                "report.section_6_references",
            ))
            return

        source_quality_ratio = metrics["official_source_count"] / max(1, metrics["total_source_count"])
        if source_quality_ratio < 0.25:
            issues.append(VerificationIssue(
                "weak_source_quality",
                "medium",
                "공식/전문 출처 비율이 낮아 외부 근거 품질 검토가 필요합니다.",
                "report.section_6_references",
            ))

    def _check_section_availability(
        self,
        report: dict[str, Any],
        valuation: dict[str, Any],
        similar_analysis: dict[str, Any] | None,
        issues: list[VerificationIssue],
    ) -> None:
        evidence = valuation.get("evidence") or {}
        business_use = evidence.get("business_use") if isinstance(evidence, dict) else None
        project_section = report.get("section_3_project_utilization") or {}
        if not business_use and not project_section.get("available"):
            issues.append(VerificationIssue(
                "missing_business_evidence",
                "medium",
                "사내 사업화/RAG 근거가 없어 사업성 판단은 고객 확인이 필요합니다.",
                "report.section_3_project_utilization",
            ))

        if similar_analysis is None:
            issues.append(VerificationIssue(
                "missing_similar_analysis",
                "medium",
                "유사 특허 분석 결과가 없어 경쟁/차별화 판단 신뢰도가 낮습니다.",
                "report.section_4_similar_patents",
            ))

    def _build_result(
        self,
        metrics: dict[str, Any],
        issues: list[VerificationIssue],
    ) -> dict[str, Any]:
        issue_dicts = [issue.to_dict() for issue in issues]
        coverage = metrics["source_backed_item_count"] / max(1, metrics["score_item_count"])
        numeric_integrity = metrics["numeric_mismatch_count"] == 0
        source_quality = metrics["official_source_count"] / max(1, metrics["total_source_count"])

        penalty = 0.0
        for issue in issues:
            penalty += {
                "critical": 0.25,
                "high": 0.12,
                "medium": 0.05,
                "low": 0.02,
            }.get(issue.severity, 0.03)

        reliability = 0.35 + (coverage * 0.3) + (source_quality * 0.2) + (0.15 if numeric_integrity else 0.0)
        reliability = max(0.0, min(1.0, reliability - penalty))
        risk_level = self._risk_level(reliability, issues)
        human_review_required = risk_level in {"caution", "high_risk"} or any(
            issue.severity in {"critical", "high"} for issue in issues
        )

        return {
            "schema_version": "report-verification/v1",
            "overall_reliability_score": round(reliability, 2),
            "reliability_grade": self._grade(reliability),
            "risk_level": risk_level,
            "human_review_required": human_review_required,
            "evidence_coverage": round(coverage, 2),
            "source_quality_score": round(source_quality, 2),
            "numeric_integrity": "pass" if numeric_integrity else "fail",
            "metrics": {
                **metrics,
                "issue_count": len(issues),
                "critical_issue_count": sum(1 for issue in issues if issue.severity == "critical"),
                "high_issue_count": sum(1 for issue in issues if issue.severity == "high"),
            },
            "issues": issue_dicts,
            "summary": self._summary(reliability, risk_level, human_review_required, issue_dicts),
        }

    def _dimension_averages(self, scores: list[dict[str, Any]]) -> dict[str, float]:
        by_dim: dict[str, list[float]] = {}
        for score in scores:
            value = self._as_number(score.get("score"))
            if value is None:
                continue
            by_dim.setdefault(str(score.get("dim") or "unknown"), []).append(value)
        return {dim: round(sum(values) / len(values), 2) for dim, values in by_dim.items() if values}

    def _collect_sources(
        self,
        report: dict[str, Any],
        valuation: dict[str, Any],
        similar_analysis: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        for score in self._all_scores(valuation):
            sources.extend(src for src in score.get("sources") or [] if isinstance(src, dict))

        refs = report.get("references") or {}
        grouped_sources = refs.get("sources") if isinstance(refs, dict) else None
        if isinstance(grouped_sources, dict):
            for group in grouped_sources.values():
                sources.extend(src for src in group or [] if isinstance(src, dict))
        else:
            section6 = report.get("section_6_references") or {}
            for key in ("tech_market_sources", "papers_and_reports", "project_rag_sources", "all_sources_deduplicated"):
                sources.extend(src for src in section6.get(key) or [] if isinstance(src, dict))

        if similar_analysis:
            for patent in similar_analysis.get("similar_patents") or []:
                if isinstance(patent, dict):
                    sources.append({"source": "KIPRIS", **patent})
        return self._dedup_sources(sources)

    def _report_dimensions_by_name(self, report: dict[str, Any]) -> dict[str, dict[str, Any]]:
        evaluation = report.get("evaluation") or {}
        dimensions = evaluation.get("dimensions") if isinstance(evaluation, dict) else None
        if isinstance(dimensions, list):
            return {
                str(item.get("key") or item.get("label") or ""): item
                for item in dimensions
                if isinstance(item, dict)
            }

        legacy = ((report.get("section_2_detailed_scores") or {}).get("dimensions") or {})
        return legacy if isinstance(legacy, dict) else {}

    def _summary_dimensions_by_name(self, report: dict[str, Any]) -> dict[str, dict[str, Any]]:
        summary = report.get("summary") or {}
        cards = summary.get("dimension_cards") if isinstance(summary, dict) else None
        if isinstance(cards, list):
            return {
                str(item.get("key") or item.get("label") or ""): item
                for item in cards
                if isinstance(item, dict)
            }

        legacy = ((report.get("section_1_summary") or {}).get("dimension_scores") or {})
        return legacy if isinstance(legacy, dict) else {}

    def _dedup_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for source in sources:
            key = str(
                source.get("url")
                or source.get("patent_no")
                or source.get("title")
                or source.get("source")
                or source
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(source)
        return result

    def _is_official_source(self, source: dict[str, Any]) -> bool:
        text = " ".join(
            str(source.get(key) or "")
            for key in ("url", "source", "title", "publisher", "patent_no")
        ).lower()
        return any(keyword in text for keyword in OFFICIAL_SOURCE_KEYWORDS)

    def _as_number(self, value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except Exception:
            return None

    def _grade(self, reliability: float) -> str:
        if reliability >= 0.9:
            return "A"
        if reliability >= 0.75:
            return "B"
        if reliability >= 0.6:
            return "C"
        return "D"

    def _risk_level(self, reliability: float, issues: list[VerificationIssue]) -> str:
        if any(issue.severity == "critical" for issue in issues) or reliability < 0.6:
            return "high_risk"
        if any(issue.severity == "high" for issue in issues) or reliability < 0.75:
            return "caution"
        return "acceptable"

    def _summary(
        self,
        reliability: float,
        risk_level: str,
        human_review_required: bool,
        issues: list[dict[str, Any]],
    ) -> str:
        if not issues and risk_level == "acceptable":
            return f"자동 검증 기준상 신뢰도 {reliability:.2f}로 주요 구조와 근거가 확인되었습니다."
        review = "사람 검토가 필요합니다" if human_review_required else "자동 납품 가능 범위입니다"
        return (
            f"자동 검증 신뢰도는 {reliability:.2f}이며 위험 등급은 {risk_level}입니다. "
            f"주요 이슈 {len(issues)}건이 발견되어 {review}."
        )
