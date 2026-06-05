"""
SK AX 특허 제품 RAG 검색기 - 메인 진입점

Usage:
  # 전체 파이프라인 실행 (크롤링 → 처리 → 인덱싱 → 평가)
  python main.py --run-all

  # 개별 단계 실행
  python main.py --crawl
  python main.py --process
  python main.py --index
  python main.py --evaluate

  # 쿼리 실행
  python main.py --query "AccuInsight+의 시장 전망은?"
  python main.py --query "Aibril은 어떤 사업에 활용돼?" --top-k 3
"""
import argparse
import json
import sys
from pathlib import Path

# src/ 가 패키지 루트
sys.path.insert(0, str(Path(__file__).parent))

from .config import PRODUCTS, RAW_DIR, PROCESSED_DIR, DATA_DIR, TOP_K


def cmd_crawl(keywords: list[str] | None = None, use_playwright: bool = False) -> None:
    from .crawler import crawl_all_products
    targets = keywords if keywords else PRODUCTS
    crawl_all_products(targets, use_playwright=use_playwright)


def cmd_process() -> None:
    from .document_processor import load_and_process
    load_and_process()


def cmd_index() -> None:
    import json
    from .vector_store import build_index
    chunks_path = PROCESSED_DIR / "chunks.json"
    if not chunks_path.exists():
        print("청크 파일이 없습니다. 먼저 --process를 실행하세요.")
        sys.exit(1)
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    build_index(chunks)


def cmd_query(query: str, top_k: int = TOP_K) -> None:
    from .rag_engine import ask, print_result
    result = ask(query, top_k=top_k)
    print_result(result)


def cmd_evaluate(keywords: list[str] | None = None) -> None:
    from .evaluator import evaluate
    evaluate(products=keywords, save_path=DATA_DIR / "eval_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="SK AX 특허 제품 RAG 검색기")
    parser.add_argument("--run-all", action="store_true", help="전체 파이프라인 실행")
    parser.add_argument("--crawl", action="store_true", help="웹 크롤링")
    parser.add_argument("--keyword", nargs="+", metavar="KW",
                        help="크롤링/평가 대상 키워드 지정 (예: --keyword ChainZ Aibril)")
    parser.add_argument("--no-playwright", action="store_true", help="Playwright 비활성화 (requests 사용)")
    parser.add_argument("--process", action="store_true", help="문서 청크 처리")
    parser.add_argument("--index", action="store_true", help="FAISS 인덱스 빌드")
    parser.add_argument("--evaluate", action="store_true", help="RAG 성능 평가")
    parser.add_argument("--query", type=str, help="RAG 검색 쿼리")
    parser.add_argument("--top-k", type=int, default=TOP_K, help=f"검색 결과 수 (기본: {TOP_K})")

    args = parser.parse_args()

    if args.run_all:
        print("=== 1/4 크롤링 ===")
        cmd_crawl(use_playwright=not args.no_playwright)
        print("\n=== 2/4 문서 처리 ===")
        cmd_process()
        print("\n=== 3/4 인덱싱 ===")
        cmd_index()
        print("\n=== 4/4 성능 평가 ===")
        cmd_evaluate()
        return

    if args.crawl:
        cmd_crawl(keywords=args.keyword, use_playwright=not args.no_playwright)
    if args.process:
        cmd_process()
    if args.index:
        cmd_index()
    if args.evaluate:
        cmd_evaluate(keywords=args.keyword)
    if args.query:
        cmd_query(args.query, top_k=args.top_k)

    if not any([args.run_all, args.crawl, args.process, args.index, args.evaluate, args.query]):
        parser.print_help()


if __name__ == "__main__":
    main()
