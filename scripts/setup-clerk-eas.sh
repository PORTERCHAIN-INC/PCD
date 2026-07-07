#!/usr/bin/env bash
# Push per-app Clerk publishable keys to EAS for iOS/Android builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/env/clerk.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Run pnpm clerk:sync first (needs env/clerk.env)" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

command -v eas >/dev/null || { echo "Install: npm i -g eas-cli && eas login" >&2; exit 1; }

echo "==> mobile-customer (porterchain-customer Clerk app)"
(
  cd "${ROOT}/apps/mobile-customer"
  eas secret:create --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value "${CLERK_CUSTOMER_PUBLISHABLE_KEY}" --force 2>/dev/null \
    || eas env:create --environment production --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value "${CLERK_CUSTOMER_PUBLISHABLE_KEY}" --visibility plaintext --force
)

echo "==> mobile-driver (porterchain-driver Clerk app)"
(
  cd "${ROOT}/apps/mobile-driver"
  eas secret:create --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value "${CLERK_DRIVER_PUBLISHABLE_KEY}" --force 2>/dev/null \
    || eas env:create --environment production --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value "${CLERK_DRIVER_PUBLISHABLE_KEY}" --visibility plaintext --force
)

echo "✓ EAS Clerk publishable keys configured"
