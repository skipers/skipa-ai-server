#!/usr/bin/env bash
set -euo pipefail

service="${APP_SERVICE:-chatbot}"
if [ "$#" -gt 0 ]; then
  service="$1"
  shift
fi

case "$service" in
  chatbot)
    exec python -m uvicorn chatbot.app.main:app \
      --host "${HOST:-0.0.0.0}" \
      --port "${PORT:-8001}" \
      "$@"
    ;;
  eval-logic|eval_logic|eval)
    cd /app/eval_logic
    exec python -m uvicorn apps.api.main:app \
      --host "${HOST:-0.0.0.0}" \
      --port "${PORT:-8000}" \
      --app-dir /app/eval_logic/src \
      "$@"
    ;;
  nightly-reindex|reindex-once)
    exec python /app/chatbot/scripts/preprocess_chatbot_data.py --mode nightly-reindex "$@"
    ;;
  bash|sh|python|uvicorn)
    exec "$service" "$@"
    ;;
  *)
    echo "Unknown APP_SERVICE or command: $service" >&2
    echo "Use one of: chatbot, eval-logic, nightly-reindex, bash, sh, python, uvicorn" >&2
    exit 64
    ;;
esac
