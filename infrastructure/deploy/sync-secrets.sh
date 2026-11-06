#!/usr/bin/env bash
# Sync production secrets to /opt/porterchain/.env (DD-14).
#
# Auth: self-hosted Keycloak (realm porterchain). API needs KEYCLOAK_ADMIN_CLIENT_SECRET;
# web apps need AUTH_SESSION_SECRET. Legacy CLERK_* keys are stripped from .env.
#
# Modes:
#   runtime.env present   → CI decrypted secrets/droplet.enc.yaml (sops + age) on the runner
#                           and copied it here; apply it (deploy.yml path)
#   SOPS_SECRETS_FILE set → decrypt on this host with sops + the host age key (doc 37)
#   otherwise             → write .env from CI env vars (break-glass)
#
# Usage (on droplet):
#   cd /opt/porterchain && bash sync-secrets.sh
#
# Local dry-run:
#   SOPS_SECRETS_FILE=secrets/droplet.enc.yaml bash infrastructure/deploy/sync-secrets.sh /tmp/porterchain-test

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
  KEYCLOAK_ADMIN_CLIENT_SECRET
  AUTH_SESSION_SECRET
)

env_value() {
  local key="$1"
  local line value
  line="$(grep -E "^${key}=" .env 2>/dev/null | tail -n1 || true)"
  value="${line#*=}"
  # dotenv exports may wrap values in single/double quotes.
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

# Clerk is gone (L36): drop any CLERK_* left in a legacy secret source.
strip_legacy_clerk() {
  if grep -qE "^(NEXT_PUBLIC_)?CLERK_" .env 2>/dev/null; then
    grep -v -E "^(NEXT_PUBLIC_)?CLERK_" .env > .env.tmp && mv .env.tmp .env
    echo "::warning::removed legacy CLERK_* keys from .env (delete them at the source)" >&2
  fi
}

verify_auth_env() {
  local secret
  secret="$(env_value AUTH_SESSION_SECRET)"
  if [ "${#secret}" -lt 32 ]; then
    echo "::error::AUTH_SESSION_SECRET must be at least 32 characters" >&2
    return 1
  fi
  echo "Auth: Keycloak (realm ${KEYCLOAK_REALM:-porterchain})"
  return 0
}

# Production transactional mail is ZeptoMail HTTPS, not Zoho Mail SMTP / Mailpit.
normalize_zeptomail() {
  local host pass user transport
  host="$(env_value MAIL_HOST)"
  pass="$(env_value MAIL_PASSWORD)"
  user="$(env_value MAIL_USERNAME)"
  transport="$(env_value MAIL_TRANSPORT)"
  host_lc="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]')"

  if [ -z "$pass" ]; then
    echo "::warning::ZeptoMail: MAIL_PASSWORD empty — transactional email will not send until MAIL_PASSWORD is set in secrets/droplet.enc.yaml" >&2
    return 0
  fi

  case "$host_lc" in
    ""|localhost|127.0.0.1|smtp.zohocloud.ca|smtp.zoho.com|smtp.zoho.ca)
      echo "::warning::ZeptoMail: rewriting MAIL_HOST=${host:-<empty>} → smtp.zeptomail.ca" >&2
      set_env_key MAIL_HOST smtp.zeptomail.ca
      set_env_key MAIL_PORT 587
      ;;
  esac
  if [ -z "$user" ] || [ "$user" = "mailpit" ]; then
    set_env_key MAIL_USERNAME emailapikey
  fi
  if [ -z "$transport" ] || [ "$transport" = "auto" ] || [ "$transport" = "smtp" ]; then
    set_env_key MAIL_TRANSPORT https
  fi
  if [ -z "$(env_value ZEPTOMAIL_API_URL)" ]; then
    set_env_key ZEPTOMAIL_API_URL "https://api.zeptomail.ca/v1.1/email"
  fi
  if [ -z "$(env_value MAIL_FROM_ADDRESS)" ]; then
    set_env_key MAIL_FROM_ADDRESS noreply@porterchain.com
  fi
  if [ -z "$(env_value MAIL_FROM_NAME)" ]; then
    set_env_key MAIL_FROM_NAME Porterchain
  fi
  echo "ZeptoMail: HTTPS api.zeptomail.ca (from=$(env_value MAIL_FROM_ADDRESS))"
}

write_firebase_file() {
  if [ -n "${FIREBASE_CREDENTIALS_JSON:-}" ]; then
    printf '%s' "$FIREBASE_CREDENTIALS_JSON" > secrets/firebase-service-account.json
  elif [ -f secrets/firebase-service-account.json ] && [ -s secrets/firebase-service-account.json ]; then
    : # keep existing file when the secrets file has no inline JSON
  else
    : > secrets/firebase-service-account.json
  fi
  chmod 600 secrets/firebase-service-account.json
}

extract_firebase_from_env() {
  if ! grep -q '^FIREBASE_CREDENTIALS_JSON=' .env 2>/dev/null; then
    return 0
  fi
  # Soft-fail: malformed JSON must not abort secret sync (appleboy also redacts
  # tracebacks that embed private_key material, which looks like a silent exit).
  if ! python3 - <<'PY'
import json
import re
import sys
from pathlib import Path

try:
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
    Path("secrets").mkdir(parents=True, exist_ok=True)
    Path("secrets/firebase-service-account.json").write_text(out, encoding="utf-8")
except Exception as exc:
    print(f"::warning::firebase extract skipped ({type(exc).__name__})", file=sys.stderr)
    raise SystemExit(0)
PY
  then
    echo "::warning::firebase extract command failed; continuing sync" >&2
    return 0
  fi
  chmod 600 secrets/firebase-service-account.json 2>/dev/null || true
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

# SOPS + age (doc 37) is the only secrets store.
apply_env_file() {
  local src="$1" label="$2" bytes
  bytes="$(wc -c < "$src")"
  if [ "$bytes" -lt 500 ]; then
    echo "::error::${label} too small (${bytes} bytes)" >&2
    exit 1
  fi
  if [ -s .env ]; then cp -a .env ".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"; fi
  # Copy then rename so a partial failure never leaves a truncated .env.
  cp -a "$src" .env.incoming
  mv -f .env.incoming .env
  extract_firebase_from_env
  strip_inline_firebase_from_env
  strip_legacy_clerk
  echo "Secrets applied from ${label} ($(wc -c < .env) bytes)"
}

SOPS_FILE="${SOPS_SECRETS_FILE:-}"
if [ -f "${TARGET_DIR}/runtime.env" ]; then
  apply_env_file "${TARGET_DIR}/runtime.env" "CI-staged runtime.env"
  rm -f "${TARGET_DIR}/runtime.env"
elif [ -n "${SOPS_FILE}" ]; then
  [ -f "${SOPS_FILE}" ] || { echo "::error::SOPS_SECRETS_FILE not found: ${SOPS_FILE}" >&2; exit 1; }
  command -v sops >/dev/null 2>&1 || { echo "::error::sops is not installed" >&2; exit 1; }
  tmp_env="$(mktemp "${TARGET_DIR}/.env.sops.XXXXXX")"
  trap 'rm -f "${tmp_env}"' EXIT
  sops -d --output-type dotenv "${SOPS_FILE}" > "${tmp_env}"
  if [ ! -s "${tmp_env}" ]; then echo "::error::sops decrypt produced an empty file" >&2; exit 1; fi
  apply_env_file "${tmp_env}" "SOPS (${SOPS_FILE})"
  rm -f "${tmp_env}"; trap - EXIT
else
  # Break-glass: write .env from CI env vars.
  # Expand required vars before truncating .env (bash evaluates ${VAR:?} while writing the heredoc).
  : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
  : "${KEYCLOAK_ADMIN_CLIENT_SECRET:?KEYCLOAK_ADMIN_CLIENT_SECRET is required}"
  : "${AUTH_SESSION_SECRET:?AUTH_SESSION_SECRET is required}"
  : "${STRIPE_SECRET:?STRIPE_SECRET is required}"
  : "${STRIPE_WEBHOOK_SECRET:?STRIPE_WEBHOOK_SECRET is required}"
  : "${JWT_SECRET:?JWT_SECRET is required}"
  : "${SPICEDB_PRESHARED_KEY:?SPICEDB_PRESHARED_KEY is required}"
  if [ -s .env ]; then
    cp -a .env ".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
KEYCLOAK_URL=${KEYCLOAK_URL:-https://auth.porterchain.com}
KEYCLOAK_INTERNAL_URL=${KEYCLOAK_INTERNAL_URL:-http://keycloak:8080}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-porterchain}
KEYCLOAK_ADMIN_CLIENT_SECRET=${KEYCLOAK_ADMIN_CLIENT_SECRET}
AUTH_SESSION_SECRET=${AUTH_SESSION_SECRET}
STRIPE_SECRET=${STRIPE_SECRET}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
JWT_SECRET=${JWT_SECRET}
SPICEDB_PRESHARED_KEY=${SPICEDB_PRESHARED_KEY}
SPICEDB_ENABLED=${SPICEDB_ENABLED:-true}
SPICEDB_REQUIRED=${SPICEDB_REQUIRED:-true}
SPICEDB_ENDPOINT=${SPICEDB_ENDPOINT:-spicedb:50051}
GLITCHTIP_DSN=${GLITCHTIP_DSN:-}
CORS_ORIGINS=https://porterchain.com,https://www.porterchain.com,https://admin.porterchain.com,https://merchant.porterchain.com,https://driver.porterchain.com,https://customer.porterchain.com
PORTERCHAIN_PUSH_ENABLED=${PORTERCHAIN_PUSH_ENABLED:-false}
PORTERCHAIN_PUSH_SEND=${PORTERCHAIN_PUSH_SEND:-false}
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-}
FIREBASE_WEB_VAPID_KEY=${FIREBASE_WEB_VAPID_KEY:-}
MAIL_MAILER=smtp
MAIL_HOST=${MAIL_HOST:-smtp.zeptomail.ca}
MAIL_PORT=${MAIL_PORT:-587}
MAIL_USERNAME=${MAIL_USERNAME:-emailapikey}
MAIL_PASSWORD=${MAIL_PASSWORD:-}
MAIL_ENCRYPTION=tls
MAIL_TRANSPORT=${MAIL_TRANSPORT:-https}
ZEPTOMAIL_API_URL=${ZEPTOMAIL_API_URL:-https://api.zeptomail.ca/v1.1/email}
MAIL_FROM_ADDRESS=${MAIL_FROM_ADDRESS:-noreply@porterchain.com}
MAIL_FROM_ADDRESS2=${MAIL_FROM_ADDRESS2:-sales@porterchain.com}
MAIL_FROM_ADDRESS3=${MAIL_FROM_ADDRESS3:-ravi@porterchain.com}
MAIL_FROM_NAME=${MAIL_FROM_NAME:-Porterchain}
PORTERCHAIN_OPS_EMAILS=${PORTERCHAIN_OPS_EMAILS:-ops@porterchain.com}
API_REPLICAS=${API_REPLICAS:-1}
EOF
  write_firebase_file
  echo "Secrets written from deploy environment (legacy GitHub secrets path)"
fi

write_firebase_file
chmod 600 .env
normalize_zeptomail
if ! verify_env; then
  echo "::error::sync-secrets verify_env failed" >&2
  exit 1
fi
if ! verify_auth_env; then
  echo "::error::sync-secrets verify_auth_env failed" >&2
  exit 1
fi
echo "✓ ${#REQUIRED_KEYS[@]} required keys present in .env (keycloak)"
