#!/usr/bin/env bash
# Set PCD project mode by writing APP_ENV into env/.env (boot-time SoT).
# Jeff Dean: change config, then restart — never flip a live production process.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/env/.env"
MODE="${1:-}"

usage() {
  cat <<'EOF'
Usage: pnpm mode:set <development|testing|production>

Maps to APP_ENV (canonical after API normalize):
  development → local
  testing     → test
  production  → production

Then restart API and portals. Companion flags (only legal in development):
  CLERK_DEV_BYPASS, STRIPE_MOCK
EOF
  exit 1
}

case "$MODE" in
  development|dev) APP_ENV_VALUE=local ;;
  testing|test) APP_ENV_VALUE=test ;;
  production|prod) APP_ENV_VALUE=production ;;
  -h|--help|"" ) usage ;;
  * )
    echo "Unknown mode: $MODE" >&2
    usage
    ;;
esac

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "${ROOT}/env/api.env.example" ]]; then
    echo "Creating $ENV_FILE from api.env.example (edit secrets after)."
    # Prefer compose/.env style if present; else copy example keys for APP_ENV only
    if [[ -f "${ROOT}/env/.env.example" ]]; then
      cp "${ROOT}/env/.env.example" "$ENV_FILE"
    else
      echo "APP_ENV=${APP_ENV_VALUE}" > "$ENV_FILE"
    fi
  else
    echo "APP_ENV=${APP_ENV_VALUE}" > "$ENV_FILE"
  fi
fi

if grep -qE '^APP_ENV=' "$ENV_FILE"; then
  # portable in-place replace
  tmp="$(mktemp)"
  sed -E "s/^APP_ENV=.*/APP_ENV=${APP_ENV_VALUE}/" "$ENV_FILE" > "$tmp"
  mv "$tmp" "$ENV_FILE"
else
  printf '\nAPP_ENV=%s\n' "$APP_ENV_VALUE" >> "$ENV_FILE"
fi

# Keep apps/api/.env in sync when present (API Settings often loads that file).
API_ENV="${ROOT}/apps/api/.env"
if [[ -f "$API_ENV" ]]; then
  if grep -qE '^APP_ENV=' "$API_ENV"; then
    tmp="$(mktemp)"
    sed -E "s/^APP_ENV=.*/APP_ENV=${APP_ENV_VALUE}/" "$API_ENV" > "$tmp"
    mv "$tmp" "$API_ENV"
  else
    printf '\nAPP_ENV=%s\n' "$APP_ENV_VALUE" >> "$API_ENV"
  fi
fi

echo "Project mode → ${MODE} (APP_ENV=${APP_ENV_VALUE})"
echo "Updated: $ENV_FILE"
[[ -f "$API_ENV" ]] && echo "Updated: $API_ENV"
case "$APP_ENV_VALUE" in
  local)
    echo "Legal companion flags: CLERK_DEV_BYPASS=true, STRIPE_MOCK=true (optional)."
    ;;
  test)
    echo "Testing mode: auth bypass and Stripe mock stay blocked."
    ;;
  production)
    echo "Production mode: CLERK_DEV_BYPASS must be false; live Clerk required."
    ;;
esac
echo "Restart required: stop and start API + portals (e.g. pnpm dev:stop && pnpm dev:start)."
