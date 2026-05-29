"""
Collect detailed records for similar patents.

Default behavior uses data/patent_references.json as candidates. If
KIPRIS_API_KEY is set, the collector enriches each candidate through KIPRIS Plus
APIs. Without the key, it still writes a normalized details file from the
candidate data so downstream analysis can run offline.

Usage:
    python3 crawling/similar_patent_collector.py
    KIPRIS_API_KEY=... python3 crawling/similar_patent_collector.py --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from crawling.kipris_api_client import (  # noqa: E402
    KiprisApiClient,
    cache_path,
    normalize_patent_detail,
    sanitize_error,
)
from core.paths import ARTIFACT_CACHE_DIR, ARTIFACT_OUTPUT_DIR, SAMPLE_DATA_DIR  # noqa: E402


DEFAULT_CANDIDATES = SAMPLE_DATA_DIR / "patent_references.json"
DEFAULT_OUTPUT = ARTIFACT_OUTPUT_DIR / "similar_patent_details.json"
DEFAULT_CACHE_DIR = ARTIFACT_CACHE_DIR / "kipris"


def normalize_patent_id(value: str | None) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value or "")).strip("_")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_candidates(path: Path, limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = load_json(path)
    candidates = data.get("patents", data if isinstance(data, list) else [])
    if not isinstance(candidates, list):
        raise ValueError(f"후보 특허 목록을 찾을 수 없습니다: {path}")
    return data.get("meta", {}), candidates[:limit]


def candidate_identifier(candidate: dict[str, Any]) -> str:
    for key in ("application_number", "출원번호", "patent_no", "registration_number", "발명명칭", "title"):
        value = candidate.get(key)
        if value:
            return str(value)
    return f"rank_{candidate.get('rank', 'unknown')}"


def fetch_or_load_bundle(
    client: KiprisApiClient,
    candidate: dict[str, Any],
    cache_dir: Path,
    use_cache: bool,
    extra_operations: list[str],
) -> dict[str, Any]:
    identifier = candidate_identifier(candidate)
    path = cache_path(cache_dir, identifier)
    if use_cache and path.exists():
        return load_json(path)

    application_number = (
        candidate.get("application_number")
        or candidate.get("출원번호")
        or candidate.get("application_no")
        or ""
    )
    title = candidate.get("title") or candidate.get("발명명칭") or ""
    bundle = client.fetch_patent_bundle(
        application_number=str(application_number),
        title=str(title),
        extra_operations=extra_operations,
    )
    write_json(path, bundle)
    return bundle


def collect_similar_patent_details(
    candidates_path: Path = DEFAULT_CANDIDATES,
    output_path: Path = DEFAULT_OUTPUT,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    limit: int = 10,
    use_cache: bool = True,
    extra_operations: list[str] | None = None,
) -> dict[str, Any]:
    meta, candidates = load_candidates(candidates_path, limit)
    client = KiprisApiClient()
    extra_operations = extra_operations or []

    details = []
    cache_dir.mkdir(parents=True, exist_ok=True)

    for index, candidate in enumerate(candidates, 1):
        title = candidate.get("title") or candidate.get("발명명칭") or candidate.get("patent_no", "")
        print(f"[{index}/{len(candidates)}] {title}")

        if client.enabled:
            try:
                bundle = fetch_or_load_bundle(client, candidate, cache_dir, use_cache, extra_operations)
            except Exception as exc:
                bundle = {
                    "application_number": "",
                    "raw": {},
                    "errors": [sanitize_error(exc)],
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
                print(f"  API 수집 실패: {exc}")
        else:
            bundle = {
                "application_number": candidate.get("application_number") or candidate.get("출원번호") or "",
                "raw": {},
                "errors": ["KIPRIS_API_KEY not set"],
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            }

        detail = normalize_patent_detail(candidate, bundle)
        details.append(detail)
        print(f"  -> {detail.get('application_number') or '-'} / {detail.get('legal_status') or '-'}")

    output = {
        "meta": {
            "source_candidates": str(candidates_path),
            "source_candidate_meta": meta,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "api_enabled": client.enabled,
            "limit": limit,
            "extra_operations": extra_operations,
        },
        "patents": details,
    }
    write_json(output_path, output)
    print(f"\n저장 완료: {output_path} ({len(details)}건)")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="유사 특허 상세정보 수집")
    parser.add_argument("--patent-id", default=None, help="특허별 output 파일명에 사용할 ID")
    parser.add_argument("--output-dir", default=str(ARTIFACT_OUTPUT_DIR), help="--patent-id 사용 시 입출력 파일 디렉터리")
    parser.add_argument("--candidates", default=None, help="유사 특허 후보 JSON")
    parser.add_argument("--output", default=None, help="상세정보 출력 JSON")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="KIPRIS raw 응답 캐시 디렉터리")
    parser.add_argument("--limit", type=int, default=10, help="수집할 후보 수")
    parser.add_argument("--no-cache", action="store_true", help="캐시를 무시하고 다시 호출")
    parser.add_argument(
        "--extra-operation",
        action="append",
        default=[],
        help="applicationNumber로 추가 호출할 KIPRIS operation 이름. 여러 번 지정 가능",
    )
    args = parser.parse_args()
    patent_id = normalize_patent_id(args.patent_id)
    output_dir = Path(args.output_dir)
    candidates_path = Path(args.candidates) if args.candidates else (
        output_dir / f"similar_refs_{patent_id}.json" if patent_id else DEFAULT_CANDIDATES
    )
    output_path = Path(args.output) if args.output else (
        output_dir / f"similar_details_{patent_id}.json" if patent_id else DEFAULT_OUTPUT
    )

    collect_similar_patent_details(
        candidates_path=candidates_path,
        output_path=output_path,
        cache_dir=Path(args.cache_dir),
        limit=args.limit,
        use_cache=not args.no_cache,
        extra_operations=args.extra_operation,
    )


if __name__ == "__main__":
    main()
