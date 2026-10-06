#!/usr/bin/env bash
# Run D3 Phase 1 static matrix with API venv when present, else python3 (CI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/apps/api/.venv/bin/python" ]]; then
  PY="$ROOT/apps/api/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
cd "$ROOT/apps/api"
PYTHONPATH=src:../../shared/python:../../services/python:../../services/pricing-engine:../../services/event-bus:../../services/driver-platform \
  "$PY" scripts/verify_d3_matrix.py "$@"
