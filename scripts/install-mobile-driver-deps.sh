#!/usr/bin/env bash
# Run outside Cursor (Terminal.app / iTerm) — Cursor sandbox blocks xmlbuilder's .vscode path.
set -euo pipefail
cd "$(dirname "$0")/.."
CI=true pnpm install --filter @porterchain/mobile-driver --no-frozen-lockfile
test -f apps/mobile-driver/node_modules/expo-local-authentication/package.json
node -e "console.log('expo-local-authentication', require('./apps/mobile-driver/node_modules/expo-local-authentication/package.json').version)"
echo "OK"
