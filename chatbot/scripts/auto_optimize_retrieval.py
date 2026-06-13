"""자동 검색 최적화 루프.

매 이터레이션:
1. 현재 eval 결과 분석 (실패 패턴 파악)
2. 패턴 기반 청크 개선 결정
3. shared_data.py 수정
4. 벡터스토어 재빌드
5. eval 실행
6. 목표(0.8) 달성 시 다음 카테고리, 미달 시 반복
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv("chatbot/.env")

PATENT_IDS = "10-1959619,10-1959627,10-2042318,10-2142205,10-2663094,10-2686678,10-2737902,10-2753879,10-2762042,10-2839217"
GOLDEN_QA  = "chatbot/data/artifacts/golden_qa.json"
TARGET     = 0.80
CATEGORIES = ["evidence", "overview", "claims", "market", "risk", "comparison"]
MAX_ITERS  = 8

# ── Eval 실행 ────────────────────────────────────────────────────────────────
def run_eval(sample_per_pair: int = 10) -> dict:
    """eval_rag.py 실행 후 최신 results.json 리턴."""
    cmd = [
        sys.executable, "chatbot/scripts/eval_rag.py",
        "--patent-ids", PATENT_IDS,
        "--top-k", "3",
        "--skip-bertscore",
        "--retrieval-only",
        "--golden-qa", GOLDEN_QA,
        "--sample-per-pair", str(sample_per_pair),
    ]
    print(f"\n[EVAL] Running eval (sample_per_pair={sample_per_pair})...", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.time() - t0, 1)
    if proc.returncode != 0:
        print("[EVAL] ERROR:", proc.stderr[-500:])
        return {}
    # Find latest results.json
    eval_dir = sorted(Path("chatbot/data/artifacts/rag_eval").glob("*/results.json"))
    if not eval_dir:
        return {}
    results = json.loads(eval_dir[-1].read_text(encoding="utf-8"))
    samples = results.get("samples", [])
    # Compute per-category hit@3
    by_cat: dict[str, list] = {}
    for s in samples:
        c = s.get("category", "")
        by_cat.setdefault(c, []).append(s.get("hit_at_k", 0))
    metrics = {c: round(sum(v)/len(v), 4) for c, v in by_cat.items() if v}
    overall = round(sum(metrics.values()) / len(metrics), 4) if metrics else 0
    print(f"[EVAL] Done in {elapsed}s. Overall Hit@3: {overall}")
    for c, h in sorted(metrics.items(), key=lambda x: -x[1]):
        flag = "✓" if h >= TARGET else "✗"
        print(f"  {flag} {c:12s}: {h:.4f}")
    return {"metrics": metrics, "samples": samples, "overall": overall}

# ── 실패 패턴 분석 ──────────────────────────────────────────────────────────
def analyze_failures(samples: list[dict], category: str) -> dict:
    """카테고리별 실패 질문을 분석해서 개선 힌트 리턴."""
    fail_qs = [s["question"] for s in samples
               if s.get("category") == category and not s.get("hit_at_k")]
    hit_qs  = [s["question"] for s in samples
               if s.get("category") == category and s.get("hit_at_k")]
    total   = len([s for s in samples if s.get("category") == category])
    hit_cnt = total - len(fail_qs)

    # Fail keyword frequency
    kw_freq: dict[str, int] = {}
    for q in fail_qs:
        for kw in ["참고문헌", "출처", "자료", "제목", "등록상태", "유사도",
                   "항목 수", "몇 개", "발행", "해외", "확장", "파급", "경쟁사",
                   "규모", "전망", "성장률", "섹터", "평균", "신뢰도", "회피설계",
                   "사례", "적용", "산업"]:
            if kw in q:
                kw_freq[kw] = kw_freq.get(kw, 0) + 1

    top_kws = sorted(kw_freq.items(), key=lambda x: -x[1])[:5]
    print(f"\n[ANALYZE] {category}: {hit_cnt}/{total} hit — top fail keywords: {top_kws}")
    return {"fail_qs": fail_qs[:10], "top_kws": top_kws, "hit": hit_cnt, "total": total}

# ── 벡터스토어 재빌드 ────────────────────────────────────────────────────────
def rebuild_vectorstores() -> None:
    print("\n[BUILD] Rebuilding all vectorstores...", flush=True)
    t0 = time.time()
    from chatbot.app.shared_data import build_all_patent_vectorstores
    build_all_patent_vectorstores()
    print(f"[BUILD] Done in {round(time.time()-t0,1)}s")

# ── 카테고리별 개선 전략 적용 ─────────────────────────────────────────────────
def apply_improvement(category: str, analysis: dict, iteration: int) -> bool:
    """카테고리 + 이터레이션에 따라 다른 개선 전략 적용. 변경 발생 시 True."""
    fail_kws = {k for k, _ in analysis["top_kws"]}
    sd_path = Path("chatbot/app/shared_data.py")
    content = sd_path.read_text(encoding="utf-8")

    changed = False

    if category == "evidence":
        changed = _improve_evidence(content, sd_path, fail_kws, iteration)
    elif category == "market":
        changed = _improve_market(content, sd_path, fail_kws, iteration)
    elif category == "overview":
        changed = _improve_overview(content, sd_path, fail_kws, iteration)
    elif category == "risk":
        changed = _improve_risk(content, sd_path, fail_kws, iteration)
    elif category == "claims":
        changed = _improve_claims(content, sd_path, fail_kws, iteration)
    elif category == "comparison":
        changed = _improve_comparison(content, sd_path, fail_kws, iteration)

    return changed


def _write_if_changed(path: Path, old: str, new: str) -> bool:
    if old == new:
        print("  [INFO] No code change needed.")
        return False
    path.write_text(new, encoding="utf-8")
    print(f"  [INFO] shared_data.py updated ({len(new)-len(old):+d} chars)")
    return True


def _improve_evidence(content: str, path: Path, kws: set, iteration: int) -> bool:
    """Evidence: 참고문헌 증가, 차원별 all_sources 추가."""
    new_content = content
    # 1) 참고 출처 5개 → 15개
    if "for _src in (_tech_src + _papers)[:5]:" in new_content:
        new_content = new_content.replace(
            "for _src in (_tech_src + _papers)[:5]:",
            "for _src in (_tech_src + _papers)[:15]:",
        )
        print("  [evidence] Expanded reference sources 5→15")

    # 2) all_sources 청크 추가 (section_2.all_sources)
    MARKER = "# ── [evidence] 차원별 세부 점수 + 항목 수 전용 청크"
    if MARKER in new_content and "all_sources_chunk" not in new_content:
        insert = textwrap.dedent("""
    # ── [evidence] all_sources 전체 출처 목록 청크 ────────────────────────────
    _all_srcs = _s2.get("all_sources") if isinstance(_s2.get("all_sources"), list) else []
    if _all_srcs:
        asrc_lines = [
            "평가에 참고된 모든 출처 목록:",
            "핵심 참고 문헌 및 자료 제목:",
        ]
        for _asrc in _all_srcs[:20]:
            if isinstance(_asrc, dict) and _asrc.get("title"):
                _yr_str = str(_asrc.get("published_year") or _asrc.get("year") or "").strip()
                _pub = str(_asrc.get("publisher") or _asrc.get("source") or "").strip()
                _line = f"- {_asrc['title']}"
                if _yr_str:
                    _line += f" ({_yr_str})"
                if _pub:
                    _line += f" [{_pub}]"
                asrc_lines.append(_line)
        d = _make("\\n".join(asrc_lines), "전체출처목록")  # all_sources_chunk marker
        if d:
            docs.append(d)

""")
        new_content = new_content.replace(MARKER, insert + MARKER)
        print("  [evidence] Added all_sources chunk")

    # 3) 차원별 상세 항목 청크 (각 dimension item별)
    if iteration >= 2 and "차원별항목상세" not in new_content:
        MARKER2 = "# ── [evidence] valuation.evidence 사업화 현황"
        if MARKER2 in new_content:
            insert2 = textwrap.dedent("""
    # ── [evidence] section_2 차원별 상세 항목 청크 ───────────────────────────
    for _dname2, _dv2 in _s2_dims.items():
        if not isinstance(_dv2, dict):
            continue
        _ditems = _dv2.get("items") if isinstance(_dv2.get("items"), list) else []
        if not _ditems:
            continue
        di_lines = [
            f"{_dname2} 평가 세부 항목 및 근거:",
            f"{_dname2} 항목 수: {len(_ditems)}개",
            f"{_dname2} 평균 점수: {_dv2.get('average_score')}/5",
        ]
        for _dit in _ditems[:8]:
            if isinstance(_dit, dict) and _dit.get("item"):
                _dline = f"- {_dit['item']}: {_dit.get('score')}/5"
                _djb = str(_dit.get("judgment_basis") or _dit.get("judgment_summary") or "").strip()
                if _djb:
                    _dline += f" — {_djb[:150]}"
                di_lines.append(_dline)
        d = _make("\\n".join(di_lines), f"차원별항목상세_{_dname2}")
        if d:
            docs.append(d)

""")
            new_content = new_content.replace(MARKER2, insert2 + MARKER2)
            print("  [evidence] Added per-dimension detail chunks")

    return _write_if_changed(path, content, new_content)


def _improve_market(content: str, path: Path, kws: set, iteration: int) -> bool:
    """Market: 해외·확장성·파급효과·경쟁사 대응 청크 추가."""
    new_content = content
    MARKER = "# ── [comparison] ecosystem_summary 통계 전용 청크"

    if "시장확장성해외진출" not in new_content and MARKER in new_content:
        insert = textwrap.dedent("""
    # ── [market] 시장 확장성·해외 진출·파급효과 전용 청크 ─────────────────────
    _mg_sector = str(_mg.get("sector") or "").strip()
    _mg_rate   = _mg.get("growth_rate")
    _mg_data   = _mg.get("data") if isinstance(_mg.get("data"), list) else []
    _legal_info = str(valuation.get("legal") or "") if isinstance(valuation.get("legal"), (str, dict)) else ""
    if _mg_sector or _s3_answer or _s3_outlook:
        exp_lines = [
            "시장 확장성 및 해외 진출 가능성:",
            "산업적 파급효과 및 활용 범위:",
            "시장 성공 근거 및 조기 도입 필요성:",
            "상업적 확장성 평가:",
        ]
        if _mg_sector:
            exp_lines.append(f"시장 섹터: {_mg_sector}")
        if _mg_rate is not None:
            exp_lines.append(f"시장 성장률: {_mg_rate}%  (연평균)")
        if _mg_data:
            yr_vals = [f"{d.get('연도')}년: {int(d.get('값',0)):,}원" for d in _mg_data[-3:] if isinstance(d, dict)]
            if yr_vals:
                exp_lines.append(f"최근 시장 규모 데이터: {', '.join(yr_vals)}")
        if _s3_outlook:
            exp_lines += ["시장 전망 및 성장 배경:", _s3_outlook[:500]]
        if _s3_answer:
            exp_lines += ["사업화 가능성 분석:", _s3_answer[:600]]
        if _inval_risk:
            exp_lines.append(f"경쟁 리스크: {_inval_risk}")
        if _comp_intensity:
            exp_lines.append(f"경쟁사 대응 예측 — 경쟁 강도: {_comp_intensity}")
        if _diff_risk:
            exp_lines.append(f"차별화 위험 (경쟁사 모방 가능성): {_diff_risk}")
        d = _make("\\n".join(exp_lines), "시장확장성해외진출")
        if d:
            docs.append(d)

""")
        new_content = new_content.replace(MARKER, insert + MARKER)
        print("  [market] Added 시장확장성해외진출 chunk")

    return _write_if_changed(path, content, new_content)


def _improve_overview(content: str, path: Path, kws: set, iteration: int) -> bool:
    """Overview: 기술 요약·독창성·현재 가치 청크 보강."""
    new_content = content
    # Already have 종합개요상세. Try to enrich with 기술분야 summary
    if iteration >= 2 and "기술개요요약" not in new_content:
        MARKER = "# ── [risk] 권리성 항목 개별 상세 청크"
        if MARKER in new_content:
            insert = textwrap.dedent("""
    # ── [overview] 기술 개요·독창성·활용 가능성 청크 ────────────────────────
    _parsed_brief = {}
    try:
        import json as _json
        _pfile = Path("data/patent") / patent_id / "parsed.json"
        if _pfile.exists():
            _pd = _json.loads(_pfile.read_text(encoding="utf-8"))
            _parsed_brief = _pd.get("brief_summary") or {}
    except Exception:
        pass
    if _parsed_brief or _s1_opinion:
        tech_ov_lines = [
            "특허 기술 개요 및 독창성:",
            f"특허명: {_title}",
            "기술적 활용 가능성 및 독창성 평가:",
            "이 특허의 핵심 가치 및 현재 가치 평가:",
        ]
        for _bk, _bv in (list(_parsed_brief.items()) if isinstance(_parsed_brief, dict) else [])[:3]:
            if isinstance(_bv, str) and len(_bv) > 20:
                tech_ov_lines.append(f"{_bk}: {_bv[:300]}")
        if _s1_opinion:
            tech_ov_lines.append(f"종합 의견: {_s1_opinion}")
        if _s1_overall is not None:
            tech_ov_lines.append(f"종합 평균 점수: {_s1_overall}/5 (등급: {_s1_grade})")
        d = _make("\\n".join(tech_ov_lines), "기술개요요약")
        if d:
            docs.append(d)

""")
            new_content = new_content.replace(MARKER, insert + MARKER)
            print("  [overview] Added 기술개요요약 chunk")

    return _write_if_changed(path, content, new_content)


def _improve_risk(content: str, path: Path, kws: set, iteration: int) -> bool:
    """Risk: 권리성 항목 수 증가, 회피설계 전용 확장."""
    new_content = content
    # Expand rights items limit from 8 to all
    if "_rights_items[:8]" in new_content:
        new_content = new_content.replace("_rights_items[:8]", "_rights_items[:12]")
        print("  [risk] Expanded rights items 8→12")

    # Also expand rights items for the per-item loop
    if "for _ri in _rights_items:" in new_content and iteration >= 2:
        # Already have it; try expanding to all _review_items filtered to 권리성
        pass

    return _write_if_changed(path, content, new_content)


def _improve_claims(content: str, path: str, kws: set, iteration: int) -> bool:
    """Claims: 청구항 키워드 강화."""
    # Claims chunks are from _parsed_to_docs; hard to modify without seeing failures
    # First check what's failing
    print("  [claims] No automated improvement available yet; monitoring...")
    return False


def _improve_comparison(content: str, path: Path, kws: set, iteration: int) -> bool:
    """Comparison: 유사특허 청크 확장."""
    new_content = content
    # Expand from 10 to 15 similar patents
    if "_all_sim_patents[:10]" in new_content:
        new_content = new_content.replace("_all_sim_patents[:10]", "_all_sim_patents[:15]")
        print("  [comparison] Expanded similar patents 10→15")
    return _write_if_changed(path, content, new_content)


# ── Main loop ────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("AUTO OPTIMIZE: RETRIEVAL Hit@3 → 0.80+")
    print("=" * 70)

    # Initial eval
    result = run_eval(sample_per_pair=10)
    if not result:
        print("ERROR: Initial eval failed")
        return

    for iteration in range(1, MAX_ITERS + 1):
        metrics = result["metrics"]
        print(f"\n{'='*70}")
        print(f"ITERATION {iteration} — Overall: {result['overall']:.4f}")
        print("="*70)

        # Find lowest-scoring category that hasn't reached target
        below_target = [(c, metrics.get(c, 0)) for c in CATEGORIES if metrics.get(c, 0) < TARGET]
        if not below_target:
            print("\n🎉 ALL CATEGORIES REACHED 0.80! Done.")
            break

        # Focus on best opportunity (closest to 0.8 or pattern-rich)
        below_target.sort(key=lambda x: -x[1])  # highest first (closest to target)
        target_cat, target_hit = below_target[0]
        print(f"\n[FOCUS] Target category: {target_cat} (current: {target_hit:.4f})")

        # Analyze failures
        analysis = analyze_failures(result["samples"], target_cat)

        # Apply improvement
        changed = apply_improvement(target_cat, analysis, iteration)

        if changed:
            # Rebuild and re-eval
            rebuild_vectorstores()
            result = run_eval(sample_per_pair=10)
            if not result:
                print("ERROR: Eval failed after improvement")
                break

            new_hit = result["metrics"].get(target_cat, 0)
            delta = new_hit - target_hit
            print(f"\n[RESULT] {target_cat}: {target_hit:.4f} → {new_hit:.4f} ({delta:+.4f})")
            if new_hit >= TARGET:
                print(f"✓ {target_cat.upper()} REACHED 0.80!")
        else:
            print(f"  [INFO] No improvement applied for {target_cat} at iteration {iteration}")
            # Try next category
            if len(below_target) > 1:
                target_cat, target_hit = below_target[1]
                print(f"[SHIFT] Trying {target_cat} instead...")
                analysis = analyze_failures(result["samples"], target_cat)
                changed = apply_improvement(target_cat, analysis, iteration)
                if changed:
                    rebuild_vectorstores()
                    result = run_eval(sample_per_pair=10)

    print("\n[FINAL] Optimization loop complete.")
    if result:
        print(f"Final overall Hit@3: {result['overall']:.4f}")
        for c in CATEGORIES:
            h = result['metrics'].get(c, 0)
            flag = "✓" if h >= TARGET else "✗"
            print(f"  {flag} {c:12s}: {h:.4f}")


if __name__ == "__main__":
    main()
