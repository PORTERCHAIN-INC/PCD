#!/usr/bin/env bash
# Validate Clerk keys before Doppler upload.
# Canonical:
#   CLERK_MODE=platform_driver — Platform triad + Driver triad
# Retired (script fails):
#   CLERK_MODE=unified | enterprise
#
# Validation only. Does not mutate Doppler.
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

MODE="$(echo "${CLERK_MODE:-platform_driver}" | tr '[:upper:]' '[:lower:]')"
# Normalize aliases
if [ "$MODE" = "dual" ] || [ "$MODE" = "platform+driver" ]; then
  MODE="platform_driver"
fi
if [ "$MODE" = "unified" ] || [ "$MODE" = "enterprise" ]; then
  fail "CLERK_MODE=${MODE} is retired — use platform_driver (Platform + Driver)"
fi

echo "Validating ${ENV_FILE} (mode=${MODE})..."

if [ "$MODE" = "platform_driver" ]; then
  # Expand Platform → customer/merchant/admin when only ADMIN/triad present
  PLATFORM_PK="${CLERK_PUBLISHABLE_KEY:-${CLERK_ADMIN_PUBLISHABLE_KEY:-}}"
  PLATFORM_SK="${CLERK_SECRET_KEY:-${CLERK_ADMIN_SECRET_KEY:-}}"
  PLATFORM_JWKS="${CLERK_JWKS_URL:-${CLERK_ADMIN_JWKS_URL:-}}"
  CLERK_CUSTOMER_PUBLISHABLE_KEY="${CLERK_CUSTOMER_PUBLISHABLE_KEY:-$PLATFORM_PK}"
  CLERK_CUSTOMER_SECRET_KEY="${CLERK_CUSTOMER_SECRET_KEY:-$PLATFORM_SK}"
  CLERK_CUSTOMER_JWKS_URL="${CLERK_CUSTOMER_JWKS_URL:-$PLATFORM_JWKS}"
  CLERK_MERCHANT_PUBLISHABLE_KEY="${CLERK_MERCHANT_PUBLISHABLE_KEY:-$PLATFORM_PK}"
  CLERK_MERCHANT_SECRET_KEY="${CLERK_MERCHANT_SECRET_KEY:-$PLATFORM_SK}"
  CLERK_MERCHANT_JWKS_URL="${CLERK_MERCHANT_JWKS_URL:-$PLATFORM_JWKS}"
  CLERK_ADMIN_PUBLISHABLE_KEY="${CLERK_ADMIN_PUBLISHABLE_KEY:-$PLATFORM_PK}"
  CLERK_ADMIN_SECRET_KEY="${CLERK_ADMIN_SECRET_KEY:-$PLATFORM_SK}"
  CLERK_ADMIN_JWKS_URL="${CLERK_ADMIN_JWKS_URL:-$PLATFORM_JWKS}"
  # Fall through to 4-slot validation below
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

# Suggested policy values (human pastes into clerk-keys.local.env / Doppler)
issuer_from_jwks() {
  local u="${1:-}"
  u="${u%%/.well-known/jwks.json}"
  u="${u%/}"
  echo "$u"
}

suggest_issuers=""
for jwks in \
  "${CLERK_JWKS_URL:-${CLERK_ADMIN_JWKS_URL:-}}" \
  "${CLERK_DRIVER_JWKS_URL:-}"; do
  [ -n "$jwks" ] || continue
  iss="$(issuer_from_jwks "$jwks")"
  [ -n "$iss" ] || continue
  case ",${suggest_issuers}," in
    *",${iss},"*) ;;
    *) suggest_issuers="${suggest_issuers:+$suggest_issuers,}${iss}" ;;
  esac
done

suggest_parties="https://porterchain.com,https://merchant.porterchain.com,https://driver.porterchain.com,https://customer.porterchain.com,http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

echo ""
echo "--- Doppler policy (optional but recommended for prod) ---"
if [ -n "${CLERK_AUTHORIZED_ISSUERS:-}" ]; then
  pass "CLERK_AUTHORIZED_ISSUERS already set"
else
  warn "CLERK_AUTHORIZED_ISSUERS empty — suggested:"
  echo "  CLERK_AUTHORIZED_ISSUERS=${suggest_issuers}"
fi
if [ -n "${CLERK_AUTHORIZED_PARTIES:-}" ]; then
  pass "CLERK_AUTHORIZED_PARTIES already set"
else
  warn "CLERK_AUTHORIZED_PARTIES empty — suggested (no admin: staff IdP):"
  echo "  CLERK_AUTHORIZED_PARTIES=${suggest_parties}"
fi
if [ -n "${CLERK_WEBHOOK_SIGNING_SECRET:-}" ]; then
  pass "CLERK_WEBHOOK_SIGNING_SECRET already set"
else
  warn "CLERK_WEBHOOK_SIGNING_SECRET empty — set from Clerk Dashboard → Webhooks → Signing secret"
fi
