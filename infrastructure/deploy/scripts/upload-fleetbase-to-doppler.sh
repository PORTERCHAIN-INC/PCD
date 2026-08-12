#!/usr/bin/env bash
# Upload Fleetbase bridge / SSO secrets to Doppler pcd/prd.
# Reads from apps/api/.env by default (gitignored). Never prints secret values.
#
# Usage:
#   bash infrastructure/deploy/scripts/upload-fleetbase-to-doppler.sh
#   MAIL_ENV=/path/to/.env bash …   # unused; uses FLEETBASE_ENV
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
#
# Refuses localhost / 127.0.0.1 API or console URLs (prod must point at a
# hosted Fleetbase). Keeps FLEETBASE_DISPATCH_BRIDGE=false unless explicitly
# FORCE_DISPATCH_BRIDGE=true and webhook secret is set.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
FLEETBASE_ENV="${FLEETBASE_ENV:-$ROOT/apps/api/.env}"

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

if [[ ! -f "$FLEETBASE_ENV" ]]; then
  echo "Missing $FLEETBASE_ENV — set FLEETBASE_* there first." >&2
  exit 1
fi

get_kv() {
  local key="$1"
  grep -E "^${key}=" "$FLEETBASE_ENV" | tail -1 | cut -d= -f2- || true
}

FLEETBASE_API_URL="$(get_kv FLEETBASE_API_URL)"
FLEETBASE_CONSOLE_URL="$(get_kv FLEETBASE_CONSOLE_URL)"
FLEETBASE_API_KEY="$(get_kv FLEETBASE_API_KEY)"
FLEETBASE_DEFAULT_COMPANY_UUID="$(get_kv FLEETBASE_DEFAULT_COMPANY_UUID)"
FLEETBASE_WEBHOOK_SECRET="$(get_kv FLEETBASE_WEBHOOK_SECRET)"
FLEETBASE_SSO_ENABLED="$(get_kv FLEETBASE_SSO_ENABLED)"
FLEETBASE_DISPATCH_BRIDGE="$(get_kv FLEETBASE_DISPATCH_BRIDGE)"
JWT_SECRET="$(get_kv JWT_SECRET)"
SSO_JWT_SECRET="$(get_kv SSO_JWT_SECRET)"

FLEETBASE_SSO_ENABLED="${FLEETBASE_SSO_ENABLED:-false}"
FLEETBASE_DISPATCH_BRIDGE="${FLEETBASE_DISPATCH_BRIDGE:-false}"
FLEETBASE_CONSOLE_URL="${FLEETBASE_CONSOLE_URL:-}"

is_local_url() {
  local u="$1"
  [[ -z "$u" ]] && return 1
  [[ "$u" == *"localhost"* || "$u" == *"127.0.0.1"* ]] && return 0
  return 1
}

if is_local_url "$FLEETBASE_API_URL" || is_local_url "$FLEETBASE_CONSOLE_URL"; then
  echo "Refusing to upload localhost Fleetbase URLs to production Doppler." >&2
  echo "Set FLEETBASE_API_URL / FLEETBASE_CONSOLE_URL to https://… hosts first." >&2
  echo "Local SSO stays in apps/api/.env only." >&2
  exit 1
fi

if [[ -z "${FLEETBASE_API_URL}" || -z "${FLEETBASE_API_KEY}" || -z "${FLEETBASE_DEFAULT_COMPANY_UUID}" ]]; then
  echo "Need FLEETBASE_API_URL, FLEETBASE_API_KEY, FLEETBASE_DEFAULT_COMPANY_UUID in $FLEETBASE_ENV" >&2
  exit 1
fi

if [[ "${FLEETBASE_DISPATCH_BRIDGE}" == "true" && -z "${FLEETBASE_WEBHOOK_SECRET}" && "${FORCE_DISPATCH_BRIDGE:-}" != "true" ]]; then
  echo "FLEETBASE_DISPATCH_BRIDGE=true requires FLEETBASE_WEBHOOK_SECRET (or FORCE_DISPATCH_BRIDGE=true)." >&2
  exit 1
fi

echo "Uploading Fleetbase keys to Doppler project=$PROJECT config=$CONFIG (secrets not printed)…"
echo "  FLEETBASE_API_URL=${FLEETBASE_API_URL}"
echo "  FLEETBASE_CONSOLE_URL=${FLEETBASE_CONSOLE_URL:-"(empty)"}"
echo "  FLEETBASE_SSO_ENABLED=${FLEETBASE_SSO_ENABLED}"
echo "  FLEETBASE_DISPATCH_BRIDGE=${FLEETBASE_DISPATCH_BRIDGE}"
echo "  FLEETBASE_DEFAULT_COMPANY_UUID=${FLEETBASE_DEFAULT_COMPANY_UUID}"
echo "  FLEETBASE_API_KEY=(${#FLEETBASE_API_KEY} chars)"

ARGS=(
  "FLEETBASE_API_URL=${FLEETBASE_API_URL}"
  "FLEETBASE_API_KEY=${FLEETBASE_API_KEY}"
  "FLEETBASE_DEFAULT_COMPANY_UUID=${FLEETBASE_DEFAULT_COMPANY_UUID}"
  "FLEETBASE_SSO_ENABLED=${FLEETBASE_SSO_ENABLED}"
  "FLEETBASE_DISPATCH_BRIDGE=${FLEETBASE_DISPATCH_BRIDGE}"
)

if [[ -n "${FLEETBASE_CONSOLE_URL}" ]]; then
  ARGS+=("FLEETBASE_CONSOLE_URL=${FLEETBASE_CONSOLE_URL}")
fi
if [[ -n "${FLEETBASE_WEBHOOK_SECRET}" ]]; then
  ARGS+=("FLEETBASE_WEBHOOK_SECRET=${FLEETBASE_WEBHOOK_SECRET}")
fi
# Prefer dedicated SSO secret; fall back to JWT_SECRET already in Doppler.
if [[ -n "${SSO_JWT_SECRET}" ]]; then
  ARGS+=("SSO_JWT_SECRET=${SSO_JWT_SECRET}")
elif [[ -n "${JWT_SECRET}" && "${JWT_SECRET}" != "dev-sso-secret-change-in-production" ]]; then
  ARGS+=("JWT_SECRET=${JWT_SECRET}")
fi

doppler secrets set "${ARGS[@]}" \
  --project "$PROJECT" \
  --config "$CONFIG" \
  --silent

echo "Done. Next: GitHub Actions Deploy (or on droplet: bash sync-secrets.sh && recreate api)."
