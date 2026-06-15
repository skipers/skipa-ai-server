"""Golden Q&A 시트 생성 스크립트.

10개 특허 × 6개 카테고리 × 50개 = 3,000개 총합
각 (특허, 카테고리) 조합마다 50개 Q&A를 GPT-4.1이 생성합니다.

사용법:
  cd /Users/kgw/skipers-ai
  python chatbot/scripts/gen_golden_qa.py \\
    --patent-ids "10-1959619,10-1959627,10-2042318,10-2142205,10-2663094,10-2686678,10-2737902,10-2753879,10-2762042,10-2839217"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parents[2])

from dotenv import load_dotenv
load_dotenv("chatbot/.env")

from openai import OpenAI

CATEGORIES = ["overview", "claims", "market", "risk", "comparison", "evidence"]

CATEGORY_DESCRIPTIONS = {
    "overview":   "특허의 핵심 가치, 기술 요약, 사업화 관점",
    "claims":     "청구항, 기술적 차별점, 핵심 구성요소",
    "market":     "시장 성장성, 사업화 가능성, 산업 응용",
    "risk":       "권리 리스크, 회피 설계, 무효 가능성",
    "comparison": "유사 특허 비교, 경쟁 특허와의 차별점",
    "evidence":   "평가 점수 근거, 핵심 증거, 참고 문헌",
}

REPORT_FIELDS: dict[str, list[str]] = {
    "overview":   ["section_1_summary.overall_opinion",
                   "section_1_summary.project_utilization_brief",
                   "section_1_summary.title",
                   "section_1_summary.dimension_scores",
                   "section_1_summary.overall_score_out_of_100",
                   "section_1_summary.overall_grade",
                   "section_2_detailed_scores.dimensions"],
    "claims":     ["section_2_detailed_scores.dimensions",
                   "section_1_summary.title"],
    "market":     ["section_2_detailed_scores.dimensions",
                   "section_1_summary.project_utilization_brief",
                   "section_1_summary.dimension_scores",
                   "section_1_summary.overall_score_out_of_100",
                   "section_1_summary.market_sector"],
    "risk":       ["section_2_detailed_scores.dimensions",
                   "section_5_review_items"],
    "comparison": ["section_4_similar_patents"],
    "evidence":   ["section_1_summary.dimension_scores",
                   "section_6_references",
                   "section_1_summary.overall_score_out_of_100",
                   "section_1_summary.overall_grade"],
}

# 대체 스키마 (일부 특허의 다른 report.json 구조)
REPORT_FIELDS_ALT: dict[str, list[str]] = {
    "overview":   ["summary.overall_opinion",
                   "analysis.overall",
                   "summary.overall_grade"],
    "claims":     ["evaluation.dimensions",
                   "analysis.grade"],
    "market":     ["evaluation.dimensions",
                   "analysis.market_sector"],
    "risk":       ["risks.items",
                   "analysis.watch_dimensions"],
    "comparison": ["similar_patents"],
    "evidence":   ["summary.dimension_scores",
                   "references.sources",
                   "summary.overall_score_out_of_100",
                   "summary.overall_grade"],
}

_GENERATE_PROMPT = """당신은 특허 분석 전문가입니다.
아래 특허 보고서 내용을 바탕으로, '{category}' 카테고리({desc})에 관한
질문-답변 쌍 {n}개를 생성하세요.

조건:
- 질문은 특허 RAG 챗봇을 테스트하기 위한 것입니다
- 질문은 구체적이고 보고서 내용에서 명확히 답할 수 있어야 합니다
- 답변은 보고서 기반으로 3~6문장, 150~300자 분량으로 핵심 사실과 그 근거·수치를 함께 서술합니다
- 첫 문장에서 질문에 직접 답하고, 이후 문장에서 근거·수치·맥락을 추가합니다
- 중요: 보고서 내용에 실제 데이터가 있는 질문만 생성하세요. "없습니다", "언급이 없습니다", "명시되지 않았습니다" 형태로 답하는 질문은 생성하지 마세요
- 점수·등급·항목명·판단 근거 등 구체적 수치나 사실이 있는 내용을 기반으로 질문을 만드세요
- 서로 다른 측면을 다루는 다양한 질문을 생성하세요 (유사한 질문 반복 금지)
- 질문과 답변은 한국어로 작성하세요

특허 ID: {patent_id}
특허 보고서 내용:
{context}

JSON 배열로만 반환하세요:
[
  {{"question": "...", "answer": "..."}},
  ...
]"""


def _get_nested(d: dict, dotpath: str):
    for p in dotpath.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _extract_context(report_path: Path, category: str) -> str:
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        rep = data.get("report") or {}

        def _pull(fields: list[str]) -> list[str]:
            results = []
            for field in fields:
                # rep 안과 data 최상위 모두 시도
                val = _get_nested(rep, field) or _get_nested(data, field)
                if val is None:
                    continue
                if isinstance(val, str):
                    results.append(val[:1200])
                else:
                    results.append(json.dumps(val, ensure_ascii=False)[:1200])
            return results

        parts = _pull(REPORT_FIELDS.get(category, []))
        if not parts:
            parts = _pull(REPORT_FIELDS_ALT.get(category, []))
        return "\n\n".join(parts)
    except Exception:
        return ""


def generate_qa(
    client: OpenAI,
    patent_id: str,
    report_path: Path,
    category: str,
    n: int = 50,
    retries: int = 3,
) -> list[dict]:
    context = _extract_context(report_path, category)
    if not context.strip():
        print(f"    [WARN] {patent_id}/{category}: 보고서 내용 없음", file=sys.stderr)
        return []

    prompt = _GENERATE_PROMPT.format(
        category=category,
        desc=CATEGORY_DESCRIPTIONS[category],
        n=n,
        patent_id=patent_id,
        context=context[:4000],
    )

    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                response_format={"type": "json_object"},
                timeout=120,
            )
            raw = resp.choices[0].message.content
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = parsed
            else:
                items = next((v for v in parsed.values() if isinstance(v, list)), [])

            result = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                q = str(item.get("question") or "").strip()
                a = str(item.get("answer") or "").strip()
                if q and a:
                    result.append({
                        "patent_id": patent_id,
                        "category":  category,
                        "question":  q,
                        "answer":    a,
                    })
            if result:
                return result[:n]
        except Exception as e:
            print(f"    [WARN] attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(2)
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--patent-ids",
        default="10-1959619,10-1959627,10-2042318,10-2142205,10-2663094,"
                "10-2686678,10-2737902,10-2753879,10-2762042,10-2839217",
    )
    parser.add_argument("--per-pair", type=int, default=50,
                        help="(특허, 카테고리) 쌍당 Q&A 수 (기본 50 → 총 3,000)")
    parser.add_argument("--patent-root", type=Path, default=Path("data/patent"))
    parser.add_argument("--output",      type=Path,
                        default=Path("chatbot/data/artifacts/golden_qa.json"))
    args = parser.parse_args()

    patent_ids = [p.strip() for p in args.patent_ids.split(",")]
    client     = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_tasks   = len(patent_ids) * len(CATEGORIES)
    total_planned = total_tasks * args.per_pair
    print(f"\n{'='*65}")
    print(f"  Golden Q&A 생성")
    print(f"  {len(patent_ids)}개 특허 × {len(CATEGORIES)}개 카테고리 × {args.per_pair}개 = {total_planned:,}개")
    print(f"{'='*65}\n")

    all_qa: list[dict] = []
    idx = 0

    for pid in patent_ids:
        report_path = args.patent_root / pid / "report.json"
        if not report_path.exists():
            print(f"[WARN] {pid}: report.json 없음, 건너뜀")
            continue

        for cat in CATEGORIES:
            idx += 1
            print(f"  [{idx:02d}/{total_tasks}] {pid} / {cat} ...", end=" ", flush=True)
            t0    = time.time()
            pairs = generate_qa(client, pid, report_path, cat, n=args.per_pair)
            elapsed = round(time.time() - t0, 1)
            print(f"{len(pairs)}개 생성 ({elapsed}s)")
            all_qa.extend(pairs)

    # 요약
    from collections import Counter
    by_cat = Counter(q["category"] for q in all_qa)
    by_pat = Counter(q["patent_id"] for q in all_qa)
    print(f"\n{'='*65}")
    print(f"생성 완료: 총 {len(all_qa):,}개")
    print(f"\n카테고리별:")
    for c in CATEGORIES:
        print(f"  {c:12s}: {by_cat.get(c, 0):4d}개")
    print(f"\n특허별:")
    for pid in patent_ids:
        print(f"  {pid}: {by_pat.get(pid, 0):4d}개")

    args.output.write_text(
        json.dumps(all_qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n저장: {args.output}")


if __name__ == "__main__":
    main()
