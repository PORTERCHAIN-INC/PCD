#!/usr/bin/env bash
# Enable PorterChain → Fleetbase SSO on the production droplet.
# Idempotent. Does not print secret values.
#
# Usage (on droplet as root):
#   bash /opt/porterchain/scripts/enable-fleetbase-sso-prod.sh
set -euo pipefail

PORTERCHAIN_DIR="${PORTERCHAIN_DIR:-/opt/porterchain}"
FLEETBASE_DIR="${FLEETBASE_DIR:-/opt/fleetbase}"
BRIDGE_SRC="${PORTERCHAIN_DIR}/packages/porterchain-bridge"
SSO_OVERRIDE="${PORTERCHAIN_DIR}/fleetbase.sso.override.yml"

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

need() {
  if [[ ! -e "$1" ]]; then
    err "Missing $1"
    exit 1
  fi
}

need "$PORTERCHAIN_DIR/.env"
need "$FLEETBASE_DIR/docker-compose.yml"
need "$BRIDGE_SRC/src/Http/Controllers/SsoController.php"
need "$SSO_OVERRIDE"

env_value() {
  local key="$1" file="${2:-$PORTERCHAIN_DIR/.env}"
  local line value
  line="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -n1 || true)"
  value="${line#*=}"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

set_env_key() {
  local file="$1" key="$2" value="$3"
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    grep -v -E "^${key}=" "$file" >"${file}.tmp" && mv "${file}.tmp" "$file"
  fi
  printf '%s=%s\n' "$key" "$value" >>"$file"
}

JWT_SECRET="$(env_value JWT_SECRET)"
SSO_JWT_SECRET="$(env_value SSO_JWT_SECRET)"
COMPANY_UUID="$(env_value FLEETBASE_DEFAULT_COMPANY_UUID)"
CONSOLE_URL="$(env_value FLEETBASE_CONSOLE_URL)"

if [[ -z "$JWT_SECRET" ]]; then
  err "JWT_SECRET missing in $PORTERCHAIN_DIR/.env"
  exit 1
fi
if [[ -z "$COMPANY_UUID" ]]; then
  err "FLEETBASE_DEFAULT_COMPANY_UUID missing"
  exit 1
fi

SSO_SECRET="${SSO_JWT_SECRET:-$JWT_SECRET}"
CONSOLE_URL="${CONSOLE_URL:-https://console.porterchain.com}"

info "Writing Fleetbase SSO env (lengths only)…"
umask 077
touch "$FLEETBASE_DIR/.env"
chmod 600 "$FLEETBASE_DIR/.env"
set_env_key "$FLEETBASE_DIR/.env" PORTERCHAIN_SSO_JWT_SECRET "$SSO_SECRET"
set_env_key "$FLEETBASE_DIR/.env" PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID "$COMPANY_UUID"
ok "Fleetbase SSO env jwt_len=${#SSO_SECRET} company=${COMPANY_UUID}"

info "Patching Fleetbase docker-compose.override.yml public URLs…"
python3 - <<'PY'
from pathlib import Path
p = Path("/opt/fleetbase/docker-compose.override.yml")
text = p.read_text()
replacements = {
    'APP_URL: "http://localhost:8000"': 'APP_URL: "https://console.porterchain.com"',
    'APP_URL: "https://fleetbase.porterchain.com"': 'APP_URL: "https://console.porterchain.com"',
    'ENVIRONMENT: "development"': 'ENVIRONMENT: "production"',
    'APP_DEBUG: "true"': 'APP_DEBUG: "false"',
    'SESSION_DOMAIN: "localhost"': 'SESSION_DOMAIN: "console.porterchain.com"',
    'SESSION_DOMAIN: ".porterchain.com"': 'SESSION_DOMAIN: "console.porterchain.com"',
    'APP_NAME: "Fleetbase"': 'APP_NAME: "PorterChain"',
}
for a, b in replacements.items():
    text = text.replace(a, b)
# SocketCluster origins — allow the public console host
old = 'SOCKETCLUSTER_OPTIONS: \'{"origins":"http://localhost:*,https://localhost:*,ws://localhost:*,wss://localhost:*"}\''
new = 'SOCKETCLUSTER_OPTIONS: \'{"origins":"https://console.porterchain.com:*,https://admin.porterchain.com:*,wss://console.porterchain.com:*"}\''
text = text.replace(old, new)
p.write_text(text)
print("patched docker-compose.override.yml")
PY

info "Writing console runtime config…"
mkdir -p "$FLEETBASE_DIR/console"
cat >"$FLEETBASE_DIR/console/fleetbase.config.json" <<'JSON'
{
  "API_HOST": "https://console.porterchain.com",
  "SOCKETCLUSTER_HOST": "console.porterchain.com",
  "SOCKETCLUSTER_PORT": "443",
  "SOCKETCLUSTER_SECURE": "true"
}
JSON
ok "console/fleetbase.config.json → https://console.porterchain.com"

info "Recreating Fleetbase application with SSO bridge…"
cd "$FLEETBASE_DIR"
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$SSO_OVERRIDE" \
  up -d --no-deps --pull never application socket

# Nginx in httpd caches upstream IPs; restart so it finds the new application container.
docker restart fleetbase-httpd-1 >/dev/null
sleep 5
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$SSO_OVERRIDE" \
  exec -T application php artisan config:clear >/dev/null 2>&1 || true

info "Enabling SSO on PorterChain API…"
set_env_key "$PORTERCHAIN_DIR/.env" FLEETBASE_SSO_ENABLED true
set_env_key "$PORTERCHAIN_DIR/.env" FLEETBASE_CONSOLE_URL "$CONSOLE_URL"
if [[ -n "$SSO_JWT_SECRET" ]]; then
  set_env_key "$PORTERCHAIN_DIR/.env" SSO_JWT_SECRET "$SSO_JWT_SECRET"
fi
chmod 600 "$PORTERCHAIN_DIR/.env"

cd "$PORTERCHAIN_DIR"
API_IMAGE="$(docker inspect porterchain-prod-api-1 --format '{{.Config.Image}}')"
export API_IMAGE
info "Recreating API/worker/caddy (image ${API_IMAGE})"
docker compose -f docker-compose.prod.yml up -d --no-deps --pull never --force-recreate api worker caddy

info "Waiting for API health…"
for i in $(seq 1 30); do
  if docker exec porterchain-prod-api-1 printenv FLEETBASE_SSO_ENABLED 2>/dev/null | grep -qiE '^(true|1|yes)$'; then
    ok "API FLEETBASE_SSO_ENABLED=true"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    err "API did not pick up FLEETBASE_SSO_ENABLED"
    docker exec porterchain-prod-api-1 printenv FLEETBASE_SSO_ENABLED || true
    exit 1
  fi
  sleep 2
done

info "Verifying Fleetbase SSO bridge…"
body=""
if docker exec fleetbase-application-1 sh -c 'command -v curl >/dev/null'; then
  body="$(docker exec fleetbase-application-1 curl -sS -X POST http://httpd/int/v1/porterchain/sso/exchange \
    -H 'Content-Type: application/json' -H 'Accept: application/json' \
    -d '{"token":"bad"}' || true)"
else
  body="$(curl -sS -X POST http://127.0.0.1:8000/int/v1/porterchain/sso/exchange \
    -H 'Content-Type: application/json' -H 'Accept: application/json' \
    -d '{"token":"bad"}' || true)"
fi
echo "$body"
if echo "$body" | grep -q 'sso_token_invalid'; then
  ok "SSO exchange endpoint is live"
else
  err "SSO exchange did not return sso_token_invalid (bridge not mounted?)"
  docker exec fleetbase-application-1 ls /fleetbase/api/packages/porterchain-bridge | head || true
  exit 1
fi

ok "SSO enabled. Open the dispatch console from https://admin.porterchain.com"
echo "Direct https://console.porterchain.com shows the Admin gate (no Fleetbase password form)."
echo "Add DNS A record for fleetbase.porterchain.com → this droplet when you want a public API host."
