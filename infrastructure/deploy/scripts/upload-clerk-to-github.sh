#!/usr/bin/env bash
# Set GitHub Actions secrets for per-portal Clerk publishable keys (Docker build args).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$(bash "${SCRIPT_DIR}/resolve-clerk-env.sh" "${1:-}")"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

command -v gh >/dev/null || { echo "Install: brew install gh && gh auth login" >&2; exit 1; }

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

echo "Setting GitHub secrets (publishable keys only)..."

gh secret set CLERK_CUSTOMER_PUBLISHABLE_KEY -b "${CLERK_CUSTOMER_PUBLISHABLE_KEY}"
gh secret set CLERK_MERCHANT_PUBLISHABLE_KEY -b "${CLERK_MERCHANT_PUBLISHABLE_KEY}"
gh secret set CLERK_ADMIN_PUBLISHABLE_KEY -b "${CLERK_ADMIN_PUBLISHABLE_KEY}"
gh secret set CLERK_DRIVER_PUBLISHABLE_KEY -b "${CLERK_DRIVER_PUBLISHABLE_KEY}"

# Legacy fallbacks — keep customer as default for any old references
gh secret set CLERK_PUBLISHABLE_KEY -b "${CLERK_CUSTOMER_PUBLISHABLE_KEY}"

echo "✓ GitHub publishable secrets updated"
echo "Runtime sk_* keys stay in Doppler only (see docs/SECRETS_MAP.md)"
