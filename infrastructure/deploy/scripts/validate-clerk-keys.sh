#!/usr/bin/env bash
# Validate Clerk keys before Doppler upload.
# Supports:
#   CLERK_MODE=enterprise (default) — 4 isolated apps (12 keys)
#   CLERK_MODE=unified — one Platform triad (pk/sk/jwks)
#
# Phase 6: validation only. Does not mutate Doppler.
# Production upload remains a manual human gate (upload-clerk-to-doppler.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${1:-${SCRIPT_DIR}/clerk-keys.local.env}"

if [ ! -f "$ENV_FILE" ]; then
  # Prefer repo env/clerk.env when present
  if [ -f "${SCRIPT_DIR}/../../../env/clerk.env" ]; then
    ENV_FILE="${SCRIPT_DIR}/../../../env/clerk.env"
  else
    echo "Missing ${ENV_FILE}" >&2
    echo "Copy env/clerk.env.example → env/clerk.env (or clerk-keys.template.env)." >&2
    exit 1
  fi
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }
warn() { echo "WARN  $*"; }

check_key() {
  local name="$1" value="$2" prefix="$3"
  if [ -z "${value}" ] || [ "${value}" = "${prefix}_" ]; then
    fail "${name} is empty or placeholder"
  fi
  case "$value" in
    ${prefix}_*) pass "${name} format" ;;
    *) fail "${name} must start with ${prefix}_" ;;
  esac
}

check_jwks() {
  local portal="$1" url="$2"
  if [ -z "$url" ] || [[ "$url" == *YOUR_INSTANCE* ]]; then
    fail "${portal} JWKS URL not set"
  fi
  local body
  body="$(curl -sf -m 10 "$url" || true)"
  if [ -z "$body" ]; then
    fail "${portal} JWKS unreachable: ${url}"
  fi
  local count
  count="$(echo "$body" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('keys',[])))")"
  if [ "$count" -lt 1 ]; then
    fail "${portal} JWKS has no keys"
  fi
  pass "${portal} JWKS (${count} key(s))"
}

MODE="$(echo "${CLERK_MODE:-enterprise}" | tr '[:upper:]' '[:lower:]')"
# Auto-detect unified triad when mode unset/enterprise but only platform keys present
if [ "$MODE" != "unified" ]; then
  if [ -n "${CLERK_PUBLISHABLE_KEY:-}${CLERK_UNIFIED_PUBLISHABLE_KEY:-}" ] \
    && [ -n "${CLERK_SECRET_KEY:-}${CLERK_UNIFIED_SECRET_KEY:-}" ] \
    && [ -n "${CLERK_JWKS_URL:-}${CLERK_UNIFIED_JWKS_URL:-}" ] \
    && [ -z "${CLERK_CUSTOMER_PUBLISHABLE_KEY:-}" ]; then
    MODE="unified"
  fi
fi

echo "Validating ${ENV_FILE} (mode=${MODE})..."

if [ "$MODE" = "unified" ]; then
  PUB="${CLERK_UNIFIED_PUBLISHABLE_KEY:-${CLERK_PUBLISHABLE_KEY:-}}"
  SEC="${CLERK_UNIFIED_SECRET_KEY:-${CLERK_SECRET_KEY:-}}"
  JWKS="${CLERK_UNIFIED_JWKS_URL:-${CLERK_JWKS_URL:-}}"

  if [[ "$PUB" == pk_test_* ]]; then
    warn "CLERK_PUBLISHABLE_KEY is pk_test_ — use Production (pk_live_) before go-live"
  fi
  if [[ "$SEC" == sk_test_* ]]; then
    warn "CLERK_SECRET_KEY is sk_test_ — use Production (sk_live_) before go-live"
  fi
  if [[ "$PUB" == pk_live_* && "$SEC" == sk_test_* ]]; then
    fail "env mismatch: publishable is live but secret is test"
  fi
  if [[ "$PUB" == pk_test_* && "$SEC" == sk_live_* ]]; then
    fail "env mismatch: publishable is test but secret is live"
  fi

  check_key "CLERK_PUBLISHABLE_KEY" "$PUB" "pk"
  check_key "CLERK_SECRET_KEY" "$SEC" "sk"
  check_jwks "PLATFORM" "$JWKS"
  pass "Unified Platform Clerk app validated (local only — do not auto-upload to Doppler prod)"
  exit 0
fi

for portal in CUSTOMER MERCHANT ADMIN DRIVER; do
  pub_var="CLERK_${portal}_PUBLISHABLE_KEY"
  sec_var="CLERK_${portal}_SECRET_KEY"
  jwks_var="CLERK_${portal}_JWKS_URL"
  pub_val="${!pub_var:-}"
  sec_val="${!sec_var:-}"
  jwks_val="${!jwks_var:-}"

  if [[ "$pub_val" == pk_test_* ]]; then
    warn "${pub_var} is pk_test_ — use Production (pk_live_) before go-live"
  fi
  if [[ "$sec_val" == sk_test_* ]]; then
    warn "${sec_var} is sk_test_ — use Production (sk_live_) before go-live"
  fi
  if [[ "$pub_val" == pk_live_* && "$sec_val" == sk_test_* ]]; then
    fail "${portal}: env mismatch — publishable live / secret test"
  fi
  if [[ "$pub_val" == pk_test_* && "$sec_val" == sk_live_* ]]; then
    fail "${portal}: env mismatch — publishable test / secret live"
  fi

  check_key "$pub_var" "$pub_val" "pk"
  check_key "$sec_var" "$sec_val" "sk"
  check_jwks "$portal" "$jwks_val"
done

pass "All 4 Clerk apps validated — upload to Doppler is a manual human gate"
