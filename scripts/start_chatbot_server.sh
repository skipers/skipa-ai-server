#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f "chatbot/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "chatbot/.venv/bin/activate"
fi

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8001}"
export INTENT_LLM_TIMEOUT="${INTENT_LLM_TIMEOUT:-30}"
export ANSWER_LLM_TIMEOUT="${ANSWER_LLM_TIMEOUT:-120}"
export ANSWER_NUM_PREDICT="${ANSWER_NUM_PREDICT:-900}"

echo "Starting SKIPA chatbot API/UI at http://${HOST}:${PORT}/ui"
echo "Intent timeout: ${INTENT_LLM_TIMEOUT}s, answer timeout: ${ANSWER_LLM_TIMEOUT}s"

exec uvicorn chatbot.app.main:app --host "$HOST" --port "$PORT"
