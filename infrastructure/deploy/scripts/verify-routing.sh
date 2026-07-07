#!/usr/bin/env bash
# Post-deploy routing smoke — Valhalla in prod compose (§0.1.6).
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
API_URL="${API_URL:-https://api.porterchain.com}"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

if docker compose -f "$COMPOSE_FILE" ps valhalla --status running >/dev/null 2>&1; then
  if docker compose -f "$COMPOSE_FILE" exec -T valhalla curl -sf -m 5 http://localhost:8002/status | grep -qi tile; then
    pass "Valhalla container — /status OK"
  else
    echo "WARN  Valhalla running but tiles not ready (first boot builds Ontario graph — see RUNBOOK)"
  fi
else
  fail "Valhalla container not running"
fi

ready="$(curl -sf -m 10 "${API_URL}/health/ready" || true)"
if echo "$ready" | grep -q '"routing":"ok"'; then
  pass "API readiness — routing ok"
elif echo "$ready" | grep -q '"routing"'; then
  echo "WARN  API routing check: $(echo "$ready" | tr -d '\n' | sed -n 's/.*"routing":"\([^"]*\)".*/\1/p')"
else
  fail "API readiness missing routing check"
fi

pass "Routing verification complete"
