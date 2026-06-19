"""
183개 patents/{id}/reports/{id}/report.json 전체 신뢰도 배치 검증 스크립트.
report.json 의 evaluation.dimensions.items 에서 pseudo-valuation 을 재구성해
ReportVerificationService.verify() 를 호출하고 결과를 집계합니다.
"""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict

# eval_logic 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "eval_logic"))
from src.services.report_verification_service import ReportVerificationService

PATENTS_DIR = Path(__file__).parent / "patents"
VERIFIER = ReportVerificationService()


def reconstruct_valuation(report: dict) -> dict:
    """report.evaluation.dimensions.items → auto_scores / llm_scores 로 변환"""
    auto_scores, llm_scores = [], []
    evaluation = report.get("evaluation") or {}
    for dim in evaluation.get("dimensions") or []:
        dim_key = dim.get("key") or dim.get("label") or ""
        for item in dim.get("items") or []:
            entry = {
                "item": item.get("name", ""),
                "dim": dim_key,
                "score": item.get("score"),
                "method": item.get("method", ""),
                "strategy": item.get("strategy", ""),
                "confidence": item.get("confidence", ""),
                "sources": item.get("sources") or [],
                "basis": item.get("judgment_basis", ""),
                "summary": item.get("judgment_summary", ""),
            }
            if item.get("method") == "auto" or str(item.get("method", "")).startswith("auto"):
                auto_scores.append(entry)
            else:
                llm_scores.append(entry)
    return {"auto_scores": auto_scores, "llm_scores": llm_scores}


def count_truncated_summaries(report: dict) -> int:
    """'입니다.' 로 잘린 판단요지 수 집계"""
    count = 0
    for dim in (report.get("evaluation") or {}).get("dimensions") or []:
        for item in dim.get("items") or []:
            summary = item.get("judgment_summary") or ""
            if summary.endswith("입니다.") and len(summary) < 60:
                count += 1
    return count


def collect_all_reports() -> list[Path]:
    paths = []
    for p in sorted(PATENTS_DIR.rglob("report.json")):
        paths.append(p)
    return paths


def run_batch():
    report_paths = collect_all_reports()
    print(f"대상 보고서: {len(report_paths)}개\n")

    all_results = []
    issue_code_counter: Counter = Counter()
    severity_counter: Counter = Counter()
    reliability_grades: Counter = Counter()
    risk_levels: Counter = Counter()
    method_counter: Counter = Counter()
    confidence_counter: Counter = Counter()
    score_distribution: list[float] = []
    truncated_total = 0
    errors = []

    for path in report_paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            report = raw.get("report", raw)
            valuation = reconstruct_valuation(report)

            # similar_patents → similar_analysis 형식으로 변환
            similar_raw = report.get("similar_patents") or {}
            similar_analysis = None
            if similar_raw.get("available"):
                similar_analysis = {
                    "similar_patents": similar_raw.get("patents") or []
                }

            result = VERIFIER.verify(report, valuation, similar_analysis)

            patent_id = report.get("patent", {}).get("registration_number") or path.parts[-3]
            overall_score = (report.get("summary") or {}).get("overall_score_out_of_100", 0)
            truncated = count_truncated_summaries(report)
            truncated_total += truncated

            # 항목별 method / confidence 집계
            for scores in [valuation["auto_scores"], valuation["llm_scores"]]:
                for s in scores:
                    method_counter[s["method"]] += 1
                    confidence_counter[s["confidence"]] += 1

            score_distribution.append(overall_score)
            reliability_grades[result["reliability_grade"]] += 1
            risk_levels[result["risk_level"]] += 1

            for issue in result.get("issues") or []:
                issue_code_counter[issue["code"]] += 1
                severity_counter[issue["severity"]] += 1

            all_results.append({
                "patent_id": patent_id,
                "overall_score": overall_score,
                "overall_grade": (report.get("summary") or {}).get("overall_grade", ""),
                "reliability_score": result["overall_reliability_score"],
                "reliability_grade": result["reliability_grade"],
                "risk_level": result["risk_level"],
                "human_review_required": result["human_review_required"],
                "evidence_coverage": result["evidence_coverage"],
                "source_quality_score": result["source_quality_score"],
                "numeric_integrity": result["numeric_integrity"],
                "issue_count": result["metrics"]["issue_count"],
                "critical_count": result["metrics"]["critical_issue_count"],
                "high_count": result["metrics"]["high_issue_count"],
                "truncated_summaries": truncated,
                "score_item_count": result["metrics"]["score_item_count"],
                "low_confidence_count": result["metrics"]["low_confidence_item_count"],
                "path": str(path),
            })

        except Exception as e:
            errors.append((str(path), str(e)))

    # ── 요약 출력 ─────────────────────────────────────────────────────────────
    n = len(all_results)
    print("=" * 65)
    print(f"  전체 보고서 분석 결과  (성공: {n}개 / 오류: {len(errors)}개)")
    print("=" * 65)

    # 보고서 점수 분포
    if score_distribution:
        avg_score = sum(score_distribution) / len(score_distribution)
        min_score = min(score_distribution)
        max_score = max(score_distribution)
        print(f"\n[특허 평가 점수 (overall_score_out_of_100)]")
        print(f"  평균: {avg_score:.1f}  /  최소: {min_score}  /  최대: {max_score}")
        grade_dist: Counter = Counter(r["overall_grade"] for r in all_results)
        print(f"  등급 분포: {dict(sorted(grade_dist.items()))}")

    # 신뢰도
    rel_scores = [r["reliability_score"] for r in all_results]
    if rel_scores:
        avg_rel = sum(rel_scores) / len(rel_scores)
        print(f"\n[신뢰도 (reliability_score, 0~1)]")
        print(f"  평균: {avg_rel:.3f}  /  최소: {min(rel_scores):.3f}  /  최대: {max(rel_scores):.3f}")
        print(f"  등급 분포: {dict(sorted(reliability_grades.items()))}")

    print(f"\n[위험 등급 (risk_level)]")
    for lvl, cnt in sorted(risk_levels.items(), key=lambda x: -x[1]):
        pct = cnt / n * 100
        print(f"  {lvl:<20} {cnt:>4}건  ({pct:.1f}%)")

    human_review_cnt = sum(1 for r in all_results if r["human_review_required"])
    print(f"\n[사람 검토 필요]  {human_review_cnt}건 / {n}건  ({human_review_cnt/n*100:.1f}%)")

    print(f"\n[수치 무결성 (numeric_integrity)]")
    ni_pass = sum(1 for r in all_results if r["numeric_integrity"] == "pass")
    print(f"  pass: {ni_pass}건  /  fail: {n - ni_pass}건")

    print(f"\n[근거 커버리지 (evidence_coverage, 소스 있는 항목/전체)]")
    cov = [r["evidence_coverage"] for r in all_results]
    print(f"  평균: {sum(cov)/len(cov):.3f}  /  0.0인 보고서: {cov.count(0.0)}건")

    print(f"\n[출처 품질 (source_quality_score, 공식 출처 비율)]")
    sq = [r["source_quality_score"] for r in all_results]
    print(f"  평균: {sum(sq)/len(sq):.3f}")

    print(f"\n[잘린 요약 (judgment_summary 가 '입니다.'로 끝나며 60자 미만)]")
    print(f"  총 {truncated_total}건  /  영향 보고서: {sum(1 for r in all_results if r['truncated_summaries'] > 0)}개")

    print(f"\n[평가 방법 분포 (method)]")
    for m, cnt in method_counter.most_common():
        print(f"  {m or '(없음)':<20} {cnt:>5}건")

    print(f"\n[신뢰도 분포 (confidence)]")
    for c, cnt in confidence_counter.most_common():
        print(f"  {c or '(없음)':<10} {cnt:>5}건")

    print(f"\n[이슈 심각도 분포]")
    total_issues = sum(severity_counter.values())
    for sev in ["critical", "high", "medium", "low"]:
        cnt = severity_counter.get(sev, 0)
        print(f"  {sev:<10} {cnt:>6}건  (보고서당 평균 {cnt/n:.1f}건)")

    print(f"\n[이슈 코드 Top 15]")
    for code, cnt in issue_code_counter.most_common(15):
        print(f"  {code:<45} {cnt:>5}건")

    # 최하위 신뢰도 보고서 10건
    worst = sorted(all_results, key=lambda x: x["reliability_score"])[:10]
    print(f"\n[신뢰도 하위 10건]")
    print(f"  {'특허번호':<20} {'신뢰도':>6}  {'등급':>4}  {'위험':>12}  {'이슈':>5}  {'잘린요약':>6}")
    for r in worst:
        print(f"  {r['patent_id']:<20} {r['reliability_score']:>6.3f}  {r['reliability_grade']:>4}  {r['risk_level']:>12}  {r['issue_count']:>5}  {r['truncated_summaries']:>6}")

    # 오류
    if errors:
        print(f"\n[처리 오류 {len(errors)}건]")
        for path, err in errors[:10]:
            print(f"  {path}: {err}")

    print("\n" + "=" * 65)

    # JSON 저장
    out_path = Path(__file__).parent / "batch_verify_results.json"
    out_path.write_text(
        json.dumps({"summary": {
            "total": n,
            "errors": len(errors),
            "avg_reliability": round(sum(rel_scores)/len(rel_scores), 3) if rel_scores else 0,
            "avg_overall_score": round(sum(score_distribution)/len(score_distribution), 1) if score_distribution else 0,
            "risk_levels": dict(risk_levels),
            "reliability_grades": dict(reliability_grades),
            "human_review_required": human_review_cnt,
            "numeric_integrity_fail": n - ni_pass,
            "truncated_summary_total": truncated_total,
            "issue_code_top15": dict(issue_code_counter.most_common(15)),
        }, "reports": all_results}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"상세 결과 저장: {out_path}")


if __name__ == "__main__":
    run_batch()
