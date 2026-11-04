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

# --- Local Keycloak (self-hosted IdP) ---
if [ -f "$ROOT/env/.env" ] && grep -q "^KEYCLOAK_URL=" "$ROOT/env/.env"; then
  ok "Local Keycloak: KEYCLOAK_URL set in env/.env"
else
  warn "Local Keycloak: KEYCLOAK_URL not in env/.env (apps default to http://localhost:8180)"
fi

# --- GitHub (required deploy) ---
GITHUB_REQUIRED=(DEPLOY_HOST DEPLOY_USER DEPLOY_SSH_KEY SOPS_AGE_KEY)
GITHUB_BUILD=()
GITHUB_OPTIONAL=(POSTGRES_PASSWORD JWT_SECRET STRIPE_SECRET STRIPE_WEBHOOK_SECRET)
GITHUB_LEGACY=(CLERK_SECRET_KEY CLERK_PUBLISHABLE_KEY CLERK_JWKS_URL CLERK_CUSTOMER_PUBLISHABLE_KEY CLERK_MERCHANT_PUBLISHABLE_KEY CLERK_ADMIN_PUBLISHABLE_KEY CLERK_DRIVER_PUBLISHABLE_KEY)

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  GH_SECRETS="$(gh secret list 2>/dev/null | awk '{print $1}' | sort -u || true)"
  has_secret() { echo "$GH_SECRETS" | grep -qx "$1"; }

  for key in "${GITHUB_REQUIRED[@]}"; do
    if has_secret "$key"; then ok "GitHub required: $key"; else fail "GitHub required: $key MISSING"; fi
  done
  for key in "${GITHUB_BUILD[@]}"; do
    if has_secret "$key"; then ok "GitHub build-time: $key"; else warn "GitHub build-time: $key missing"; fi
  done

  ok "Runtime secrets: secrets/droplet.enc.yaml (SOPS + age) is SSOT"
  for key in "${GITHUB_LEGACY[@]}" DOPPLER_TOKEN; do
    if has_secret "$key"; then warn "GitHub legacy (can remove): $key"; fi
  done
  for key in "${GITHUB_OPTIONAL[@]}"; do
    if has_secret "$key"; then warn "GitHub duplicate of SOPS file (can remove): $key"; fi
  done

  for key in SENTRY_DSN NEXT_PUBLIC_SENTRY_DSN; do
    if has_secret "$key"; then warn "GitHub legacy (can remove; GlitchTip DSN is GLITCHTIP_DSN in SOPS + vars.NEXT_PUBLIC_GLITCHTIP_DSN): $key"; fi
  done
else
  warn "gh CLI not authenticated — skip GitHub checks"
fi

# --- SOPS (doc 37) ---
for f in secrets/*.enc.yaml; do
  [ -f "$f" ] || continue
  if grep -q "^sops:" "$f"; then ok "SOPS encrypted: $f"; else warn "SOPS: $f is not encrypted"; fi
done
if grep -q "PLACEHOLDER" .sops.yaml 2>/dev/null; then warn "SOPS: .sops.yaml still has placeholder age recipients"; fi

if [ ! -f secrets/droplet.enc.yaml ]; then warn "SOPS: secrets/droplet.enc.yaml not created yet (see secrets/README.md)"; fi

echo ""
echo "Canonical map: docs/SECRETS_MAP.md"
