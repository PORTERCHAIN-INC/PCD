#!/usr/bin/env bash
# Ensure PUBLIC_INGEST_API_KEY exists in Doppler pcd/prd (website → API inquiry → CRM leads).
# Generates a new key only when missing/empty. Never prints the key value.
#
# Usage:
#   bash infrastructure/deploy/scripts/upload-ingest-to-doppler.sh
#   DOPPLER_TOKEN=dp.st… bash infrastructure/deploy/scripts/upload-ingest-to-doppler.sh
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
set -euo pipefail

PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

existing="$(doppler secrets get PUBLIC_INGEST_API_KEY --project "$PROJECT" --config "$CONFIG" --plain 2>/dev/null || true)"
if [[ -n "${existing}" ]]; then
  echo "PUBLIC_INGEST_API_KEY already set in Doppler ${PROJECT}/${CONFIG} (not rotated)."
  exit 0
fi

key="$(openssl rand -hex 32)"
doppler secrets set "PUBLIC_INGEST_API_KEY=${key}" --project "$PROJECT" --config "$CONFIG"
echo "Uploaded PUBLIC_INGEST_API_KEY to Doppler ${PROJECT}/${CONFIG}."
echo "Next: deploy or on droplet run sync-secrets.sh and recreate api + web."
