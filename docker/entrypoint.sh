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
  worker|eval-worker|eval_worker)
    cd /app/eval_logic
    exec python /app/eval_logic/src/workers/run_worker.py "$@"
    ;;
  report-worker|report_worker)
    cd /app/eval_logic
    exec python /app/eval_logic/src/workers/run_worker.py --worker report "$@"
    ;;
  patent-extract-worker|patent_extract_worker)
    cd /app/eval_logic
    exec python /app/eval_logic/src/workers/run_worker.py --worker patent-extract "$@"
    ;;
  pre-evaluation-worker|pre_evaluation_worker|preval-worker|preval_worker)
    cd /app/eval_logic
    exec python /app/eval_logic/src/workers/run_worker.py --worker pre-evaluation "$@"
    ;;
  nightly-reindex|reindex-once)
    exec python /app/chatbot/scripts/preprocess_chatbot_data.py --mode nightly-reindex "$@"
    ;;
  bash|sh|python|uvicorn)
    exec "$service" "$@"
    ;;
  *)
    echo "Unknown APP_SERVICE or command: $service" >&2
    echo "Use one of: chatbot, eval-logic, worker, report-worker, patent-extract-worker, pre-evaluation-worker, nightly-reindex, bash, sh, python, uvicorn" >&2
    exit 64
    ;;
esac
