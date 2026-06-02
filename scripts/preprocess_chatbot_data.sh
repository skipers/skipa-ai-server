#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f "chatbot/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "chatbot/.venv/bin/activate"
fi

python3 scripts/preprocess_chatbot_data.py "$@"
