"""SKIPA 특허 챗봇 종합 RAG 성능 평가 스크립트.

평가 영역 4가지:

  1. Retrieval   — Hit@K, Precision@K, MRR, nDCG@K
                   LLM binary judge → 각 청크의 관련성 판정 (K=3 기본)
  2. Answer      — LLM Judge (0~1, vs golden answer) + Semantic Sim (cosine)
  3. Groundedness— LLM Judge (0~1, 답변이 컨텍스트에 근거하는 정도)
  4. Production  — Latency (mean/p95), Source Count, Fallback Rate, Token/Cost 추정

golden Q&A 시트 사용 시 (--golden-qa):
  gen_golden_qa.py로 생성한 300개 Q&A를 retrieval + answer 평가 ground truth로 활용.

사용법:
  cd /Users/kgw/skipers-ai
  # golden Q&A 먼저 생성:
  python chatbot/scripts/gen_golden_qa.py

  # 평가 실행 (실시간 로그):
  python chatbot/scripts/eval_rag.py \\
    --patent-ids "10-1959619,10-1959627,10-2042318,10-2142205,10-2663094,10-2686678,10-2737902,10-2753879,10-2762042,10-2839217" \\
    --top-k 3 --skip-bertscore \\
    --golden-qa chatbot/data/artifacts/golden_qa.json \\
    2>&1 | tee chatbot/data/artifacts/eval_$(date +%Y%m%d_%H%M%S).log
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parents[2])

from dotenv import load_dotenv
load_dotenv("chatbot/.env")

import numpy as np
from openai import OpenAI

OPENAI_PRICE_PER_1K_IN  = 0.002   # gpt-4.1 input  $/1K tokens (근사)
OPENAI_PRICE_PER_1K_OUT = 0.008   # gpt-4.1 output $/1K tokens (근사)


# ════════════════════════════════════════════════════════════════
# Phase 0 — 유틸리티
# ════════════════════════════════════════════════════════════════

def _avg(samples: list[dict], key: str) -> float:
    vals = [s[key] for s in samples if isinstance(s.get(key), (int, float)) and s.get(key) is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _parse_float(text: str, default: float = 0.0) -> float:
    """GPT 응답에서 0~1 float 파싱."""
    m = re.search(r"[01](?:\.\d+)?|\.\d+", text.strip())
    if m:
        v = float(m.group())
        return round(min(max(v, 0.0), 1.0), 4)
    return default


# ════════════════════════════════════════════════════════════════
# Phase 1 — 챗봇 응답 수집 (subprocess 분리 — langgraph 버전 충돌 방지)
# ════════════════════════════════════════════════════════════════

def collect_responses(patent_ids: list[str], top_k: int,
                      golden_qa_path: str | None = None,
                      sample_per_pair: int | None = None,
                      retrieval_only: bool = False) -> list[dict]:
    import subprocess
    helper = Path(__file__).with_name("_collect_responses.py")
    arg    = json.dumps({
        "patent_ids":      patent_ids,
        "top_k":           top_k,
        "golden_qa_path":  golden_qa_path,
        "sample_per_pair": sample_per_pair,
        "retrieval_only":  retrieval_only,
    })
    proc = subprocess.run(
        [sys.executable, str(helper), arg],
        capture_output=False,
        stdout=subprocess.PIPE,
        text=True,
        timeout=7200,   # golden Q&A 300개 기준 최대 2시간
    )
    if proc.returncode != 0:
        raise RuntimeError(f"collect subprocess 실패 (returncode={proc.returncode})")
    return json.loads(proc.stdout.strip())


# ════════════════════════════════════════════════════════════════
# Phase 2 — Retrieval 지표 (LLM binary chunk relevance → rank metrics)
# ════════════════════════════════════════════════════════════════

_RELEVANCE_PROMPT = """다음 질문에 대해, 주어진 문서 청크가 답변하는 데 유용한지 판단하세요.
"yes" 또는 "no"만 답하세요.

질문: {question}
청크: {chunk}"""

_RELEVANCE_WITH_GOLDEN_PROMPT = """다음 질문과 정답 힌트를 참고하여, 주어진 문서 청크가 질문 답변에 유용한지 판단하세요.
"yes" 또는 "no"만 답하세요.

판단 기준:
- 청크가 질문에 대한 답변(긍정적이든 부정적이든)을 제공하면 "yes"
- 질문이 특정 정보의 존재 여부를 묻는 경우, 해당 정보가 없다고 명시하는 청크도 유용한 것으로 간주하여 "yes"
- 청크가 질문과 전혀 관련 없으면 "no"

질문: {question}
정답 힌트 (레퍼런스 답변 요약): {golden_hint}
청크: {chunk}"""


def _judge_chunk_relevance(
    client: OpenAI, question: str, chunk: str,
    golden_hint: str | None = None
) -> int:
    try:
        if golden_hint:
            content = _RELEVANCE_WITH_GOLDEN_PROMPT.format(
                question=question[:300],
                golden_hint=golden_hint[:200],
                chunk=chunk[:400],
            )
        else:
            content = _RELEVANCE_PROMPT.format(
                question=question[:300], chunk=chunk[:400]
            )
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": content}],
            temperature=0,
            max_tokens=5,
            timeout=15,
        )
        return 1 if "yes" in resp.choices[0].message.content.lower() else 0
    except Exception:
        return 0


def _ndcg(relevances: list[int], k: int) -> float:
    relevances = relevances[:k]
    dcg  = sum(r / math.log2(i + 2) for i, r in enumerate(relevances))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(sum(relevances), k)))
    return dcg / idcg if idcg > 0 else 0.0


def _score_sample(args):
    i, total, s, client, k = args
    chunks      = s["contexts"][:k]
    golden_hint = (s.get("golden_answer") or "")[:200] or None
    print(f"  [{i+1:03d}/{total}] [{s['category']:10s}] {s['patent_id']} relevance@{k}...", flush=True)
    rels = [_judge_chunk_relevance(client, s["question"], c, golden_hint) for c in chunks]
    hit  = float(any(rels))
    prec = sum(rels) / len(rels)
    mrr  = next((1 / (j + 1) for j, r in enumerate(rels) if r), 0.0)
    ndcg = _ndcg(rels, k)
    return i, {"hit_at_k": round(hit, 4), "precision_at_k": round(prec, 4),
               "mrr": round(mrr, 4), "ndcg_at_k": round(ndcg, 4), "relevance_list": rels}


def compute_retrieval(samples: list[dict], client: OpenAI, k: int = 3) -> list[dict]:
    total = len(samples)
    valid_args = []
    for i, s in enumerate(samples):
        if not s["chatbot_ok"] or s["source_count"] == 0:
            s.update({"hit_at_k": 0.0, "precision_at_k": 0.0,
                       "mrr": 0.0, "ndcg_at_k": 0.0, "relevance_list": []})
        else:
            valid_args.append((i, total, s, client, k))

    with ThreadPoolExecutor(max_workers=20) as pool:
        for i, metrics in pool.map(_score_sample, valid_args):
            samples[i].update(metrics)

    return samples


# ════════════════════════════════════════════════════════════════
# Phase 3 — Answer Quality (LLM Judge + Cosine Similarity)
# ════════════════════════════════════════════════════════════════
#
# LLM Judge (0~1):
#   - 질문 + golden_answer(또는 reference) + chatbot_answer
#   - GPT-4.1이 정확성·완결성·관련성 기준으로 0~1 점수 판정
#
# Semantic Similarity:
#   - OpenAI text-embedding-3-large 기반 코사인 유사도
#   - 비교 대상: golden_answer 우선, 없으면 reference

_ANSWER_QUALITY_JUDGE_PROMPT = """당신은 AI 답변을 평가하는 전문가입니다.
질문에 대한 챗봇 답변이 레퍼런스 답변과 얼마나 일치하는지 0~1 점수로 평가하세요.

평가 기준:
- 1.0: 완벽히 일치하거나 레퍼런스보다 더 상세하고 정확
- 0.7~0.9: 핵심 내용 포함, 일부 세부 사항 누락
- 0.4~0.6: 관련은 있으나 중요한 내용 누락 또는 부정확
- 0.1~0.3: 주제는 맞으나 내용이 크게 다름
- 0.0: 완전히 틀리거나 관련 없음

질문: {question}
레퍼런스 답변: {reference}
챗봇 답변: {answer}

점수만 반환하세요 (예: 0.75)."""


def _answer_quality_judge(
    client: OpenAI, question: str, answer: str, reference: str
) -> float:
    if not answer.strip() or not reference.strip():
        return 0.0
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": _ANSWER_QUALITY_JUDGE_PROMPT.format(
                question=question[:300],
                reference=reference[:1500],
                answer=answer[:1500],
            )}],
            temperature=0,
            max_tokens=10,
            timeout=20,
        )
        return _parse_float(resp.choices[0].message.content)
    except Exception:
        return 0.0


def compute_answer_quality(
    samples: list[dict], client: OpenAI, emb_client: Any,
    skip_bertscore: bool = False
) -> list[dict]:
    ok = [s for s in samples if s["chatbot_ok"]]
    total = len(ok)

    # 1) LLM Judge
    print(f"  LLM Judge 계산 중 ({total}개)...")
    for i, s in enumerate(ok):
        ref = (s.get("golden_answer") or "") or s.get("reference") or ""
        print(f"  [{i+1:03d}/{total}] [{s['category']:10s}] {s['patent_id']} llm_judge...", flush=True)
        s["answer_quality_judge"] = _answer_quality_judge(
            client, s["question"], s["answer"], ref
        )

    # 2) Semantic Similarity
    print(f"\n  Semantic Similarity 계산 중 ({total}개)...")
    refs_for_sim = [(s.get("golden_answer") or "") or (s.get("reference") or "") for s in ok]
    valid_idx = [i for i, r in enumerate(refs_for_sim) if r.strip() and ok[i]["answer"].strip()]
    if valid_idx:
        texts = [ok[i]["answer"] for i in valid_idx] + [refs_for_sim[i] for i in valid_idx]
        vecs  = emb_client.embed_documents(texts)
        n = len(valid_idx)
        for j, vi in enumerate(valid_idx):
            a = np.array(vecs[j])
            r = np.array(vecs[j + n])
            cos = float(np.dot(a, r) / (np.linalg.norm(a) * np.linalg.norm(r) + 1e-9))
            ok[vi]["semantic_sim"] = round(cos, 4)

    for s in samples:
        s.setdefault("answer_quality_judge", 0.0)
        s.setdefault("semantic_sim", 0.0)

    # 3) BERTScore (선택)
    if skip_bertscore:
        for s in samples:
            s["bertscore_f1"] = None
        return samples

    print(f"\n  BERTScore F1 계산 중 ({total}개)...")
    try:
        from bert_score import score as bert_score_fn
        cands = [ok[i]["answer"]    for i in range(total)]
        refs  = [refs_for_sim[i]   for i in range(total)]
        valid = [(c, r) for c, r in zip(cands, refs) if c.strip() and r.strip()]
        if valid:
            c_list, r_list = zip(*valid)
            _, _, F1 = bert_score_fn(list(c_list), list(r_list), lang="ko",
                                     verbose=False, model_type="bert-base-multilingual-cased")
            vi = 0
            for i, s in enumerate(ok):
                if ok[i]["answer"].strip() and refs_for_sim[i].strip():
                    s["bertscore_f1"] = round(float(F1[vi]), 4)
                    vi += 1
                else:
                    s["bertscore_f1"] = None
    except Exception as e:
        print(f"  [BERTScore 오류] {e}")
        for s in ok:
            s["bertscore_f1"] = None

    for s in samples:
        s.setdefault("bertscore_f1", None)

    return samples


# ════════════════════════════════════════════════════════════════
# Phase 4 — Groundedness (LLM Judge)
# ════════════════════════════════════════════════════════════════
#
# LLM Judge (0~1):
#   답변의 각 주장이 검색된 컨텍스트에 의해 얼마나 뒷받침되는지 평가

_GROUNDEDNESS_JUDGE_PROMPT = """당신은 AI 답변의 근거성을 평가하는 전문가입니다.
주어진 컨텍스트를 기반으로, 챗봇 답변의 내용이 컨텍스트에 의해 얼마나 뒷받침되는지 0~1 점수로 평가하세요.

평가 기준:
- 1.0: 모든 주장이 컨텍스트에 명확히 근거함 (환각 없음)
- 0.7~0.9: 대부분 근거 있음, 일부 추론/일반화 포함
- 0.4~0.6: 절반 정도 근거 있음, 일부 컨텍스트 외 주장 포함
- 0.1~0.3: 대부분 컨텍스트 미지원 또는 사실 오류 포함
- 0.0: 컨텍스트와 무관하거나 완전한 환각

컨텍스트:
{context}

챗봇 답변: {answer}

점수만 반환하세요 (예: 0.82)."""


def _groundedness_judge(client: OpenAI, answer: str, contexts: list[str]) -> float:
    if not answer.strip() or not contexts:
        return 0.0
    context_text = "\n\n".join(c for c in contexts[:3] if c.strip())
    if not context_text.strip():
        return 0.0
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": _GROUNDEDNESS_JUDGE_PROMPT.format(
                context=context_text[:2000],
                answer=answer[:1500],
            )}],
            temperature=0,
            max_tokens=10,
            timeout=20,
        )
        return _parse_float(resp.choices[0].message.content)
    except Exception:
        return 0.0


def compute_groundedness(samples: list[dict], client: OpenAI) -> list[dict]:
    ok = [s for s in samples if s["chatbot_ok"]]
    total = len(ok)
    print(f"  {total}개 샘플 groundedness 판정 중...")
    for i, s in enumerate(ok):
        print(f"  [{i+1:03d}/{total}] [{s['category']:10s}] {s['patent_id']} groundedness...", flush=True)
        score = _groundedness_judge(client, s["answer"], s["contexts"])
        s["groundedness"]      = score
        s["hallucination_risk"] = round(1.0 - score, 4)

    for s in samples:
        s.setdefault("groundedness",      0.0)
        s.setdefault("hallucination_risk", 1.0)

    return samples


# ════════════════════════════════════════════════════════════════
# Phase 5 — Production 지표
# ════════════════════════════════════════════════════════════════

def compute_production(samples: list[dict]) -> dict:
    latencies     = [s["latency_sec"] for s in samples if s["chatbot_ok"]]
    source_counts = [s["source_count"] for s in samples if s["chatbot_ok"]]
    fallbacks     = [s for s in samples if s["chatbot_ok"] and s["source_count"] == 0]
    tok_in_total  = sum(s["tok_in_est"]  for s in samples if s["chatbot_ok"])
    tok_out_total = sum(s["tok_out_est"] for s in samples if s["chatbot_ok"])
    cost_est      = (tok_in_total  / 1000 * OPENAI_PRICE_PER_1K_IN +
                     tok_out_total / 1000 * OPENAI_PRICE_PER_1K_OUT)

    return {
        "total_queries":      len(samples),
        "successful_queries": len([s for s in samples if s["chatbot_ok"]]),
        "fallback_count":     len(fallbacks),
        "fallback_rate":      round(len(fallbacks) / max(len(samples), 1), 4),
        "latency_mean_sec":   round(float(np.mean(latencies)), 2) if latencies else 0,
        "latency_p50_sec":    round(float(np.percentile(latencies, 50)), 2) if latencies else 0,
        "latency_p95_sec":    round(float(np.percentile(latencies, 95)), 2) if latencies else 0,
        "source_count_mean":  round(float(np.mean(source_counts)), 2) if source_counts else 0,
        "source_count_min":   int(min(source_counts)) if source_counts else 0,
        "tokens_in_total":    tok_in_total,
        "tokens_out_total":   tok_out_total,
        "cost_usd_est":       round(cost_est, 4),
        "cost_per_query_usd": round(cost_est / max(len(samples), 1), 5),
    }


# ════════════════════════════════════════════════════════════════
# 요약 출력
# ════════════════════════════════════════════════════════════════

def print_summary(samples: list[dict], prod: dict, k: int) -> None:
    ok   = [s for s in samples if s["chatbot_ok"]]
    cats = ["overview", "claims", "market", "risk", "comparison", "evidence"]

    W = 72
    def section(title): print(f"\n{'='*W}\n  {title}\n{'='*W}")
    def bar(v, w=20):
        v = max(0.0, min(1.0, float(v)))
        return "█" * int(v * w) + "░" * (w - int(v * w))

    by_cat = defaultdict(list)
    by_pat = defaultdict(list)
    for s in ok:
        by_cat[s["category"]].append(s)
        by_pat[s["patent_id"]].append(s)

    # ── 1. Retrieval ──────────────────────────────────────────────
    section(f"1. RETRIEVAL  (K={k}, 0~1 높을수록 좋음)")
    for label, key in [
        (f"Hit@{k}           (정답 문서 포함 여부)",    "hit_at_k"),
        (f"Precision@{k}     (관련 청크 비율)",         "precision_at_k"),
        (f"MRR              (첫 관련 청크 순위역수)",   "mrr"),
        (f"nDCG@{k}          (순위 가중 품질)",         "ndcg_at_k"),
    ]:
        v = _avg(ok, key)
        print(f"  {label:46s}: {v:.4f}  [{bar(v)}]")

    print(f"\n  [ 카테고리별 Hit@{k} / Precision@{k} / MRR / nDCG@{k} ]")
    print(f"  {'카테고리':12s}  {'Hit':>6}  {'Prec':>6}  {'MRR':>6}  {'nDCG':>6}")
    print("  " + "-" * 46)
    for c in cats:
        rows = by_cat.get(c, [])
        h = _avg(rows, "hit_at_k")
        p = _avg(rows, "precision_at_k")
        m = _avg(rows, "mrr")
        n = _avg(rows, "ndcg_at_k")
        print(f"  {c:12s}  {h:6.4f}  {p:6.4f}  {m:6.4f}  {n:6.4f}")

    # ── 2. Answer Quality ─────────────────────────────────────────
    section("2. ANSWER QUALITY  (0~1 높을수록 좋음)")
    for label, key in [
        ("LLM Judge         (질문+레퍼런스 vs 답변, GPT-4.1)",   "answer_quality_judge"),
        ("Semantic Sim      (답변↔레퍼런스 임베딩 코사인)",        "semantic_sim"),
        ("BERTScore F1      (multilingual BERT 토큰 매칭)",        "bertscore_f1"),
    ]:
        vals = [s[key] for s in ok if isinstance(s.get(key), (int, float))]
        v = round(sum(vals) / len(vals), 4) if vals else None
        if v is None:
            print(f"  {label:52s}: N/A")
        else:
            print(f"  {label:52s}: {v:.4f}  [{bar(v)}]")

    print(f"\n  [ 카테고리별 LLM Judge / Semantic Sim ]")
    print(f"  {'카테고리':12s}  {'Judge':>7}  {'SemSim':>7}  {'BERTSc':>7}")
    print("  " + "-" * 42)
    for c in cats:
        rows = by_cat.get(c, [])
        j  = _avg(rows, "answer_quality_judge")
        ss = _avg(rows, "semantic_sim")
        bs_vals = [s["bertscore_f1"] for s in rows if isinstance(s.get("bertscore_f1"), float)]
        bs = round(sum(bs_vals) / len(bs_vals), 4) if bs_vals else None
        bs_str = f"{bs:7.4f}" if bs is not None else "    N/A"
        print(f"  {c:12s}  {j:7.4f}  {ss:7.4f}  {bs_str}")

    # ── 3. Groundedness ───────────────────────────────────────────
    section("3. GROUNDEDNESS / HALLUCINATION  (0~1 높을수록 좋음 — Groundedness만)")
    g_v  = _avg(ok, "groundedness")
    hr_v = _avg(ok, "hallucination_risk")
    print(f"  {'Groundedness      (LLM Judge — 컨텍스트 지지 정도)':52s}: {g_v:.4f}  [{bar(g_v)}]")
    print(f"  {'Hallucination Risk (1 - Groundedness)':52s}: {hr_v:.4f}  [{bar(hr_v)}]  ← 낮을수록 좋음")

    print(f"\n  [ 특허별 Groundedness / Hallucination Risk ]")
    print(f"  {'특허ID':15s}  {'Ground':>7}  {'HallRisk':>8}")
    print("  " + "-" * 35)
    for pid in sorted(by_pat):
        rows = by_pat[pid]
        g = _avg(rows, "groundedness")
        h = _avg(rows, "hallucination_risk")
        print(f"  {pid:15s}  {g:7.4f}  {h:8.4f}")

    # ── 4. Production ─────────────────────────────────────────────
    section("4. PRODUCTION METRICS")
    print(f"  총 쿼리:           {prod['total_queries']}개")
    print(f"  성공:              {prod['successful_queries']}개")
    print(f"  Fallback (소스0):  {prod['fallback_count']}개  ({prod['fallback_rate']*100:.1f}%)")
    print(f"  응답 지연 (평균):  {prod['latency_mean_sec']}s")
    print(f"  응답 지연 (P50):   {prod['latency_p50_sec']}s")
    print(f"  응답 지연 (P95):   {prod['latency_p95_sec']}s")
    print(f"  소스 청크 (평균):  {prod['source_count_mean']}개")
    print(f"  토큰 총합:         in={prod['tokens_in_total']:,}  out={prod['tokens_out_total']:,}")
    print(f"  비용 추정:         ${prod['cost_usd_est']:.4f}  (${prod['cost_per_query_usd']:.5f}/query)")

    # ── 하위 5개 ──────────────────────────────────────────────────
    section("하위 5개 — Groundedness 기준")
    worst = sorted(
        [s for s in ok if isinstance(s.get("groundedness"), float)],
        key=lambda s: s["groundedness"]
    )[:5]
    for s in worst:
        print(f"  [{s['patent_id']}][{s['category']:10s}]"
              f"  ground={s['groundedness']:.4f}"
              f"  judge={s.get('answer_quality_judge', 0):.4f}"
              f"  ndcg={s.get('ndcg_at_k', 0):.4f}")


# ════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patent-ids",     required=True)
    parser.add_argument("--top-k",          type=int, default=3)
    parser.add_argument("--skip-bertscore", action="store_true")
    parser.add_argument("--golden-qa",       type=str, default=None,
                        help="golden Q&A JSON 경로 (gen_golden_qa.py 출력)")
    parser.add_argument("--sample-per-pair", type=int, default=None,
                        help="(특허,카테고리)당 샘플 수 (기본: 전체)")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Retrieval 지표만 계산 (Answer Quality·Groundedness 건너뜀)")
    parser.add_argument("--output-dir",     type=Path,
                        default=Path("chatbot/data/artifacts/rag_eval"))
    args = parser.parse_args()

    patent_ids = [p.strip() for p in args.patent_ids.split(",")]
    client     = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # langchain_openai: subprocess 수집 완료 후 import (langgraph 버전 충돌 방지)
    from langchain_openai import OpenAIEmbeddings
    emb_client = OpenAIEmbeddings(model="text-embedding-3-large")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = args.output_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    golden_qa_path = args.golden_qa
    if golden_qa_path and not Path(golden_qa_path).exists():
        print(f"[WARN] --golden-qa '{golden_qa_path}' 파일 없음 — 기본 6개 질문으로 실행")
        golden_qa_path = None

    n_qa_label = "golden Q&A" if golden_qa_path else "고정 6개 질문"
    if golden_qa_path:
        raw_qa = json.loads(Path(golden_qa_path).read_text(encoding="utf-8"))
        pid_set = set(patent_ids)
        n_q = sum(1 for q in raw_qa if q["patent_id"] in pid_set)
    else:
        n_q = len(patent_ids) * 6

    print(f"\n{'='*72}")
    print(f"  SKIPA RAG 종합 성능 평가")
    print(f"  {len(patent_ids)}개 특허  |  {n_qa_label}  |  {n_q}개 쿼리  |  top-k={args.top_k}")
    print(f"  Retrieval · Answer Quality · Groundedness · Production")
    print(f"{'='*72}\n")

    # Phase 1
    print("[Phase 1/4] 챗봇 응답 수집")
    samples = collect_responses(patent_ids, args.top_k, golden_qa_path,
                                sample_per_pair=args.sample_per_pair,
                                retrieval_only=args.retrieval_only)
    n_ok    = sum(1 for s in samples if s["chatbot_ok"])
    print(f"  수집 완료: {len(samples)}개 (성공 {n_ok}개)")

    # Phase 2
    print(f"\n[Phase 2/4] Retrieval 지표 — LLM chunk relevance (K={args.top_k})")
    samples = compute_retrieval(samples, client, k=args.top_k)

    # Phase 3
    if args.retrieval_only:
        print(f"\n[Phase 3/4] Answer Quality — 건너뜀 (--retrieval-only)")
        for s in samples:
            s.setdefault("answer_quality_judge", None)
            s.setdefault("semantic_sim", None)
            s.setdefault("bertscore_f1", None)
    else:
        print(f"\n[Phase 3/4] Answer Quality — LLM Judge + Semantic Sim")
        samples = compute_answer_quality(samples, client, emb_client,
                                         skip_bertscore=args.skip_bertscore)

    # Phase 4
    if args.retrieval_only:
        print(f"\n[Phase 4/4] Groundedness — 건너뜀 (--retrieval-only)")
        for s in samples:
            s.setdefault("groundedness", None)
            s.setdefault("hallucination_risk", None)
    else:
        print(f"\n[Phase 4/4] Groundedness — LLM Judge")
        samples = compute_groundedness(samples, client)

    # Production
    prod = compute_production(samples)

    # 출력
    print_summary(samples, prod, k=args.top_k)

    # 저장
    out = {
        "timestamp":      timestamp,
        "patent_ids":     patent_ids,
        "top_k":          args.top_k,
        "golden_qa_path": golden_qa_path,
        "production":     prod,
        "metrics_description": {
            "hit_at_k":              f"Recall@{args.top_k} proxy — 관련 청크가 상위 {args.top_k}에 1개 이상",
            "precision_at_k":        f"Precision@{args.top_k} — 상위 {args.top_k} 청크 중 관련 비율",
            "mrr":                   "Mean Reciprocal Rank — 첫 관련 청크 순위 역수의 평균",
            "ndcg_at_k":             f"nDCG@{args.top_k} — 순위 반영 정규화 누적 이득",
            "answer_quality_judge":  "LLM Judge (GPT-4.1) — 질문+레퍼런스 vs 챗봇 답변 정확성 (0~1)",
            "semantic_sim":          "OpenAI text-embedding-3-large — 답변 vs 레퍼런스 코사인 유사도",
            "bertscore_f1":          "BERTScore F1 — bert-base-multilingual-cased 기반 토큰 매칭",
            "groundedness":          "LLM Judge (GPT-4.1) — 컨텍스트 기반 답변 근거성 (0~1)",
            "hallucination_risk":    "1 - Groundedness — 환각/미지원 주장 위험도",
        },
        "samples": samples,
    }
    out_file = out_dir / "results.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n\n결과 저장: {out_dir}")


if __name__ == "__main__":
    main()
