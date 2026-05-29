"""
보고서 레이어용 통합 JSON 생성기

patent_{id}.json (input) + patent_{id}_output.json (llm/auto 평가 결과)
→ patent_{id}_report_input.json (보고서 레이어 입력용)

사용법:
    python build_report_input.py \
        --input  patent_10_2925867.json \
        --output patent_10_2925867_output.json \
        --dest   patent_10_2925867_report_input.json
"""

import json
import argparse
from pathlib import Path


def build_report_input(input_path: str, output_path: str, dest_path: str) -> None:
    # ── 파일 로드 ──
    with open(input_path, encoding="utf-8") as f:
        patent = json.load(f)
    with open(output_path, encoding="utf-8") as f:
        evaluation = json.load(f)

    patent_id = patent.get("patent_id", evaluation.get("patent_id", ""))

    # ── 평가 결과를 dim별로 그룹핑 ──
    def group_scores(scores: list[dict]) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for s in scores:
            dim = s.get("dim", "기타")
            grouped.setdefault(dim, []).append(s)
        return grouped

    auto_scores = evaluation.get("auto_scores", [])
    llm_scores  = evaluation.get("llm_scores", [])

    auto_by_dim = group_scores(auto_scores)
    llm_by_dim  = group_scores(llm_scores)

    # 등장하는 모든 dim 수집
    all_dims = sorted(set(list(auto_by_dim.keys()) + list(llm_by_dim.keys())))

    # dim별 통합 점수 리스트 (auto + llm 합산)
    scores_by_dim: dict[str, list[dict]] = {}
    for dim in all_dims:
        combined = auto_by_dim.get(dim, []) + llm_by_dim.get(dim, [])
        scores_by_dim[dim] = combined

    # ── 차원별 합산 점수 계산 ──
    def dim_summary(scores: list[dict]) -> dict:
        if not scores:
            return {"total": None, "count": 0, "avg": None}
        total = sum(s.get("score", 0) for s in scores if s.get("score") is not None)
        count = sum(1 for s in scores if s.get("score") is not None)
        return {
            "total": total,
            "count": count,
            "avg": round(total / count, 2) if count else None,
        }

    dim_summaries = {dim: dim_summary(scores_by_dim[dim]) for dim in all_dims}

    # ── 통합 JSON 조립 ──
    report_input = {
        "patent_id": patent_id,

        # ── 특허 원본 메타 (input 그대로) ──
        "meta": patent.get("meta", {}),
        "legal": patent.get("legal"),
        "claims_text": patent.get("claims_text", {}),
        "description_summary": patent.get("description_summary", ""),

        # ── 수집 데이터 (있는 것만) ──
        **({"kipris_data": patent["kipris_data"]} if patent.get("kipris_data") else {}),
        **({"market_data": patent["market_data"]} if patent.get("market_data") else {}),
        **({"tax_data": patent["tax_data"]} if patent.get("tax_data") else {}),
        **({"discount_rate_data": patent["discount_rate_data"]} if patent.get("discount_rate_data") else {}),
        **({"llm_input": patent["llm_input"]} if patent.get("llm_input") else {}),
        **({"data_collection_status": patent["data_collection_status"]} if patent.get("data_collection_status") else {}),

        # ── 평가 결과 ──
        "evaluation": {
            "scores_by_dim": scores_by_dim,
            "dim_summary": dim_summaries,
            "all_scores": auto_scores + llm_scores,
        },
    }

    # ── 저장 ──
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(report_input, f, ensure_ascii=False, indent=2)

    print(f"✅ 저장 완료: {dest}")
    print(f"   특허: {patent_id}")
    print(f"   평가 차원: {list(all_dims)}")
    for dim, summary in dim_summaries.items():
        print(f"   [{dim}] {summary['count']}개 항목, 합계 {summary['total']}점, 평균 {summary['avg']}점")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="보고서 레이어용 통합 JSON 생성")
    parser.add_argument("--input",  required=True, help="특허 input JSON 경로")
    parser.add_argument("--output", required=True, help="평가 output JSON 경로")
    parser.add_argument("--dest",   required=True, help="생성할 report_input JSON 경로")
    args = parser.parse_args()

    build_report_input(args.input, args.output, args.dest)