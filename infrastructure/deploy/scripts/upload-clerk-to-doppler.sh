#!/usr/bin/env bash
# Upload Clerk keys to Doppler — platform_driver mode (Platform + Driver).
#
# MANUAL HUMAN GATE — founder/security-owned for production.
# Usage:
#   bash infrastructure/deploy/scripts/upload-clerk-to-doppler.sh [env-file]
#   DOPPLER_CONFIG=prd bash .../upload-clerk-to-doppler.sh infrastructure/deploy/scripts/clerk-keys.local.env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$(bash "${SCRIPT_DIR}/resolve-clerk-env.sh" "${1:-}")"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

bash "${SCRIPT_DIR}/validate-clerk-keys.sh" "$ENV_FILE" || true

command -v doppler >/dev/null || { echo "Install: brew install dopplerhq/cli/doppler" >&2; exit 1; }
doppler me >/dev/null 2>&1 || doppler login

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

MODE="${CLERK_MODE:-platform_driver}"

# Expand Platform → customer/merchant/admin when only ADMIN / triad set
PLATFORM_PK="${CLERK_PUBLISHABLE_KEY:-${CLERK_ADMIN_PUBLISHABLE_KEY:-}}"
PLATFORM_SK="${CLERK_SECRET_KEY:-${CLERK_ADMIN_SECRET_KEY:-}}"
PLATFORM_JWKS="${CLERK_JWKS_URL:-${CLERK_ADMIN_JWKS_URL:-}}"

CLERK_ADMIN_PUBLISHABLE_KEY="${CLERK_ADMIN_PUBLISHABLE_KEY:-$PLATFORM_PK}"
CLERK_ADMIN_SECRET_KEY="${CLERK_ADMIN_SECRET_KEY:-$PLATFORM_SK}"
CLERK_ADMIN_JWKS_URL="${CLERK_ADMIN_JWKS_URL:-$PLATFORM_JWKS}"

CLERK_CUSTOMER_PUBLISHABLE_KEY="${CLERK_CUSTOMER_PUBLISHABLE_KEY:-$PLATFORM_PK}"
CLERK_CUSTOMER_SECRET_KEY="${CLERK_CUSTOMER_SECRET_KEY:-$PLATFORM_SK}"
CLERK_CUSTOMER_JWKS_URL="${CLERK_CUSTOMER_JWKS_URL:-$PLATFORM_JWKS}"

CLERK_MERCHANT_PUBLISHABLE_KEY="${CLERK_MERCHANT_PUBLISHABLE_KEY:-$PLATFORM_PK}"
CLERK_MERCHANT_SECRET_KEY="${CLERK_MERCHANT_SECRET_KEY:-$PLATFORM_SK}"
CLERK_MERCHANT_JWKS_URL="${CLERK_MERCHANT_JWKS_URL:-$PLATFORM_JWKS}"

CLERK_PUBLISHABLE_KEY="$PLATFORM_PK"
CLERK_SECRET_KEY="$PLATFORM_SK"
CLERK_JWKS_URL="$PLATFORM_JWKS"

if [ -z "$PLATFORM_PK" ] || [ -z "$PLATFORM_SK" ] || [ -z "${CLERK_DRIVER_SECRET_KEY:-}" ]; then
  echo "Missing Platform triad or CLERK_DRIVER_* in ${ENV_FILE}" >&2
  exit 1
fi

if [ "$MODE" = "unified" ] || [ "$MODE" = "enterprise" ]; then
  echo "CLERK_MODE=${MODE} is retired — use platform_driver" >&2
  exit 1
fi
UNIFIED_FLAG="false"

# Optional JWT / webhook policy (set in clerk-keys.local.env when ready)
CLERK_AUTHORIZED_PARTIES="${CLERK_AUTHORIZED_PARTIES:-}"
CLERK_AUTHORIZED_ISSUERS="${CLERK_AUTHORIZED_ISSUERS:-}"
CLERK_WEBHOOK_SIGNING_SECRET="${CLERK_WEBHOOK_SIGNING_SECRET:-}"

echo "Uploading Clerk keys to Doppler ${PROJECT}/${CONFIG} (mode=${MODE})..."

DOPPLER_ARGS=(
  --project "$PROJECT"
  --config "$CONFIG"
  "CLERK_MODE=${MODE}"
  "CLERK_UNIFIED_MODE=${UNIFIED_FLAG}"
  "CLERK_PUBLISHABLE_KEY=${CLERK_PUBLISHABLE_KEY}"
  "CLERK_SECRET_KEY=${CLERK_SECRET_KEY}"
  "CLERK_JWKS_URL=${CLERK_JWKS_URL}"
  "CLERK_CUSTOMER_PUBLISHABLE_KEY=${CLERK_CUSTOMER_PUBLISHABLE_KEY}"
  "CLERK_CUSTOMER_SECRET_KEY=${CLERK_CUSTOMER_SECRET_KEY}"
  "CLERK_CUSTOMER_JWKS_URL=${CLERK_CUSTOMER_JWKS_URL}"
  "CLERK_MERCHANT_PUBLISHABLE_KEY=${CLERK_MERCHANT_PUBLISHABLE_KEY}"
  "CLERK_MERCHANT_SECRET_KEY=${CLERK_MERCHANT_SECRET_KEY}"
  "CLERK_MERCHANT_JWKS_URL=${CLERK_MERCHANT_JWKS_URL}"
  "CLERK_ADMIN_PUBLISHABLE_KEY=${CLERK_ADMIN_PUBLISHABLE_KEY}"
  "CLERK_ADMIN_SECRET_KEY=${CLERK_ADMIN_SECRET_KEY}"
  "CLERK_ADMIN_JWKS_URL=${CLERK_ADMIN_JWKS_URL}"
  "CLERK_DRIVER_PUBLISHABLE_KEY=${CLERK_DRIVER_PUBLISHABLE_KEY}"
  "CLERK_DRIVER_SECRET_KEY=${CLERK_DRIVER_SECRET_KEY}"
  "CLERK_DRIVER_JWKS_URL=${CLERK_DRIVER_JWKS_URL}"
)

if [ -n "$CLERK_AUTHORIZED_PARTIES" ]; then
  DOPPLER_ARGS+=("CLERK_AUTHORIZED_PARTIES=${CLERK_AUTHORIZED_PARTIES}")
fi
if [ -n "$CLERK_AUTHORIZED_ISSUERS" ]; then
  DOPPLER_ARGS+=("CLERK_AUTHORIZED_ISSUERS=${CLERK_AUTHORIZED_ISSUERS}")
fi
if [ -n "$CLERK_WEBHOOK_SIGNING_SECRET" ]; then
  DOPPLER_ARGS+=("CLERK_WEBHOOK_SIGNING_SECRET=${CLERK_WEBHOOK_SIGNING_SECRET}")
fi

doppler secrets set "${DOPPLER_ARGS[@]}"

echo "✓ Clerk secrets set in Doppler ${PROJECT}/${CONFIG}"
if [ -n "$CLERK_AUTHORIZED_PARTIES" ] || [ -n "$CLERK_AUTHORIZED_ISSUERS" ] || [ -n "$CLERK_WEBHOOK_SIGNING_SECRET" ]; then
  echo "  (included optional azp/issuers/webhook when set in env file)"
fi
echo "Next: bash infrastructure/deploy/scripts/upload-clerk-to-github.sh (publishable keys for CI)"
echo "Then: rebuild/redeploy portals so Next gets correct NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY per app"
