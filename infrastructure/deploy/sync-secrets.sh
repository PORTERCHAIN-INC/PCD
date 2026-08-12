#!/usr/bin/env bash
# Sync production secrets to /opt/porterchain/.env (DD-14).
#
# Clerk: platform_driver — TWO apps
#   Platform (clerk.admin.porterchain.com) → CLERK_* + CUSTOMER/MERCHANT/ADMIN slots
#   Driver   (clerk.driver.porterchain.com) → CLERK_DRIVER_*
# CLERK_UNIFIED_MODE must stay false. Do not strip portal slots.
#
# Modes:
#   DOPPLER_TOKEN set  → download from Doppler (secret manager SSOT)
#   otherwise          → write .env from CI env vars (legacy / break-glass)
#
# Usage (on droplet):
#   cd /opt/porterchain && bash sync-secrets.sh
#
# Local dry-run:
#   DOPPLER_TOKEN=dp.st… bash infrastructure/deploy/sync-secrets.sh /tmp/porterchain-test

set -euo pipefail

TARGET_DIR="${1:-/opt/porterchain}"
cd "$TARGET_DIR"
umask 077
mkdir -p secrets

REQUIRED_KEYS=(
  POSTGRES_PASSWORD
  STRIPE_SECRET
  STRIPE_WEBHOOK_SECRET
  JWT_SECRET
  SPICEDB_PRESHARED_KEY
  CLERK_SECRET_KEY
  CLERK_JWKS_URL
  CLERK_DRIVER_SECRET_KEY
  CLERK_DRIVER_JWKS_URL
)

env_value() {
  local key="$1"
  local line value
  line="$(grep -E "^${key}=" .env 2>/dev/null | tail -n1 || true)"
  value="${line#*=}"
  # Doppler env export may wrap values in single/double quotes.
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

set_env_key() {
  local key="$1"
  local value="$2"
  if grep -qE "^${key}=" .env 2>/dev/null; then
    grep -v -E "^${key}=" .env > .env.tmp && mv .env.tmp .env
  fi
  printf '%s=%s\n' "$key" "$value" >> .env
}

# Promote Admin slot → Platform triad when triad is missing (Platform = Admin app).
promote_platform_triad_from_admin() {
  local sk pk jwks
  sk="$(env_value CLERK_SECRET_KEY)"
  pk="$(env_value CLERK_PUBLISHABLE_KEY)"
  jwks="$(env_value CLERK_JWKS_URL)"

  if [ -z "$sk" ]; then
    sk="$(env_value CLERK_ADMIN_SECRET_KEY)"
    [ -n "$sk" ] && set_env_key CLERK_SECRET_KEY "$sk"
  fi
  if [ -z "$pk" ]; then
    pk="$(env_value CLERK_ADMIN_PUBLISHABLE_KEY)"
    [ -n "$pk" ] && set_env_key CLERK_PUBLISHABLE_KEY "$pk"
  fi
  if [ -z "$jwks" ]; then
    jwks="$(env_value CLERK_ADMIN_JWKS_URL)"
    [ -n "$jwks" ] && set_env_key CLERK_JWKS_URL "$jwks"
  fi
}

# Expand Platform triad into customer/merchant/admin slots when empty.
expand_platform_slots() {
  local sk pk jwks
  sk="$(env_value CLERK_SECRET_KEY)"
  pk="$(env_value CLERK_PUBLISHABLE_KEY)"
  jwks="$(env_value CLERK_JWKS_URL)"
  [ -z "$sk" ] && return 0

  for portal in ADMIN CUSTOMER MERCHANT; do
    [ -z "$(env_value "CLERK_${portal}_SECRET_KEY")" ] && set_env_key "CLERK_${portal}_SECRET_KEY" "$sk"
    [ -z "$(env_value "CLERK_${portal}_PUBLISHABLE_KEY")" ] && [ -n "$pk" ] && set_env_key "CLERK_${portal}_PUBLISHABLE_KEY" "$pk"
    [ -z "$(env_value "CLERK_${portal}_JWKS_URL")" ] && set_env_key "CLERK_${portal}_JWKS_URL" "$jwks"
  done
}

normalize_clerk_platform_driver() {
  promote_platform_triad_from_admin
  expand_platform_slots
  set_env_key CLERK_MODE platform_driver
  set_env_key CLERK_UNIFIED_MODE false
}

verify_clerk_env() {
  local sk jwks pk dsk djwks
  sk="$(env_value CLERK_SECRET_KEY)"
  jwks="$(env_value CLERK_JWKS_URL)"
  pk="$(env_value CLERK_PUBLISHABLE_KEY)"
  dsk="$(env_value CLERK_DRIVER_SECRET_KEY)"
  djwks="$(env_value CLERK_DRIVER_JWKS_URL)"

  if [ -z "$sk" ] || [ -z "$jwks" ]; then
    echo "::error::Clerk: set CLERK_SECRET_KEY + CLERK_JWKS_URL (Platform / admin.porterchain.com)" >&2
    return 1
  fi
  if [ -z "$dsk" ] || [ -z "$djwks" ]; then
    echo "::error::Clerk: set CLERK_DRIVER_SECRET_KEY + CLERK_DRIVER_JWKS_URL (Porterchain Driver)" >&2
    return 1
  fi
  if [[ "$sk" == sk_test_* ]] || [[ "$pk" == pk_test_* ]] || [[ "$dsk" == sk_test_* ]]; then
    echo "::error::Clerk: test keys are not allowed in production (need sk_live_ / pk_live_)" >&2
    return 1
  fi
  if [[ "$sk" != sk_live_* ]]; then
    echo "::error::Clerk: CLERK_SECRET_KEY must be sk_live_… (Platform)" >&2
    return 1
  fi
  if [[ "$dsk" != sk_live_* ]]; then
    echo "::error::Clerk: CLERK_DRIVER_SECRET_KEY must be sk_live_… (Driver)" >&2
    return 1
  fi
  if [ -n "$pk" ] && [[ "$pk" != pk_live_* ]]; then
    echo "::error::Clerk: CLERK_PUBLISHABLE_KEY must be pk_live_… (Platform)" >&2
    return 1
  fi
  if [ "$sk" = "$dsk" ]; then
    echo "::warning::Clerk: Platform and Driver secret keys match — expected distinct apps in production" >&2
  fi
  echo "Clerk: platform_driver (Platform + Driver triads)"
  return 0
}

write_firebase_file() {
  if [ -n "${FIREBASE_CREDENTIALS_JSON:-}" ]; then
    printf '%s' "$FIREBASE_CREDENTIALS_JSON" > secrets/firebase-service-account.json
  elif [ -f secrets/firebase-service-account.json ] && [ -s secrets/firebase-service-account.json ]; then
    : # keep existing file when syncing from Doppler without inline JSON
  else
    : > secrets/firebase-service-account.json
  fi
  chmod 600 secrets/firebase-service-account.json
}

extract_firebase_from_env() {
  if ! grep -q '^FIREBASE_CREDENTIALS_JSON=' .env 2>/dev/null; then
    return 0
  fi
  python3 - <<'PY'
import json
import re
from pathlib import Path

raw = Path(".env").read_text(encoding="utf-8")
match = re.search(r"^FIREBASE_CREDENTIALS_JSON=(.*)$", raw, re.MULTILINE)
if not match:
    raise SystemExit(0)
value = match.group(1).strip()
if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
    value = json.loads(value)
elif value.startswith("{\\"):
    value = json.loads(value.encode().decode("unicode_escape"))
elif value.startswith("{"):
    value = json.loads(value)
if not value:
    raise SystemExit(0)
out = json.dumps(value) if isinstance(value, dict) else str(value)
Path("secrets/firebase-service-account.json").write_text(out, encoding="utf-8")
PY
  chmod 600 secrets/firebase-service-account.json
}

strip_inline_firebase_from_env() {
  if grep -q '^FIREBASE_CREDENTIALS_JSON=' .env 2>/dev/null; then
    grep -v '^FIREBASE_CREDENTIALS_JSON=' .env > .env.tmp && mv .env.tmp .env
  fi
}

verify_env() {
  local missing=0
  local key
  for key in "${REQUIRED_KEYS[@]}"; do
    if ! grep -qE "^${key}=.+" .env; then
      echo "::error::missing required secret key: ${key}" >&2
      missing=1
    fi
  done
  return "$missing"
}

# Prefer CI-uploaded token file over env. appleboy env forwarding can truncate
# or mangle DOPPLER_TOKEN (observed len=53) while the SCP'd file stays intact.
if [ -f "${TARGET_DIR}/doppler.token" ]; then
  DOPPLER_TOKEN="$(tr -d '\r\n' < "${TARGET_DIR}/doppler.token")"
  export DOPPLER_TOKEN
  echo "Using Doppler token from doppler.token (len=${#DOPPLER_TOKEN})"
elif [ -n "${DOPPLER_TOKEN:-}" ]; then
  echo "Using Doppler token from environment (len=${#DOPPLER_TOKEN})"
fi

_download_doppler_env() {
  local out="$1"
  local project="${DOPPLER_PROJECT:-pcd}"
  local config="${DOPPLER_CONFIG:-prd}"
  if command -v doppler >/dev/null 2>&1; then
    if doppler secrets download \
      --no-file \
      --format env \
      --project "$project" \
      --config "$config" \
      >"$out"; then
      return 0
    fi
    echo "doppler CLI download failed; trying HTTP API…" >&2
  fi
  # Fallback: same API the Actions preflight uses (no CLI / no sudo).
  local code
  code="$(curl -sS -o "$out" -w '%{http_code}' \
    -H "Authorization: Bearer ${DOPPLER_TOKEN}" \
    "https://api.doppler.com/v3/configs/config/secrets/download?project=${project}&config=${config}&format=env")"
  if [ "$code" != "200" ]; then
    echo "::error::Doppler secrets download failed (HTTP ${code}) for ${project}/${config}" >&2
    head -c 400 "$out" >&2 || true
    echo >&2
    return 1
  fi
  return 0
}

if [ -n "${DOPPLER_TOKEN:-}" ]; then
  if [ -z "${DOPPLER_TOKEN}" ]; then
    echo "::error::DOPPLER_TOKEN is empty on droplet (env + doppler.token missing)" >&2
    exit 1
  fi
  export DOPPLER_TOKEN
  # Write to a temp file first — a failed download must not truncate .env to 0 bytes.
  tmp_env="$(mktemp "${TARGET_DIR}/.env.doppler.XXXXXX")"
  trap 'rm -f "${tmp_env}"' EXIT
  if ! _download_doppler_env "${tmp_env}"; then
    exit 1
  fi
  if [ ! -s "${tmp_env}" ]; then
    echo "::error::doppler secrets download produced an empty file" >&2
    exit 1
  fi
  if [ -s .env ]; then
    cp -a .env ".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  mv "${tmp_env}" .env
  trap - EXIT
  rm -f "${TARGET_DIR}/doppler.token"
  extract_firebase_from_env
  strip_inline_firebase_from_env
  normalize_clerk_platform_driver
  echo "Secrets synced from Doppler (${DOPPLER_PROJECT:-pcd}/${DOPPLER_CONFIG:-prd})"
else
  # Break-glass: Platform + Driver (optional Admin names as Platform fallback).
  CLERK_SECRET_KEY="${CLERK_SECRET_KEY:-${CLERK_ADMIN_SECRET_KEY:-}}"
  CLERK_PUBLISHABLE_KEY="${CLERK_PUBLISHABLE_KEY:-${CLERK_ADMIN_PUBLISHABLE_KEY:-}}"
  CLERK_JWKS_URL="${CLERK_JWKS_URL:-${CLERK_ADMIN_JWKS_URL:-}}"
  # Expand required vars before truncating .env (bash evaluates ${VAR:?} while writing the heredoc).
  : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
  : "${CLERK_SECRET_KEY:?CLERK_SECRET_KEY (Platform) is required}"
  : "${CLERK_JWKS_URL:?CLERK_JWKS_URL (Platform) is required}"
  : "${CLERK_DRIVER_SECRET_KEY:?CLERK_DRIVER_SECRET_KEY is required}"
  : "${CLERK_DRIVER_JWKS_URL:?CLERK_DRIVER_JWKS_URL is required}"
  : "${STRIPE_SECRET:?STRIPE_SECRET is required}"
  : "${STRIPE_WEBHOOK_SECRET:?STRIPE_WEBHOOK_SECRET is required}"
  : "${JWT_SECRET:?JWT_SECRET is required}"
  : "${SPICEDB_PRESHARED_KEY:?SPICEDB_PRESHARED_KEY is required}"
  if [ -s .env ]; then
    cp -a .env ".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  cat > .env <<EOF
GOOGLE_MAPS_SERVER_API_KEY=${GOOGLE_MAPS_SERVER_API_KEY:-}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
CLERK_MODE=platform_driver
CLERK_UNIFIED_MODE=false
CLERK_SECRET_KEY=${CLERK_SECRET_KEY}
CLERK_PUBLISHABLE_KEY=${CLERK_PUBLISHABLE_KEY:-}
CLERK_JWKS_URL=${CLERK_JWKS_URL}
CLERK_ADMIN_SECRET_KEY=${CLERK_ADMIN_SECRET_KEY:-${CLERK_SECRET_KEY}}
CLERK_ADMIN_PUBLISHABLE_KEY=${CLERK_ADMIN_PUBLISHABLE_KEY:-${CLERK_PUBLISHABLE_KEY}}
CLERK_ADMIN_JWKS_URL=${CLERK_ADMIN_JWKS_URL:-${CLERK_JWKS_URL}}
CLERK_CUSTOMER_SECRET_KEY=${CLERK_CUSTOMER_SECRET_KEY:-${CLERK_SECRET_KEY}}
CLERK_CUSTOMER_PUBLISHABLE_KEY=${CLERK_CUSTOMER_PUBLISHABLE_KEY:-${CLERK_PUBLISHABLE_KEY}}
CLERK_CUSTOMER_JWKS_URL=${CLERK_CUSTOMER_JWKS_URL:-${CLERK_JWKS_URL}}
CLERK_MERCHANT_SECRET_KEY=${CLERK_MERCHANT_SECRET_KEY:-${CLERK_SECRET_KEY}}
CLERK_MERCHANT_PUBLISHABLE_KEY=${CLERK_MERCHANT_PUBLISHABLE_KEY:-${CLERK_PUBLISHABLE_KEY}}
CLERK_MERCHANT_JWKS_URL=${CLERK_MERCHANT_JWKS_URL:-${CLERK_JWKS_URL}}
CLERK_DRIVER_SECRET_KEY=${CLERK_DRIVER_SECRET_KEY}
CLERK_DRIVER_PUBLISHABLE_KEY=${CLERK_DRIVER_PUBLISHABLE_KEY:-}
CLERK_DRIVER_JWKS_URL=${CLERK_DRIVER_JWKS_URL}
CLERK_AUTHORIZED_PARTIES=${CLERK_AUTHORIZED_PARTIES:-}
CLERK_AUTHORIZED_ISSUERS=${CLERK_AUTHORIZED_ISSUERS:-}
CLERK_WEBHOOK_SIGNING_SECRET=${CLERK_WEBHOOK_SIGNING_SECRET:-}
STRIPE_SECRET=${STRIPE_SECRET}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
JWT_SECRET=${JWT_SECRET}
SPICEDB_PRESHARED_KEY=${SPICEDB_PRESHARED_KEY}
SPICEDB_ENABLED=${SPICEDB_ENABLED:-true}
SPICEDB_REQUIRED=${SPICEDB_REQUIRED:-true}
SPICEDB_ENDPOINT=${SPICEDB_ENDPOINT:-spicedb:50051}
SENTRY_DSN=${SENTRY_DSN:-}
CORS_ORIGINS=https://porterchain.com,https://www.porterchain.com,https://admin.porterchain.com,https://merchant.porterchain.com,https://driver.porterchain.com,https://customer.porterchain.com
FLEETBASE_DISPATCH_BRIDGE=${FLEETBASE_DISPATCH_BRIDGE:-false}
FLEETBASE_SSO_ENABLED=${FLEETBASE_SSO_ENABLED:-false}
FLEETBASE_API_URL=${FLEETBASE_API_URL:-}
FLEETBASE_API_KEY=${FLEETBASE_API_KEY:-}
FLEETBASE_WEBHOOK_SECRET=${FLEETBASE_WEBHOOK_SECRET:-}
FLEETBASE_DEFAULT_COMPANY_UUID=${FLEETBASE_DEFAULT_COMPANY_UUID:-}
PORTERCHAIN_PUSH_ENABLED=${PORTERCHAIN_PUSH_ENABLED:-false}
PORTERCHAIN_PUSH_SEND=${PORTERCHAIN_PUSH_SEND:-false}
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-}
FIREBASE_WEB_VAPID_KEY=${FIREBASE_WEB_VAPID_KEY:-}
API_REPLICAS=${API_REPLICAS:-2}
EOF
  write_firebase_file
  echo "Secrets written from deploy environment (legacy GitHub secrets path)"
fi

write_firebase_file
chmod 600 .env
if ! verify_env; then
  echo "::error::sync-secrets verify_env failed" >&2
  exit 1
fi
if ! verify_clerk_env; then
  echo "::error::sync-secrets verify_clerk_env failed" >&2
  exit 1
fi
echo "✓ ${#REQUIRED_KEYS[@]} required keys present in .env (platform_driver)"
