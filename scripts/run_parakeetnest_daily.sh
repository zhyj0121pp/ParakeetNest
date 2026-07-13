#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python"
fi

REPORT_MODE="${PARAKEETNEST_REPORT_MODE:-morning}"
if [[ "${1:-}" == "--mode" ]]; then
  if [[ $# -lt 2 ]]; then
    echo "--mode requires morning or evening" >&2
    exit 2
  fi
  REPORT_MODE="$2"
  shift 2
fi

case "${REPORT_MODE}" in
  morning|evening)
    ;;
  *)
    echo "invalid report mode: ${REPORT_MODE}; expected morning or evening" >&2
    exit 2
    ;;
esac

exec "${PYTHON_BIN}" -m parakeetnest.cli.daily_report \
  --mode "${REPORT_MODE}" \
  --archive \
  "$@"
