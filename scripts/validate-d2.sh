#!/usr/bin/env bash
# Run static D2 contract validators with API venv when present, else python3 (CI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/apps/api/.venv/bin/python" ]]; then
  PY="$ROOT/apps/api/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
cd "$ROOT/apps/api"
PYTHONPATH=src "$PY" scripts/verify_d2_contracts.py
cd "$ROOT"
"$PY" scripts/verify_repositories.py
"$PY" scripts/verify_order_transitions.py
"$PY" scripts/verify_notification_catalog.py
"$PY" scripts/verify_event_catalog.py
"$PY" scripts/verify_shared_kernel.py
"$PY" scripts/verify_merchant_webhook_event_path.py
"$PY" scripts/verify_reporting_context.py
"$PY" scripts/verify_schema_context.py
"$PY" scripts/verify_queue_runbook.py
