#!/usr/bin/env bash
# Sync production secrets to /opt/porterchain/.env (DD-14).
#
# Modes:
#   DOPPLER_TOKEN set  → download from Doppler (secret manager SSOT)
#   otherwise          → write .env from CI env vars (legacy GitHub secrets)
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
)

verify_clerk_env() {
  local legacy=0 enterprise=1
  if grep -qE '^CLERK_SECRET_KEY=.+' .env && grep -qE '^CLERK_JWKS_URL=.+' .env; then
    legacy=1
  fi
  for portal in CUSTOMER MERCHANT ADMIN DRIVER; do
    if ! grep -qE "^CLERK_${portal}_SECRET_KEY=.+" .env || ! grep -qE "^CLERK_${portal}_JWKS_URL=.+" .env; then
      enterprise=0
      break
    fi
  done
  if [ "$legacy" -eq 1 ] || [ "$enterprise" -eq 1 ]; then
    if [ "$enterprise" -eq 1 ]; then
      echo "Clerk: enterprise (4 isolated apps)"
    else
      echo "Clerk: legacy single-app (migrate to CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_*)"
    fi
    return 0
  fi
  echo "::error::Clerk: set CLERK_SECRET_KEY+CLERK_JWKS_URL or all per-portal secret+JWKS keys" >&2
  return 1
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
import re
from pathlib import Path

raw = Path(".env").read_text(encoding="utf-8")
match = re.search(r"^FIREBASE_CREDENTIALS_JSON=(.*)$", raw, re.MULTILINE)
if not match:
    raise SystemExit(0)
value = match.group(1).strip()
if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
    value = value[1:-1]
if value:
    Path("secrets/firebase-service-account.json").write_text(value, encoding="utf-8")
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
  for key in "${REQUIRED_KEYS[@]}"; do
    if ! grep -q "^${key}=" .env; then
      echo "::error::missing required secret key: ${key}" >&2
      missing=1
    fi
  done
  return "$missing"
}

if [ -n "${DOPPLER_TOKEN:-}" ]; then
  if ! command -v doppler >/dev/null 2>&1; then
    echo "Installing Doppler CLI..."
    curl -sLf --retry 3 https://cli.doppler.com/install.sh | sh
  fi
  export DOPPLER_TOKEN
  doppler secrets download \
    --no-file \
    --format env \
    --project "${DOPPLER_PROJECT:-pcd}" \
    --config "${DOPPLER_CONFIG:-prd}" \
    > .env
  extract_firebase_from_env
  strip_inline_firebase_from_env
  echo "Secrets synced from Doppler (${DOPPLER_PROJECT:-pcd}/${DOPPLER_CONFIG:-prd})"
else
  cat > .env <<EOF
GOOGLE_MAPS_SERVER_API_KEY=${GOOGLE_MAPS_SERVER_API_KEY:-}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
CLERK_SECRET_KEY=${CLERK_SECRET_KEY:-}
CLERK_PUBLISHABLE_KEY=${CLERK_PUBLISHABLE_KEY:-}
CLERK_JWKS_URL=${CLERK_JWKS_URL:-}
CLERK_CUSTOMER_SECRET_KEY=${CLERK_CUSTOMER_SECRET_KEY:-}
CLERK_CUSTOMER_PUBLISHABLE_KEY=${CLERK_CUSTOMER_PUBLISHABLE_KEY:-}
CLERK_CUSTOMER_JWKS_URL=${CLERK_CUSTOMER_JWKS_URL:-}
CLERK_MERCHANT_SECRET_KEY=${CLERK_MERCHANT_SECRET_KEY:-}
CLERK_MERCHANT_PUBLISHABLE_KEY=${CLERK_MERCHANT_PUBLISHABLE_KEY:-}
CLERK_MERCHANT_JWKS_URL=${CLERK_MERCHANT_JWKS_URL:-}
CLERK_ADMIN_SECRET_KEY=${CLERK_ADMIN_SECRET_KEY:-}
CLERK_ADMIN_PUBLISHABLE_KEY=${CLERK_ADMIN_PUBLISHABLE_KEY:-}
CLERK_ADMIN_JWKS_URL=${CLERK_ADMIN_JWKS_URL:-}
CLERK_DRIVER_SECRET_KEY=${CLERK_DRIVER_SECRET_KEY:-}
CLERK_DRIVER_PUBLISHABLE_KEY=${CLERK_DRIVER_PUBLISHABLE_KEY:-}
CLERK_DRIVER_JWKS_URL=${CLERK_DRIVER_JWKS_URL:-}
STRIPE_SECRET=${STRIPE_SECRET:?STRIPE_SECRET is required}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:?STRIPE_WEBHOOK_SECRET is required}
JWT_SECRET=${JWT_SECRET:?JWT_SECRET is required}
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

chmod 600 .env
verify_env
verify_clerk_env
echo "✓ ${#REQUIRED_KEYS[@]} required keys present in .env"
