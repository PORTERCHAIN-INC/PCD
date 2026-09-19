#!/usr/bin/env bash
# Upload ZeptoMail transactional secrets to Doppler pcd/prd.
# Reads infrastructure/deploy/scripts/mail-keys.local.env (gitignored).
# Never prints the Send Mail Token.
#
# Usage:
#   cp infrastructure/deploy/scripts/mail-keys.local.env.example \
#      infrastructure/deploy/scripts/mail-keys.local.env
#   # set MAIL_PASSWORD to the ZeptoMail Send Mail Token
#   bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh
#   MAIL_ENV=/path/to/mail.env bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh
#
# Requires: doppler CLI + login (or DOPPLER_TOKEN)
# Production delivery is HTTPS (api.zeptomail.ca). Host/user/transport are forced
# here so a Zoho Mail SMTP host or Mailpit localhost cannot be uploaded.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT="${DOPPLER_PROJECT:-pcd}"
CONFIG="${DOPPLER_CONFIG:-prd}"
MAIL_ENV="${MAIL_ENV:-$ROOT/infrastructure/deploy/scripts/mail-keys.local.env}"

if [[ ! -f "$MAIL_ENV" ]]; then
  echo "Missing $MAIL_ENV" >&2
  echo "Copy infrastructure/deploy/scripts/mail-keys.local.env.example and set MAIL_PASSWORD." >&2
  echo "ZeptoMail CA → Mail Agent → Send Mail Token. Do not use smtp.zohocloud.ca or apps/api/.env (Mailpit)." >&2
  exit 1
fi

get_kv() {
  local key="$1"
  grep -E "^${key}=" "$MAIL_ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

MAIL_PASSWORD="$(get_kv MAIL_PASSWORD)"
MAIL_FROM_ADDRESS="$(get_kv MAIL_FROM_ADDRESS)"
MAIL_FROM_ADDRESS2="$(get_kv MAIL_FROM_ADDRESS2)"
MAIL_FROM_ADDRESS3="$(get_kv MAIL_FROM_ADDRESS3)"
MAIL_FROM_NAME="$(get_kv MAIL_FROM_NAME)"
PORTERCHAIN_OPS_EMAILS="$(get_kv PORTERCHAIN_OPS_EMAILS)"

# Forced production contract — ignore host/user from the file.
MAIL_MAILER="smtp"
MAIL_HOST="smtp.zeptomail.ca"
MAIL_PORT="587"
MAIL_USERNAME="emailapikey"
MAIL_ENCRYPTION="tls"
MAIL_TRANSPORT="https"
ZEPTOMAIL_API_URL="https://api.zeptomail.ca/v1.1/email"
MAIL_FROM_ADDRESS="${MAIL_FROM_ADDRESS:-noreply@porterchain.com}"
MAIL_FROM_ADDRESS2="${MAIL_FROM_ADDRESS2:-sales@porterchain.com}"
MAIL_FROM_ADDRESS3="${MAIL_FROM_ADDRESS3:-ravi@porterchain.com}"
MAIL_FROM_NAME="${MAIL_FROM_NAME:-Porterchain}"
PORTERCHAIN_OPS_EMAILS="${PORTERCHAIN_OPS_EMAILS:-ops@porterchain.com}"

if [[ -z "${MAIL_PASSWORD}" ]]; then
  echo "MAIL_PASSWORD is empty in $MAIL_ENV" >&2
  echo "Set it to the ZeptoMail Send Mail Token (Zoho-enczapikey … or the raw token)." >&2
  exit 1
fi

case "${MAIL_PASSWORD}" in
  mailpit|changeme|REPLACE_ME|"********"|password)
    echo "MAIL_PASSWORD in $MAIL_ENV is a placeholder, not a ZeptoMail token" >&2
    exit 1
    ;;
esac

if [[ "${#MAIL_PASSWORD}" -lt 20 ]]; then
  echo "MAIL_PASSWORD looks too short to be a ZeptoMail Send Mail Token" >&2
  exit 1
fi

command -v doppler >/dev/null || {
  echo "Install Doppler CLI: brew install dopplerhq/cli/doppler" >&2
  exit 1
}

if [[ -z "${DOPPLER_TOKEN:-}" ]]; then
  doppler me >/dev/null 2>&1 || doppler login
fi

echo "Uploading ZeptoMail to Doppler project=$PROJECT config=$CONFIG (token not printed)…"
echo "  MAIL_HOST=$MAIL_HOST"
echo "  MAIL_TRANSPORT=$MAIL_TRANSPORT"
echo "  ZEPTOMAIL_API_URL=$ZEPTOMAIL_API_URL"
echo "  MAIL_USERNAME=$MAIL_USERNAME"
echo "  MAIL_FROM_ADDRESS=$MAIL_FROM_ADDRESS"
echo "  source=$MAIL_ENV"

# --silent avoids printing secret values (incl. MAIL_PASSWORD) in CLI tables.
doppler secrets set \
  "MAIL_MAILER=${MAIL_MAILER}" \
  "MAIL_HOST=${MAIL_HOST}" \
  "MAIL_PORT=${MAIL_PORT}" \
  "MAIL_USERNAME=${MAIL_USERNAME}" \
  "MAIL_PASSWORD=${MAIL_PASSWORD}" \
  "MAIL_ENCRYPTION=${MAIL_ENCRYPTION}" \
  "MAIL_TRANSPORT=${MAIL_TRANSPORT}" \
  "ZEPTOMAIL_API_URL=${ZEPTOMAIL_API_URL}" \
  "MAIL_FROM_ADDRESS=${MAIL_FROM_ADDRESS}" \
  "MAIL_FROM_ADDRESS2=${MAIL_FROM_ADDRESS2}" \
  "MAIL_FROM_ADDRESS3=${MAIL_FROM_ADDRESS3}" \
  "MAIL_FROM_NAME=${MAIL_FROM_NAME}" \
  "PORTERCHAIN_OPS_EMAILS=${PORTERCHAIN_OPS_EMAILS}" \
  --project "$PROJECT" \
  --config "$CONFIG" \
  --silent

echo "Done. Next deploy (or on droplet: bash sync-secrets.sh) writes /opt/porterchain/.env"
echo "Verify names only: doppler secrets --only-names --project $PROJECT --config $CONFIG | grep -E 'MAIL_|ZEPTOMAIL_'"
