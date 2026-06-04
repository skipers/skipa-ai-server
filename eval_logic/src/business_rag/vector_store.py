"""
FAISS 기반 벡터 스토어.

개선 사항:
  - embed_text 필드 활용: 메타데이터 프리픽스가 포함된 텍스트로 임베딩
  - BM25 병렬 인덱스: 정확 키워드 매칭을 위한 희소(sparse) 검색 추가
  - RRF (Reciprocal Rank Fusion): 밀집·희소 검색 결과를 순위 기반 병합
  - MMR (Maximal Marginal Relevance): 중복 청크 제거, 검색 결과 다양성 확보
"""
import json
import pickle
import re
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi

from .config import (
    OPENAI_API_KEY, EMBEDDING_MODEL,
    INDEX_DIR, PROCESSED_DIR, TOP_K,
    CANDIDATE_K_MULTIPLIER, MMR_LAMBDA,
)

_client = OpenAI(api_key=OPENAI_API_KEY)

INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE  = INDEX_DIR / "metadata.pkl"
BM25_FILE  = INDEX_DIR / "bm25.pkl"


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _embed(texts: list[str], batch_size: int = 100) -> np.ndarray:
    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = _client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_vectors.extend([d.embedding for d in resp.data])
    return np.array(all_vectors, dtype="float32")


def _tokenize_ko(text: str) -> list[str]:
    """한국어 친화적 토크나이저: 특수문자 제거 후 공백 분리."""
    text = re.sub(r"[^\w\s가-힣]", " ", text.lower())
    return [t for t in text.split() if t]


# ── RRF ───────────────────────────────────────────────────────────────────────

def _rrf_merge(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """
    Reciprocal Rank Fusion.
    여러 랭킹 리스트를 순위 역수 합산으로 병합.
    k=60은 표준 하이퍼파라미터 (Robertson & Zaragoza, 2009).
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── MMR ───────────────────────────────────────────────────────────────────────

def _mmr_select(
    query_vec: np.ndarray,
    cand_vecs: np.ndarray,
    relevance_scores: list[float],
    top_k: int,
    lambda_: float = MMR_LAMBDA,
) -> list[int]:
    """
    Maximal Marginal Relevance.
    λ·관련성 - (1-λ)·이미_선택된_결과와의_최대_유사도 를 최대화하는 순서로 선택.
    lambda_가 높을수록 관련성 우선, 낮을수록 다양성 우선.
    """
    selected: list[int] = []
    candidates = list(range(len(cand_vecs)))

    while len(selected) < top_k and candidates:
        if not selected:
            best = max(candidates, key=lambda i: relevance_scores[i])
        else:
            sel_vecs = cand_vecs[selected]

            def _mmr_score(i: int) -> float:
                rel = relevance_scores[i]
                redundancy = float(np.max(cand_vecs[i] @ sel_vecs.T))
                return lambda_ * rel - (1 - lambda_) * redundancy

            best = max(candidates, key=_mmr_score)

        selected.append(best)
        candidates.remove(best)

    return selected


# ── 인덱스 빌드 / 로드 ────────────────────────────────────────────────────────

def build_index(chunks: list[dict]) -> faiss.Index:
    """청크 리스트로 FAISS + BM25 인덱스 생성 후 디스크 저장."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # embed_text가 있으면 메타데이터 프리픽스 포함 텍스트로 임베딩
    embed_texts = [c.get("embed_text") or c["text"] for c in chunks]
    print(f"임베딩 생성 중... ({len(embed_texts)}개)")
    vectors = _embed(embed_texts)

    # FAISS (코사인 유사도)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vectors)
    index.add(vectors)
    faiss.write_index(index, str(INDEX_FILE))

    # BM25 (희소 키워드 검색)
    tokenized = [_tokenize_ko(t) for t in embed_texts]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_FILE, "wb") as f:
        pickle.dump(bm25, f)

    with open(META_FILE, "wb") as f:
        pickle.dump(chunks, f)

    print(f"FAISS 인덱스 저장 → {INDEX_FILE} ({index.ntotal}개 벡터)")
    print(f"BM25 인덱스 저장  → {BM25_FILE}")
    return index


def load_index() -> tuple[faiss.Index, list[dict], BM25Okapi | None]:
    if not INDEX_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            "FAISS 인덱스가 없습니다. 먼저 build_index()를 실행하세요."
        )
    index = faiss.read_index(str(INDEX_FILE))
    with open(META_FILE, "rb") as f:
        chunks = pickle.load(f)

    bm25 = None
    if BM25_FILE.exists():
        with open(BM25_FILE, "rb") as f:
            bm25 = pickle.load(f)

    return index, chunks, bm25


# ── 검색 ──────────────────────────────────────────────────────────────────────

def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    하이브리드 검색 파이프라인.

    1. Dense 검색 (FAISS cosine)
    2. Sparse 검색 (BM25) — BM25 인덱스가 있을 때만
    3. RRF로 두 결과 병합
    4. MMR로 중복 제거 후 top_k 반환
    """
    index, chunks, bm25 = load_index()
    candidate_k = min(top_k * CANDIDATE_K_MULTIPLIER, index.ntotal)

    # 1. Dense 검색
    q_vec = _embed([query])
    faiss.normalize_L2(q_vec)
    scores, indices = index.search(q_vec, candidate_k)

    dense_ranking   = [int(idx) for idx in indices[0] if idx != -1]
    dense_score_map = {int(idx): float(sc) for idx, sc in zip(indices[0], scores[0]) if idx != -1}

    # 2. BM25 검색 + RRF 병합
    if bm25 is not None:
        query_tokens  = _tokenize_ko(query)
        bm25_arr      = bm25.get_scores(query_tokens)
        bm25_ranking  = np.argsort(bm25_arr)[::-1][:candidate_k].tolist()
        rrf_ranked    = _rrf_merge([dense_ranking, bm25_ranking])
        candidate_ids = [idx for idx, _ in rrf_ranked[:candidate_k]]
    else:
        candidate_ids = dense_ranking[:candidate_k]

    # 3. MMR 다양성 선택
    if len(candidate_ids) > top_k:
        cand_vecs  = np.array([index.reconstruct(i) for i in candidate_ids], dtype="float32")
        rel_scores = [dense_score_map.get(i, 0.0) for i in candidate_ids]
        selected   = _mmr_select(q_vec[0], cand_vecs, rel_scores, top_k)
        final_ids  = [candidate_ids[i] for i in selected]
    else:
        final_ids = candidate_ids[:top_k]

    results = []
    for idx in final_ids:
        chunk = dict(chunks[idx])
        chunk["score"] = dense_score_map.get(idx, 0.0)
        results.append(chunk)

    return results


if __name__ == "__main__":
    chunks_path = PROCESSED_DIR / "chunks.json"
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    build_index(chunks)
