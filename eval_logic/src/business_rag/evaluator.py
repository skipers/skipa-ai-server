"""
RAG 검색 성능 평가: Hit Rate, MRR, Precision@K.

평가 데이터셋: 각 제품명으로 생성한 golden query → 해당 제품 문서가 검색되면 정답.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import PRODUCTS, TOP_K, PROCESSED_DIR
from .vector_store import search


# 제품별 평가 쿼리 (자동 생성)
def _generate_eval_queries(products: list[str]) -> list[dict]:
    queries = []
    templates = [
        "{p}의 시장 전망은?",
        "{p} 제품의 사업성은 어떻게 돼?",
        "{p}는 어떤 솔루션이야?",
        "{p}의 경쟁 시장 내 위치는?",
    ]
    for product in products:
        for tmpl in templates:
            queries.append({
                "query": tmpl.format(p=product),
                "relevant_keyword": product,
            })
    return queries


@dataclass
class EvalResult:
    query: str
    relevant_keyword: str
    retrieved_keywords: list[str]
    hit: bool
    reciprocal_rank: float
    rank: int  # 정답이 처음 등장한 순위 (없으면 0)


def _evaluate_single(q: dict, top_k: int) -> EvalResult:
    results = search(q["query"], top_k=top_k)
    retrieved_keywords = [r["keyword"] for r in results]
    target = q["relevant_keyword"].lower()

    hit = False
    rr = 0.0
    rank = 0
    for i, kw in enumerate(retrieved_keywords, 1):
        if target in kw.lower() or kw.lower() in target:
            hit = True
            rr = 1.0 / i
            rank = i
            break

    return EvalResult(
        query=q["query"],
        relevant_keyword=q["relevant_keyword"],
        retrieved_keywords=retrieved_keywords,
        hit=hit,
        reciprocal_rank=rr,
        rank=rank,
    )


def evaluate(
    products: list[str] | None = None,
    top_k: int = TOP_K,
    save_path: Path | None = None,
) -> dict:
    """
    전체 평가 실행.

    Returns:
        {
            "hit_rate": float,
            "mrr": float,
            "precision_at_k": float,
            "total_queries": int,
            "details": list[dict]
        }
    """
    if products is None:
        products = PRODUCTS

    # 인덱싱된 키워드만 평가 (없는 제품 제외)
    chunks_path = PROCESSED_DIR / "chunks.json"
    if chunks_path.exists():
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        indexed_keywords = {c["keyword"] for c in chunks}
        products = [p for p in products if p in indexed_keywords]

    if not products:
        print("평가할 인덱싱된 문서가 없습니다.")
        return {}

    eval_queries = _generate_eval_queries(products)
    results: list[EvalResult] = []

    print(f"평가 쿼리 {len(eval_queries)}개 실행 중...")
    for i, q in enumerate(eval_queries, 1):
        r = _evaluate_single(q, top_k)
        results.append(r)
        if i % 10 == 0:
            print(f"  {i}/{len(eval_queries)} 완료")

    total = len(results)
    hit_rate = sum(r.hit for r in results) / total
    mrr = sum(r.reciprocal_rank for r in results) / total
    hits_at_k = sum(1 for r in results if r.rank > 0 and r.rank <= top_k) / total

    details = [
        {
            "query": r.query,
            "relevant_keyword": r.relevant_keyword,
            "retrieved_keywords": r.retrieved_keywords,
            "hit": r.hit,
            "rank": r.rank,
            "reciprocal_rank": round(r.reciprocal_rank, 4),
        }
        for r in results
    ]

    report = {
        "top_k": top_k,
        "total_queries": total,
        "hit_rate": round(hit_rate, 4),
        "mrr": round(mrr, 4),
        f"precision_at_{top_k}": round(hits_at_k, 4),
        "details": details,
    }

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"평가 결과 저장 → {save_path}")

    _print_report(report)
    return report


def _print_report(report: dict) -> None:
    k = report["top_k"]
    print(f"\n{'=' * 50}")
    print(f"RAG 검색 성능 평가 결과 (Top-{k})")
    print(f"{'=' * 50}")
    print(f"  총 쿼리 수     : {report['total_queries']}")
    print(f"  Hit Rate       : {report['hit_rate']:.4f} ({report['hit_rate']*100:.1f}%)")
    print(f"  MRR            : {report['mrr']:.4f}")
    print(f"  Precision@{k}   : {report[f'precision_at_{k}']:.4f}")
    print(f"{'=' * 50}")

    # 실패 케이스 요약
    failed = [d for d in report["details"] if not d["hit"]]
    if failed:
        print(f"\n미검색 케이스 ({len(failed)}개):")
        for f in failed[:5]:
            print(f"  - [{f['relevant_keyword']}] {f['query']}")
        if len(failed) > 5:
            print(f"  ... 외 {len(failed) - 5}개")


if __name__ == "__main__":
    from .config import DATA_DIR
    evaluate(save_path=DATA_DIR / "eval_report.json")
