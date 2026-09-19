#!/usr/bin/env bash
# Upload lead-ingest / CAPI / territory secrets to Doppler pcd/prd.
# Generates GOOGLE_LEAD_WEBHOOK_SECRET + SOCIAL_LEAD_WEBHOOK_SECRET when missing.
# Copies vendor tokens from LEADS_ENV (default apps/api/.env) when present — never prints values.
#
# Usage:
#   bash infrastructure/deploy/scripts/upload-leads-to-doppler.sh
#   LEADS_ENV=/path/to/leads-keys.local.env bash infrastructure/deploy/scripts/upload-leads-to-doppler.sh
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
LEADS_ENV="${LEADS_ENV:-$ROOT/apps/api/.env}"

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

get_local() {
  local key="$1"
  if [[ ! -f "$LEADS_ENV" ]]; then
    return 0
  fi
  grep -E "^${key}=" "$LEADS_ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

doppler_get() {
  local key="$1"
  doppler secrets get "$key" --project "$PROJECT" --config "$CONFIG" --plain 2>/dev/null || true
}

ensure_generated() {
  local key="$1"
  local existing
  existing="$(doppler_get "$key")"
  if [[ -n "$existing" ]]; then
    echo "${key}: already set (not rotated)"
    return 0
  fi
  local local_val
  local_val="$(get_local "$key")"
  if [[ -n "$local_val" ]]; then
    doppler secrets set "${key}=${local_val}" --project "$PROJECT" --config "$CONFIG" >/dev/null
    echo "${key}: uploaded from LEADS_ENV"
    return 0
  fi
  local gen
  gen="$(openssl rand -hex 32)"
  doppler secrets set "${key}=${gen}" --project "$PROJECT" --config "$CONFIG" >/dev/null
  echo "${key}: generated and uploaded"
}

upload_if_local() {
  local key="$1"
  local local_val
  local_val="$(get_local "$key")"
  if [[ -z "$local_val" ]]; then
    echo "${key}: skip (not in LEADS_ENV)"
    return 0
  fi
  local existing
  existing="$(doppler_get "$key")"
  if [[ -n "$existing" ]]; then
    echo "${key}: already set in Doppler (not overwritten — delete in Doppler to replace)"
    return 0
  fi
  doppler secrets set "${key}=${local_val}" --project "$PROJECT" --config "$CONFIG" >/dev/null
  echo "${key}: uploaded from LEADS_ENV"
}

echo "Doppler ${PROJECT}/${CONFIG} — lead ingest keys"
ensure_generated GOOGLE_LEAD_WEBHOOK_SECRET
ensure_generated SOCIAL_LEAD_WEBHOOK_SECRET

# Vendor / ops keys — only when present locally and missing in Doppler
for key in \
  META_APP_SECRET \
  META_WEBHOOK_VERIFY_TOKEN \
  META_CAPI_ACCESS_TOKEN \
  META_PIXEL_ID \
  LINKEDIN_CAPI_TOKEN \
  LINKEDIN_CONVERSION_URN \
  LEAD_TERRITORY_MAP_JSON \
  REFERRAL_CREDIT_CENTS \
  PUBLIC_INGEST_API_KEY
do
  upload_if_local "$key"
done

echo "Done. Next: on droplet run sync-secrets.sh and recreate api (+ website if PUBLIC_INGEST changed)."
echo "Callbacks: /v1/public/leads/webhooks/{meta,google,linkedin,x,youtube}"
