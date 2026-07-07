#!/usr/bin/env bash
# Explicitly remove legacy single-app Clerk keys from Doppler after enterprise keys are verified.
# sync-secrets.sh no longer deletes these automatically.
set -euo pipefail

PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"

command -v doppler >/dev/null || { echo "Install: brew install dopplerhq/cli/doppler" >&2; exit 1; }

export DOPPLER_PROJECT="${DOPPLER_PROJECT:-pcd}"
export DOPPLER_CONFIG="${DOPPLER_CONFIG:-prd}"

if [ -z "${DOPPLER_TOKEN:-}" ]; then
  doppler me >/dev/null 2>&1 || doppler login
else
  export DOPPLER_TOKEN
fi

if ! doppler secrets get CLERK_CUSTOMER_SECRET_KEY --project "$PROJECT" --config "$CONFIG" --plain >/dev/null 2>&1; then
  echo "Refusing to prune: CLERK_CUSTOMER_SECRET_KEY not set in Doppler" >&2
  exit 1
fi

echo "Removing legacy CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY, CLERK_JWKS_URL from ${PROJECT}/${CONFIG}..."
doppler secrets delete CLERK_SECRET_KEY CLERK_PUBLISHABLE_KEY CLERK_JWKS_URL \
  --project "$PROJECT" \
  --config "$CONFIG" \
  --yes
echo "✓ Legacy Clerk keys removed from Doppler"
