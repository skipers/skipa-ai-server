"""특허 가치 평가 서비스의 명령행 어댑터입니다.

실제 서비스 로직은 이제 ``valuation_service.py``에 있습니다. 이 파일은 로컬
명령행 실행에만 필요한 책임을 담당합니다.

1. 입력 JSON 파일 1개 또는 JSON 디렉터리를 해석합니다.
2. 각 특허 JSON을 로드합니다.
3. ``PatentValuationService``를 호출합니다.
4. 사람이 읽기 쉬운 요약을 콘솔에 출력합니다.
5. 표준 출력 JSON을 ``artifacts/output`` 아래에 저장합니다.

실제 AI 서버는 스크립트를 셸로 실행하지 않고 같은 서비스 레이어를 직접
호출해야 하므로, 이 어댑터는 얇게 유지하는 것이 중요합니다.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.paths import ARTIFACT_OUTPUT_DIR, SAMPLE_INPUT_DIR
from services.valuation_service import PatentValuationService

DEFAULT_INPUT_DIR = SAMPLE_INPUT_DIR
OUTPUT_DIR = ARTIFACT_OUTPUT_DIR

def resolve_input_files(input_path: str | None = None) -> list[Path]:
    """파일, 디렉터리, 기본 샘플 디렉터리에서 입력 JSON 목록을 해석합니다."""
    if input_path:
        candidate = Path(input_path)
        if not candidate.exists():
            raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")
        if candidate.is_file():
            return [candidate]
        if candidate.is_dir():
            files = sorted(candidate.glob("*.json"))
            if not files:
                raise FileNotFoundError(f"디렉터리에 JSON 파일이 없습니다: {input_path}")
            return files
        raise ValueError(f"지원하지 않는 입력 경로입니다: {input_path}")

    files = sorted(DEFAULT_INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"기본 입력 디렉터리에 JSON 파일이 없습니다: {DEFAULT_INPUT_DIR}")
    return files


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def output_path_for(input_file: Path) -> Path:
    """입력 JSON 파일에 대응하는 출력 경로를 만듭니다."""
    return OUTPUT_DIR / f"{input_file.stem}_output.json"


def run_full_pipeline(patent: dict[str, Any], input_file: str | None = None) -> dict[str, Any]:
    """서비스를 실행하고 기존 구조와 호환되는 딕셔너리를 반환합니다.

    프로토타입에서 ``run_full_pipeline``을 import하던 기존 노트북이나 스크립트와
    호환되도록 함수명은 유지합니다.
    """
    return PatentValuationService().evaluate(patent, input_file=input_file).to_dict()


def print_pipeline_result(result: dict[str, Any]) -> None:
    """로컬 디버깅을 위해 통합 결과를 보기 좋게 출력합니다.

    이 출력 로직은 의도적으로 서비스 레이어에 넣지 않았습니다. 서버 코드는
    JSON을 반환하고, CLI를 실행하는 사용자는 간단한 콘솔 요약을 봅니다.
    """
    print("=" * 72)
    print(f"특허: {result.get('patent_id')} | {result.get('title', '')[:40]}")
    print("=" * 72)

    market = result.get("market_growth") or {}
    print("[시장성]")
    print(f"  C2/산업: {market.get('c2_code')} ({market.get('sector')})")
    print(f"  성장률:  {market.get('growth_rate')}%")
    print(f"  점수:    {market.get('score')}점 / 5점")
    if market.get("source_field"):
        print(f"  출처:    {market.get('source_field')}")
    if market.get("error"):
        print(f"  오류:    {market.get('error')}")

    print()
    print("[자동 점수]")
    auto_scores = result.get("auto_scores", [])
    for score in auto_scores:
        bar = "█" * int(score["score"]) + "░" * (5 - int(score["score"]))
        print(f"  {score['item']:<20} {score['dim']:<6} {score['score']:>2}/5 [{bar}]  {score['basis']}")

    auto_summary = result.get("summary", {}).get("auto", {})
    if auto_summary.get("by_dimension"):
        print("\n  차원별 자동 점수")
        for dim, info in auto_summary["by_dimension"].items():
            print(f"    {dim}: {info['total']}점 / {info['count'] * 5}점 (평균 {info['average']})")

    print()
    print("[LLM 점수]")
    llm_scores = result.get("llm_scores", [])
    if llm_scores:
        all_sources: dict[str, dict] = {}  # url -> source 중복 없이 수집
        for score in llm_scores:
            bar = "█" * int(score["score"]) + "░" * (5 - int(score["score"]))
            print(f"  {score['item']:<20} {score['dim']:<6} {score['score']:>2}/5 [{bar}]")
            print(f"    → {score['reason']}")
            for src in score.get("sources", []):
                url = src.get("url", "")
                if url and url not in all_sources:
                    all_sources[url] = src
        if all_sources:
            print()
            print("  [참고 출처]")
            for i, src in enumerate(all_sources.values(), 1):
                date_str = f" ({src['published_date']})" if src.get("published_date") else ""
                print(f"  [{i}] {src['title']}{date_str}")
                print(f"      {src['url']}")
    else:
        print("  LLM 결과 없음 또는 생략됨")

    if result.get("summary", {}).get("llm_skipped"):
        print(f"  사유: {result['summary']['llm_skipped']}")

    steps = result.get("summary", {}).get("steps", [])
    if steps:
        print()
        print("[실행 단계]")
        for step in steps:
            status = step.get("status")
            elapsed = step.get("elapsed_seconds")
            message = step.get("message", "")
            print(f"  {step.get('name'):<16} {status:<8} {elapsed:>6}s  {message}")


def main() -> None:
    main_start = time.time()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*72}")
    print(f"🚀 파이프라인 시작: {now}")
    print(f"{'='*72}")

    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    input_files = resolve_input_files(input_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n✅ 처리 대상 파일 수: {len(input_files)}")
    for idx, source_path in enumerate(input_files, 1):
        print(f"\n{'-'*72}")
        print(f"📂 [{idx}/{len(input_files)}] 처리 중: {source_path}")
        print(f"{'-'*72}")

        patent = load_json(source_path)
        result = run_full_pipeline(patent, input_file=str(source_path))

        print_pipeline_result(result)

        out_path = output_path_for(source_path)
        with out_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        print(f"\n✅ 통합 결과 저장: {out_path}")

    total_time = time.time() - main_start
    print(f"\n{'='*72}")
    print(f"⏱️  전체 실행 시간: {total_time:.2f}초")
    print(f"📁 결과 저장 폴더: {OUTPUT_DIR}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
