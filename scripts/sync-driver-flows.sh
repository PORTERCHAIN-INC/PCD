#!/usr/bin/env bash
# Doc 82: vendor packages/driver-flows into the Expo driver app (EAS builds outside the workspace).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dst="$root/apps/mobile-driver/vendor/driver-flows"
rm -rf "$dst" && mkdir -p "$dst"
cp -R "$root/packages/driver-flows/package.json" "$root/packages/driver-flows/src" "$dst/"
rm -f "$dst/src/"*.test.ts
echo "synced $dst"
