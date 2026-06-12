"""챗봇 응답 수집 전용 subprocess 헬퍼.

eval_rag.py가 subprocess로 호출하며, chatbot 모듈만 import하고
JSON 결과를 stdout으로 출력합니다 (ragas/langchain_openai 미사용).

인자 (JSON string):
  patent_ids:      평가할 특허 ID 목록
  top_k:           retrieval top-k
  golden_qa_path:  (선택) golden Q&A JSON 경로 — 없으면 기본 6개 질문 사용
"""

from __future__ import annotations

import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parents[2])

from dotenv import load_dotenv
load_dotenv("chatbot/.env")

# 기본 고정 질문 (golden_qa 없을 때 fallback)
DEFAULT_QUESTIONS = [
    ("overview",   "이 특허를 사업부 관점에서 핵심 가치 중심으로 3줄로 요약해줘."),
    ("claims",     "이 특허의 핵심 청구항이 뭐야? 기술적 차별점 위주로 설명해줘."),
    ("market",     "이 특허의 시장 성장성과 사업화 가능성을 평가해줘."),
    ("risk",       "이 특허의 권리 리스크와 회피 설계 방향을 알려줘."),
    ("comparison", "이 특허와 유사한 경쟁 특허들과의 차별점이 뭐야?"),
    ("evidence",   "이 특허의 평가 점수 근거가 되는 핵심 증거를 보여줘."),
]

REPORT_FIELDS = {
    "overview":   ["section_1_summary.overall_opinion", "section_1_summary.project_utilization_brief"],
    "claims":     ["section_2_detailed_scores.dimensions"],
    "market":     ["section_2_detailed_scores.dimensions", "section_1_summary.project_utilization_brief"],
    "risk":       ["section_2_detailed_scores.dimensions", "section_5_review_items"],
    "comparison": ["section_4_similar_patents"],
    "evidence":   ["section_1_summary.dimension_scores", "section_6_references"],
}


def _get_nested(d, dotpath):
    for p in dotpath.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _extract_reference(report_path: Path, category: str) -> str:
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        rep = data.get("report") or {}
        parts = []
        for field in REPORT_FIELDS.get(category, []):
            val = _get_nested(rep, field)
            if val is None:
                continue
            if isinstance(val, str):
                parts.append(val[:800])
            else:
                parts.append(json.dumps(val, ensure_ascii=False)[:800])
        return "\n\n".join(parts)
    except Exception:
        return ""


def main():
    args = json.loads(sys.argv[1])
    patent_ids       = args["patent_ids"]
    top_k            = args["top_k"]
    golden_qa_path   = args.get("golden_qa_path")
    sample_per_pair  = args.get("sample_per_pair")  # None = 전체 사용

    from chatbot.app.agents.graph import run_chat_agent
    from chatbot.app.store import list_patents

    patent_map  = {p["patent_id"]: p for p in list_patents()}
    patent_root = Path("data/patent")

    # golden Q&A 로드 또는 기본 질문 사용
    if golden_qa_path and Path(golden_qa_path).exists():
        import random
        raw_qa = json.loads(Path(golden_qa_path).read_text(encoding="utf-8"))
        # (patent_id, category) 별로 그룹핑 + 샘플링
        from collections import defaultdict
        qa_by_pair: dict[tuple, list[dict]] = defaultdict(list)
        for item in raw_qa:
            qa_by_pair[(item["patent_id"], item["category"])].append(item)
        if sample_per_pair:
            sampled = []
            for key, items in qa_by_pair.items():
                sampled.extend(random.sample(items, min(sample_per_pair, len(items))))
            raw_qa = sampled
        qa_by_patent: dict[str, list[dict]] = defaultdict(list)
        for item in raw_qa:
            qa_by_patent[item["patent_id"]].append(item)
        print(f"  Golden Q&A 로드: {len(raw_qa)}개"
              + (f" (특허×카테고리당 {sample_per_pair}개 샘플)" if sample_per_pair else "")
              + f" ({len(qa_by_patent)}개 특허)", file=sys.stderr)
        use_golden = True
    else:
        qa_by_patent = {}
        use_golden   = False
        if golden_qa_path:
            print(f"  [WARN] golden_qa_path '{golden_qa_path}' 없음 → 기본 질문 사용", file=sys.stderr)

    samples = []

    if use_golden:
        # golden Q&A 기반 수집
        all_items = []
        for pid in patent_ids:
            for item in qa_by_patent.get(pid, []):
                all_items.append((pid, item["category"], item["question"], item["answer"]))
        total = len(all_items)

        for idx, (pid, category, question, golden_answer) in enumerate(all_items, 1):
            title       = (patent_map.get(pid) or {}).get("title") or pid
            report_path = patent_root / pid / "report.json"

            print(f"  [{idx:03d}/{total}] [{category:10s}] {pid}", end=" ... ", flush=True, file=sys.stderr)
            t0 = time.time()
            try:
                result    = run_chat_agent(question, patent_id=pid, chat_history=[], top_k=top_k)
                answer    = result.get("answer") or ""
                src_cards = result.get("source_cards") or []
                contexts  = [" ".join(str(c.get("snippet") or "").split())
                             for c in src_cards if c.get("snippet")]
                ok = True
            except Exception as e:
                print(f"[ERROR] {e}", file=sys.stderr)
                answer, contexts = "", []
                ok = False

            elapsed   = round(time.time() - t0, 2)
            reference = _extract_reference(report_path, category)
            tok_in    = len(question.split()) * 2 + sum(len(c.split()) for c in contexts) * 2
            tok_out   = len(answer.split()) * 2

            print(f"{len(contexts)} src, {elapsed}s", file=sys.stderr)
            samples.append({
                "patent_id":     pid,
                "patent_title":  title,
                "category":      category,
                "question":      question,
                "golden_answer": golden_answer,
                "answer":        answer,
                "contexts":      contexts or ["(검색 결과 없음)"],
                "reference":     reference,
                "chatbot_ok":    ok,
                "source_count":  len(contexts),
                "latency_sec":   elapsed,
                "tok_in_est":    tok_in,
                "tok_out_est":   tok_out,
            })
    else:
        # 기본 6개 질문으로 수집
        total = len(patent_ids) * len(DEFAULT_QUESTIONS)
        idx   = 0

        for pid in patent_ids:
            title       = (patent_map.get(pid) or {}).get("title") or pid
            report_path = patent_root / pid / "report.json"

            for category, question in DEFAULT_QUESTIONS:
                idx += 1
                print(f"  [{idx:02d}/{total}] [{category:10s}] {pid}", end=" ... ", flush=True, file=sys.stderr)
                t0 = time.time()
                try:
                    result    = run_chat_agent(question, patent_id=pid, chat_history=[], top_k=top_k)
                    answer    = result.get("answer") or ""
                    src_cards = result.get("source_cards") or []
                    contexts  = [" ".join(str(c.get("snippet") or "").split())
                                 for c in src_cards if c.get("snippet")]
                    ok = True
                except Exception as e:
                    print(f"[ERROR] {e}", file=sys.stderr)
                    answer, contexts = "", []
                    ok = False

                elapsed   = round(time.time() - t0, 2)
                reference = _extract_reference(report_path, category)
                tok_in    = len(question.split()) * 2 + sum(len(c.split()) for c in contexts) * 2
                tok_out   = len(answer.split()) * 2

                print(f"{len(contexts)} src, {elapsed}s", file=sys.stderr)
                samples.append({
                    "patent_id":     pid,
                    "patent_title":  title,
                    "category":      category,
                    "question":      question,
                    "golden_answer": None,
                    "answer":        answer,
                    "contexts":      contexts or ["(검색 결과 없음)"],
                    "reference":     reference,
                    "chatbot_ok":    ok,
                    "source_count":  len(contexts),
                    "latency_sec":   elapsed,
                    "tok_in_est":    tok_in,
                    "tok_out_est":   tok_out,
                })

    print(json.dumps(samples, ensure_ascii=False))


if __name__ == "__main__":
    main()
