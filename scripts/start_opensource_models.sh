#!/usr/bin/env bash
# Start all three AI model servers for opensource mode.
#
# Usage:
#   scripts/start_opensource_models.sh [llm|embedding|reranker|all] [--cpu]
#
# LLM 실행 방식:
#   기본값 (--cpu)  : llama-cpp-python (GGUF, CPU/Metal) - 모든 환경에서 동작
#   --mlx           : mlx_lm.server (Apple Silicon 전용)
#
# Ports:
#   LLM       -> 8000
#   Embedding -> 8001  (scripts/serve_embedding.py)
#   Reranker  -> 8003  (scripts/serve_reranker.py)
#
# Quantization 선택 (CPU 모드):
#   LLM_QUANT=Q3_K_M  → 16.4 GB RAM (32GB 서버)
#   LLM_QUANT=Q4_K_M  → 22.0 GB RAM (32GB+ 서버) [기본값]
#
# GPU layers (CPU 모드):
#   LLM_GPU_LAYERS=0   → 순수 CPU (기본값)
#   LLM_GPU_LAYERS=99  → 전체 Metal 오프로드 (Mac)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# parse args
TARGET="all"
LLM_BACKEND="cpu"
for arg in "$@"; do
  case "$arg" in
    --cpu) LLM_BACKEND="cpu" ;;
    --mlx) LLM_BACKEND="mlx" ;;
    llm|embedding|reranker|all) TARGET="$arg" ;;
  esac
done

EMBEDDING_MODEL="${OPEN_SOURCE_EMBEDDING_MODEL:-Qwen/Qwen3-Embedding-4B}"
RERANKER_MODEL="${OPEN_SOURCE_RERANKER_MODEL:-Qwen/Qwen3-Reranker-4B}"
LLM_QUANT="${LLM_QUANT:-Q4_K_M}"
LLM_CPU_MODEL="${OPEN_SOURCE_LLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
LLM_MLX_MODEL="${OPEN_SOURCE_LLM_MODEL:-mlx-community/Qwen3.5-35B-A3B-4bit}"

LLM_PORT=8000
EMBEDDING_PORT=8001
RERANKER_PORT=8003

LOG_DIR="${ROOT}/logs/ai_models"
mkdir -p "$LOG_DIR"

start_llm() {
  if [[ "$LLM_BACKEND" == "mlx" ]]; then
    echo "▶ LLM (mlx): ${LLM_MLX_MODEL} -> :${LLM_PORT}"
    mlx_lm.server \
      --model "$LLM_MLX_MODEL" \
      --port "$LLM_PORT" \
      --host 0.0.0.0 \
      --trust-remote-code \
      > "${LOG_DIR}/llm.log" 2>&1 &
    echo "  PID=$! | tail -f ${LOG_DIR}/llm.log"
  else
    echo "▶ LLM (cpu/transformers): ${LLM_CPU_MODEL} -> :${LLM_PORT}"
    python3 "${ROOT}/scripts/serve_llm_cpu.py" \
      --model "$LLM_CPU_MODEL" \
      --port "$LLM_PORT" \
      --host 0.0.0.0 \
      > "${LOG_DIR}/llm.log" 2>&1 &
    echo "  PID=$! | tail -f ${LOG_DIR}/llm.log"
  fi
}

start_embedding() {
  echo "▶ Embedding: ${EMBEDDING_MODEL} -> :${EMBEDDING_PORT}"
  python3 "${ROOT}/scripts/serve_embedding.py" \
    --model "$EMBEDDING_MODEL" \
    --port "$EMBEDDING_PORT" \
    > "${LOG_DIR}/embedding.log" 2>&1 &
  echo "  PID=$! | tail -f ${LOG_DIR}/embedding.log"
}

start_reranker() {
  echo "▶ Reranker: ${RERANKER_MODEL} -> :${RERANKER_PORT}"
  python3 "${ROOT}/scripts/serve_reranker.py" \
    --model "$RERANKER_MODEL" \
    --port "$RERANKER_PORT" \
    > "${LOG_DIR}/reranker.log" 2>&1 &
  echo "  PID=$! | tail -f ${LOG_DIR}/reranker.log"
}

case "$TARGET" in
  llm)       start_llm ;;
  embedding) start_embedding ;;
  reranker)  start_reranker ;;
  all)
    start_llm
    start_embedding
    start_reranker
    echo ""
    echo "모든 모델 서버 시작됨. 로그:"
    echo "  tail -f ${LOG_DIR}/llm.log"
    echo "  tail -f ${LOG_DIR}/embedding.log"
    echo "  tail -f ${LOG_DIR}/reranker.log"
    echo ""
    echo "헬스체크:"
    echo "  curl http://127.0.0.1:${LLM_PORT}/v1/models"
    echo "  curl http://127.0.0.1:${EMBEDDING_PORT}/health"
    echo "  curl http://127.0.0.1:${RERANKER_PORT}/health"
    ;;
  *)
    echo "Usage: $0 [llm|embedding|reranker|all] [--cpu|--mlx]" >&2
    exit 1
    ;;
esac
