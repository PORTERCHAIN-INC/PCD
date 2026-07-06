#!/usr/bin/env bash
# Upload 4-app Clerk keys from clerk-keys.local.env to Doppler (§0.5).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${1:-${SCRIPT_DIR}/clerk-keys.local.env}"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

bash "${SCRIPT_DIR}/validate-clerk-keys.sh" "$ENV_FILE"

command -v doppler >/dev/null || { echo "Install: brew install dopplerhq/cli/doppler" >&2; exit 1; }
doppler me >/dev/null 2>&1 || doppler login

echo "Uploading Clerk keys to Doppler ${PROJECT}/${CONFIG}..."

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

doppler secrets set \
  --project "$PROJECT" \
  --config "$CONFIG" \
  "CLERK_CUSTOMER_PUBLISHABLE_KEY=${CLERK_CUSTOMER_PUBLISHABLE_KEY}" \
  "CLERK_CUSTOMER_SECRET_KEY=${CLERK_CUSTOMER_SECRET_KEY}" \
  "CLERK_CUSTOMER_JWKS_URL=${CLERK_CUSTOMER_JWKS_URL}" \
  "CLERK_MERCHANT_PUBLISHABLE_KEY=${CLERK_MERCHANT_PUBLISHABLE_KEY}" \
  "CLERK_MERCHANT_SECRET_KEY=${CLERK_MERCHANT_SECRET_KEY}" \
  "CLERK_MERCHANT_JWKS_URL=${CLERK_MERCHANT_JWKS_URL}" \
  "CLERK_ADMIN_PUBLISHABLE_KEY=${CLERK_ADMIN_PUBLISHABLE_KEY}" \
  "CLERK_ADMIN_SECRET_KEY=${CLERK_ADMIN_SECRET_KEY}" \
  "CLERK_ADMIN_JWKS_URL=${CLERK_ADMIN_JWKS_URL}" \
  "CLERK_DRIVER_PUBLISHABLE_KEY=${CLERK_DRIVER_PUBLISHABLE_KEY}" \
  "CLERK_DRIVER_SECRET_KEY=${CLERK_DRIVER_SECRET_KEY}" \
  "CLERK_DRIVER_JWKS_URL=${CLERK_DRIVER_JWKS_URL}"

echo "✓ 12 Clerk secrets set in Doppler"
echo "Next: bash upload-clerk-to-github.sh (publishable keys for CI builds)"
echo "Then: trigger Deploy workflow"
