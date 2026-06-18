#!/usr/bin/env bash
# Download a GGUF LLM model from HuggingFace for CPU serving.
#
# Usage:
#   scripts/download_llm_gguf.sh [quantization]
#
# quantization options (Qwen3.5-35B-A3B):
#   Q3_K_M  - 16.4 GB  → RAM 32GB 이상
#   Q4_K_M  - 22.0 GB  → RAM 32GB+ (기본값, 품질 최적)
#   Q4_K_S  - 20.7 GB  → RAM 32GB+
#   Q5_K_M  - ~27 GB   → RAM 64GB 이상
#
# 모델 저장 위치: ./models/llm/
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUANT="${1:-Q4_K_M}"
REPO="unsloth/Qwen3.5-35B-A3B-GGUF"
FILENAME="Qwen3.5-35B-A3B-${QUANT}.gguf"
DEST_DIR="${ROOT}/models/llm"
DEST="${DEST_DIR}/${FILENAME}"

mkdir -p "$DEST_DIR"

if [[ -f "$DEST" ]]; then
    echo "이미 존재: $DEST"
    exit 0
fi

echo "다운로드: ${REPO}/${FILENAME}"
echo "저장 위치: ${DEST}"

python3 -c "
from huggingface_hub import hf_hub_download
import os
path = hf_hub_download(
    repo_id='${REPO}',
    filename='${FILENAME}',
    local_dir='${DEST_DIR}',
)
print('완료:', path)
"