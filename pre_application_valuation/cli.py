"""CLI runner for pre-application patent valuation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .schemas import PreApplicationValuationRequest
from .service import evaluate_pre_application
from .storage import DEFAULT_OUTPUT_DIR, load_json, save_result


def main() -> None:
    parser = argparse.ArgumentParser(description="출원 전 아이디어/특허 사전 가치 평가 CLI")
    parser.add_argument("--input-json", help="평가 입력 JSON 경로")
    parser.add_argument("--patent-name", help="특허명")
    parser.add_argument("--technology-description", help="기술 설명")
    parser.add_argument("--claim", action="append", default=[], help="청구항. 여러 번 지정 가능")
    parser.add_argument("--related-business", default="", help="관련 사업")
    parser.add_argument("--target-countries", default="", help="쉼표로 구분한 출원 예정 국가")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="결과 JSON 저장 디렉토리")
    parser.add_argument("--print", action="store_true", dest="print_result", help="결과 JSON을 stdout에도 출력")
    args = parser.parse_args()

    payload = _payload_from_args(args)
    request = PreApplicationValuationRequest.model_validate(payload)
    result = evaluate_pre_application(request)
    output_path = save_result(result, args.output_dir)
    result.setdefault("artifacts", {})
    result["artifacts"]["output_path"] = str(output_path)

    if args.print_result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(str(output_path))


def _payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        return load_json(Path(args.input_json))
    return {
        "patent_name": args.patent_name,
        "technology_description": args.technology_description,
        "claims": args.claim,
        "related_business": args.related_business,
        "target_countries": args.target_countries,
    }


if __name__ == "__main__":
    main()
