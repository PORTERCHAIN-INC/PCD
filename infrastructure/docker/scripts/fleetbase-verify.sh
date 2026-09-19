#!/usr/bin/env bash
# Verify all Fleetbase services are running and reachable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FLEETBASE_DIR="$ROOT/apps/fleetbase"
COMPOSE_OVERRIDE="$ROOT/infrastructure/docker/fleetbase.porterchain.override.yml"
STATUS_FILE="$ROOT/SERVICE_STATUS.md"

cd "$FLEETBASE_DIR"

compose() {
  docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$COMPOSE_OVERRIDE" "$@"
}

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILED=1; }

FAILED=0
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Fleetbase service verification — $TIMESTAMP"
echo "==========================================="

# Container health
for svc in database cache socket queue scheduler application httpd console; do
  CID=$(compose ps -q "$svc" 2>/dev/null || true)
  if [[ -z "$CID" ]]; then
    fail "container $svc — not found"
    continue
  fi
  STATE=$(docker inspect -f '{{.State.Status}}' "$CID" 2>/dev/null || echo "unknown")
  if [[ "$STATE" == "running" ]]; then
    pass "container $svc — running"
  else
    fail "container $svc — $STATE"
  fi
done

# HTTP endpoints
if curl -sf -o /dev/null -m 10 http://127.0.0.1:8000/; then
  pass "API (httpd :8000) — HTTP reachable"
else
  fail "API (httpd :8000) — not reachable"
fi

# SocketCluster
if curl -sf -o /dev/null -m 5 http://127.0.0.1:38000/ 2>/dev/null || nc -z 127.0.0.1 38000 2>/dev/null; then
  pass "SocketCluster (:38000) — port open"
else
  fail "SocketCluster (:38000) — not reachable"
fi

# Redis
if compose exec -T cache redis-cli ping 2>/dev/null | grep -q PONG; then
  pass "Redis — PONG"
else
  fail "Redis — no PONG"
fi

# MySQL
if compose exec -T database mysqladmin ping -h localhost -uroot --silent 2>/dev/null; then
  pass "MySQL — ping"
else
  fail "MySQL — ping failed"
fi

# Queue worker
if compose exec -T queue php artisan queue:status 2>/dev/null; then
  pass "Queue worker — status command ok"
else
  fail "Queue worker — status check failed"
fi

# OSRM (local GTA ±150 km fallback)
if curl -sf -m 10 "http://127.0.0.1:5000/route/v1/driving/-79.38,43.65;-79.40,43.66?overview=false" | grep -q routes; then
  pass "OSRM (:5000) — route response"
else
  fail "OSRM (:5000) — unreachable (prepare-osrm-gta.sh + compose profile routing)"
fi

# Valhalla (optional — Porterchain routing profile)
if curl -sf -m 5 http://127.0.0.1:8002/status 2>/dev/null | grep -qi tile; then
  pass "Valhalla (:8002) — running (Porterchain routing profile)"
else
  echo "SKIP  Valhalla (:8002) — not running (start: pnpm docker:up:routing)"
fi

# Order create contract (root of PC→Fleetbase sync). Repair:
#   python infrastructure/docker/scripts/repair_fleetbase_local.py
API_KEY=""
COMPANY_UUID=""
if [[ -f "$ROOT/apps/api/.env" ]]; then
  API_KEY=$(grep -E '^FLEETBASE_API_KEY=' "$ROOT/apps/api/.env" | head -1 | cut -d= -f2- | tr -d '"' || true)
  COMPANY_UUID=$(grep -E '^FLEETBASE_DEFAULT_COMPANY_UUID=' "$ROOT/apps/api/.env" | head -1 | cut -d= -f2- | tr -d '"' || true)
fi
if [[ -n "$API_KEY" && -n "$COMPANY_UUID" ]]; then
  OC_COUNT=$(compose exec -T database mysql -N -ufleetbase -e \
    "SELECT COUNT(*) FROM fleetbase.order_configs WHERE \`key\`='transport' AND deleted_at IS NULL;" 2>/dev/null || echo 0)
  if [[ "${OC_COUNT:-0}" -ge 1 ]]; then
    pass "OrderConfig key=transport — present ($OC_COUNT)"
  else
    fail "OrderConfig key=transport — missing (run repair_fleetbase_local.py)"
  fi
  HTTP=$(curl -s -o /tmp/fb_order_smoke.json -w '%{http_code}' -m 20 \
    -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
    -d "{\"type\":\"transport\",\"company_uuid\":\"$COMPANY_UUID\",\"internal_id\":\"pc-verify-smoke\",\"pickup\":{\"street1\":\"1 King St W\",\"city\":\"Toronto\",\"country\":\"CA\",\"location\":{\"type\":\"Point\",\"coordinates\":[-79.38,43.65]}},\"dropoff\":{\"street1\":\"2 Bay St\",\"city\":\"Toronto\",\"country\":\"CA\",\"location\":{\"type\":\"Point\",\"coordinates\":[-79.37,43.64]}}}" \
    http://127.0.0.1:8000/v1/orders || echo 000)
  if [[ "$HTTP" == "200" || "$HTTP" == "201" ]]; then
    pass "POST /v1/orders — HTTP $HTTP"
  else
    fail "POST /v1/orders — HTTP $HTTP (see repair_fleetbase_local.py)"
  fi
else
  echo "SKIP  POST /v1/orders — FLEETBASE_API_KEY / company uuid not in apps/api/.env"
fi

echo ""
if [[ "${FAILED:-0}" -eq 0 ]]; then
  echo "All required checks passed."
  exit 0
else
  echo "Some checks failed."
  exit 1
fi
