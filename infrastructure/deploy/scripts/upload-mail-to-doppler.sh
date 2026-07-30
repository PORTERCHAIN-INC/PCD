#!/usr/bin/env bash
# Upload Zoho SMTP (MAIL_*) secrets to Doppler pcd/prd for the live droplet.
# Reads from apps/api/.env by default (gitignored). Never prints password values.
#
# Usage:
#   bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh
#   MAIL_ENV=/path/to/.env bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
MAIL_ENV="${MAIL_ENV:-$ROOT/apps/api/.env}"

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

if [[ ! -f "$MAIL_ENV" ]]; then
  echo "Missing $MAIL_ENV — set MAIL_USERNAME / MAIL_PASSWORD there first." >&2
  exit 1
fi

# Load only MAIL_* / PORTERCHAIN_OPS_EMAILS (do not source entire .env into this shell's export of secrets to logs)
get_kv() {
  local key="$1"
  # shellcheck disable=SC2002
  grep -E "^${key}=" "$MAIL_ENV" | tail -1 | cut -d= -f2-
}

MAIL_HOST="$(get_kv MAIL_HOST)"
MAIL_PORT="$(get_kv MAIL_PORT)"
MAIL_USERNAME="$(get_kv MAIL_USERNAME)"
MAIL_PASSWORD="$(get_kv MAIL_PASSWORD)"
MAIL_ENCRYPTION="$(get_kv MAIL_ENCRYPTION)"
MAIL_FROM_ADDRESS="$(get_kv MAIL_FROM_ADDRESS)"
MAIL_FROM_ADDRESS2="$(get_kv MAIL_FROM_ADDRESS2)"
MAIL_FROM_ADDRESS3="$(get_kv MAIL_FROM_ADDRESS3)"
MAIL_FROM_NAME="$(get_kv MAIL_FROM_NAME)"
MAIL_MAILER="$(get_kv MAIL_MAILER)"
PORTERCHAIN_OPS_EMAILS="$(get_kv PORTERCHAIN_OPS_EMAILS)"

# Production defaults when local file only has partial keys
MAIL_MAILER="${MAIL_MAILER:-smtp}"
MAIL_HOST="${MAIL_HOST:-smtp.zohocloud.ca}"
MAIL_PORT="${MAIL_PORT:-465}"
MAIL_ENCRYPTION="${MAIL_ENCRYPTION:-ssl}"
MAIL_FROM_ADDRESS="${MAIL_FROM_ADDRESS:-ops@porterchain.com}"
MAIL_FROM_ADDRESS2="${MAIL_FROM_ADDRESS2:-sales@porterchain.com}"
MAIL_FROM_ADDRESS3="${MAIL_FROM_ADDRESS3:-ravi@porterchain.com}"
MAIL_FROM_NAME="${MAIL_FROM_NAME:-Porterchain}"
PORTERCHAIN_OPS_EMAILS="${PORTERCHAIN_OPS_EMAILS:-ops@porterchain.com}"

if [[ -z "${MAIL_USERNAME}" || -z "${MAIL_PASSWORD}" ]]; then
  echo "MAIL_USERNAME and MAIL_PASSWORD must be set in $MAIL_ENV" >&2
  exit 1
fi

if [[ "$MAIL_HOST" == "localhost" || "$MAIL_HOST" == "127.0.0.1" ]]; then
  echo "Refusing to upload Mailpit/local host to production. Set MAIL_HOST=smtp.zohocloud.ca" >&2
  exit 1
fi

echo "Uploading Zoho MAIL_* to Doppler project=$PROJECT config=$CONFIG (password not printed)…"
echo "  MAIL_HOST=$MAIL_HOST"
echo "  MAIL_PORT=$MAIL_PORT"
echo "  MAIL_USERNAME=$MAIL_USERNAME"
echo "  MAIL_FROM_ADDRESS=$MAIL_FROM_ADDRESS"

# --silent avoids printing secret values (incl. MAIL_PASSWORD) in CLI tables.
doppler secrets set \
  "MAIL_MAILER=${MAIL_MAILER}" \
  "MAIL_HOST=${MAIL_HOST}" \
  "MAIL_PORT=${MAIL_PORT}" \
  "MAIL_USERNAME=${MAIL_USERNAME}" \
  "MAIL_PASSWORD=${MAIL_PASSWORD}" \
  "MAIL_ENCRYPTION=${MAIL_ENCRYPTION}" \
  "MAIL_FROM_ADDRESS=${MAIL_FROM_ADDRESS}" \
  "MAIL_FROM_ADDRESS2=${MAIL_FROM_ADDRESS2}" \
  "MAIL_FROM_ADDRESS3=${MAIL_FROM_ADDRESS3}" \
  "MAIL_FROM_NAME=${MAIL_FROM_NAME}" \
  "PORTERCHAIN_OPS_EMAILS=${PORTERCHAIN_OPS_EMAILS}" \
  --project "$PROJECT" \
  --config "$CONFIG" \
  --silent

echo "Done. Next deploy (or on droplet: bash sync-secrets.sh) writes /opt/porterchain/.env"
echo "Verify: doppler secrets --only-names --project $PROJECT --config $CONFIG | grep MAIL_"
