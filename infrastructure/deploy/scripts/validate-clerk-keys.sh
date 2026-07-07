#!/usr/bin/env bash
# Validate 4-app Clerk keys before Doppler upload (§0.5).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${1:-${SCRIPT_DIR}/clerk-keys.local.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing ${ENV_FILE}" >&2
  echo "Copy clerk-keys.template.env → clerk-keys.local.env and fill in keys." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

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

echo "Validating ${ENV_FILE}..."

for portal in CUSTOMER MERCHANT ADMIN DRIVER; do
  pub_var="CLERK_${portal}_PUBLISHABLE_KEY"
  sec_var="CLERK_${portal}_SECRET_KEY"
  jwks_var="CLERK_${portal}_JWKS_URL"
  pub_val="${!pub_var:-}"
  sec_val="${!sec_var:-}"
  jwks_val="${!jwks_var:-}"

  if [[ "$pub_val" == pk_test_* ]]; then
    echo "WARN  ${pub_var} is pk_test_ — use Production (pk_live_) before go-live"
  fi
  if [[ "$sec_val" == sk_test_* ]]; then
    echo "WARN  ${sec_var} is sk_test_ — use Production (sk_live_) before go-live"
  fi

  check_key "$pub_var" "$pub_val" "pk"
  check_key "$sec_var" "$sec_val" "sk"
  check_jwks "$portal" "$jwks_val"
done

pass "All 4 Clerk apps validated — run upload-clerk-to-doppler.sh"
