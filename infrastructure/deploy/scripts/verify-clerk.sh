#!/usr/bin/env bash
# Post-deploy Clerk JWKS verification (§0.5.6).
set -euo pipefail

API_URL="${API_URL:-https://api.porterchain.com}"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

ready="$(curl -sf -m 15 "${API_URL}/health/ready" || true)"
if [ -z "$ready" ]; then
  fail "API readiness unreachable at ${API_URL}/health/ready"
fi

mode="$(echo "$ready" | python3 -c "import json,sys; print(json.load(sys.stdin).get('clerk_mode',''))" 2>/dev/null || true)"
apps="$(echo "$ready" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get('clerk_apps',{})))" 2>/dev/null || echo '{}')"

if [ "$mode" = "enterprise" ]; then
  pass "Clerk mode: enterprise (4 isolated apps)"
elif [ "$mode" = "legacy" ]; then
  echo "WARN  Clerk mode: legacy single-app — add per-portal keys to Doppler for §0.5"
else
  fail "Clerk not configured (mode=${mode:-unknown})"
fi

for portal in customer merchant admin driver; do
  status="$(echo "$apps" | python3 -c "import json,sys; print(json.load(sys.stdin).get('${portal}','missing'))")"
  if [ "$status" = "ok" ]; then
    pass "JWKS ${portal}: ok"
  else
    fail "JWKS ${portal}: ${status}"
  fi
done

pass "Clerk verification complete"
