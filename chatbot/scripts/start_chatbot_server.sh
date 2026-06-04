#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${ROOT_DIR}/chatbot/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8001}"
export INTENT_LLM_TIMEOUT="${INTENT_LLM_TIMEOUT:-30}"
export ANSWER_LLM_TIMEOUT="${ANSWER_LLM_TIMEOUT:-120}"
export ANSWER_NUM_PREDICT="${ANSWER_NUM_PREDICT:-900}"
export PYTHONPATH="${PYTHONPATH:-$ROOT_DIR}"

echo "Starting SKIPA chatbot API/UI at http://${HOST}:${PORT}/ui"
echo "Intent timeout: ${INTENT_LLM_TIMEOUT}s, answer timeout: ${ANSWER_LLM_TIMEOUT}s"

exec "$PYTHON_BIN" -m uvicorn chatbot.app.main:app --host "$HOST" --port "$PORT"
