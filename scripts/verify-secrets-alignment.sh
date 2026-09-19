#!/usr/bin/env bash
# Check secret alignment across local, GitHub, and documented expectations.
# Prints key NAMES only — never values.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }

echo "=== Porterchain secrets alignment ==="
echo ""

# --- Local Clerk ---
CLERK_SOURCE=""
for candidate in "$ROOT/env/clerk.env" "$ROOT/infrastructure/deploy/scripts/clerk-keys.local.env"; do
  if [ -f "$candidate" ]; then
    CLERK_SOURCE="$candidate"
    break
  fi
done

if [ -n "$CLERK_SOURCE" ]; then
  if bash "$ROOT/infrastructure/deploy/scripts/validate-clerk-keys.sh" "$CLERK_SOURCE" >/dev/null 2>&1; then
    ok "Local Clerk: 12 keys in $(basename "$CLERK_SOURCE")"
  else
    fail "Local Clerk: incomplete keys in $CLERK_SOURCE"
    bash "$ROOT/infrastructure/deploy/scripts/validate-clerk-keys.sh" "$CLERK_SOURCE" || true
  fi
else
  warn "Local Clerk: no env/clerk.env — copy env/clerk.env.example"
fi

# --- GitHub (required deploy) ---
GITHUB_REQUIRED=(DEPLOY_HOST DEPLOY_USER DEPLOY_SSH_KEY DOPPLER_TOKEN)
GITHUB_BUILD=(NEXT_PUBLIC_GOOGLE_MAPS_API_KEY CLERK_CUSTOMER_PUBLISHABLE_KEY CLERK_MERCHANT_PUBLISHABLE_KEY CLERK_ADMIN_PUBLISHABLE_KEY CLERK_DRIVER_PUBLISHABLE_KEY)
GITHUB_OPTIONAL=(SENTRY_DSN NEXT_PUBLIC_SENTRY_DSN GOOGLE_MAPS_SERVER_API_KEY POSTGRES_PASSWORD JWT_SECRET STRIPE_SECRET STRIPE_WEBHOOK_SECRET)
GITHUB_LEGACY=(CLERK_SECRET_KEY CLERK_PUBLISHABLE_KEY CLERK_JWKS_URL)

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  GH_SECRETS="$(gh secret list 2>/dev/null | awk '{print $1}' | sort -u || true)"
  has_secret() { echo "$GH_SECRETS" | grep -qx "$1"; }

  for key in "${GITHUB_REQUIRED[@]}"; do
    if has_secret "$key"; then ok "GitHub required: $key"; else fail "GitHub required: $key MISSING"; fi
  done
  for key in "${GITHUB_BUILD[@]}"; do
    if has_secret "$key"; then ok "GitHub build-time: $key"; else warn "GitHub build-time: $key missing"; fi
  done

  DOPPLER_SET=false
  has_secret DOPPLER_TOKEN && DOPPLER_SET=true

  if [ "$DOPPLER_SET" = true ]; then
    ok "Runtime secrets: Doppler is SSOT (legacy GitHub runtime secrets optional)"
    for key in "${GITHUB_LEGACY[@]}"; do
      if has_secret "$key"; then warn "GitHub legacy (can remove): $key"; fi
    done
    for key in "${GITHUB_OPTIONAL[@]}"; do
      if has_secret "$key"; then warn "GitHub duplicate of Doppler (can remove): $key"; fi
    done
  else
    warn "DOPPLER_TOKEN not set — runtime secrets must live in GitHub"
    for key in POSTGRES_PASSWORD JWT_SECRET STRIPE_SECRET STRIPE_WEBHOOK_SECRET; do
      if has_secret "$key"; then ok "GitHub runtime (legacy): $key"; else fail "GitHub runtime (legacy): $key MISSING"; fi
    done
  fi

  for key in SENTRY_DSN NEXT_PUBLIC_SENTRY_DSN; do
    if has_secret "$key"; then ok "Optional: $key"; else warn "Optional gap: $key"; fi
  done
else
  warn "gh CLI not authenticated — skip GitHub checks"
fi

# --- Doppler ---
if command -v doppler >/dev/null 2>&1; then
  DOPPLER_OK=0
  if [ -n "${DOPPLER_TOKEN:-}" ]; then
    export DOPPLER_TOKEN
    DOPPLER_OK=1
  elif timeout 3 doppler me >/dev/null 2>&1; then
    DOPPLER_OK=1
  fi
  if [ "$DOPPLER_OK" -eq 1 ]; then
    DOPPLER_KEYS="$(doppler secrets --project "${DOPPLER_PROJECT:-pcd}" --config "${DOPPLER_CONFIG:-prd}" --only-names 2>/dev/null | sort || true)"
    if [ -n "$DOPPLER_KEYS" ]; then
      for key in POSTGRES_PASSWORD JWT_SECRET STRIPE_SECRET STRIPE_WEBHOOK_SECRET CLERK_CUSTOMER_SECRET_KEY; do
        if echo "$DOPPLER_KEYS" | grep -qx "$key"; then ok "Doppler: $key"; else warn "Doppler: $key missing"; fi
      done
      if echo "$DOPPLER_KEYS" | grep -qx CLERK_SECRET_KEY; then
        warn "Doppler: legacy CLERK_SECRET_KEY present — run prune-legacy-clerk-doppler.sh"
      fi
    else
      warn "Doppler: could not list secrets (check login / project access)"
    fi
  else
    warn "Doppler CLI not logged in — skip Doppler checks (doppler login)"
  fi
else
  warn "Doppler CLI not installed"
fi

echo ""
echo "Canonical map: docs/SECRETS_MAP.md"
