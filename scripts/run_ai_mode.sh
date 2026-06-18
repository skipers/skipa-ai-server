#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_ai_mode.sh <openai|opensource> -- <command...>

Examples:
  scripts/run_ai_mode.sh opensource -- python3 -m uvicorn pre_application_valuation.api:app --reload --port 8010
  scripts/run_ai_mode.sh openai -- python3 -m uvicorn app.main:app --app-dir ai-insights --port 8002
USAGE
}

if [[ $# -lt 3 || "${2:-}" != "--" ]]; then
  usage >&2
  exit 2
fi

MODE="$1"
shift 2

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_ENV="${ROOT_DIR}/.env"
MODE_ENV="${ROOT_DIR}/ai_runtime/modes/${MODE}.env"

if [[ ! -f "${MODE_ENV}" ]]; then
  cat >&2 <<EOF
Missing mode profile: ${MODE_ENV}

Create it first, for example:
  cp ai_runtime/modes/${MODE}.env.example ai_runtime/modes/${MODE}.env
EOF
  exit 1
fi

set -a
if [[ -f "${BASE_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${BASE_ENV}"
fi
# shellcheck disable=SC1090
source "${MODE_ENV}"
set +a

exec "$@"
