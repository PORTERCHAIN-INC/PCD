#!/usr/bin/env bash
# Resolve Clerk env file: env/clerk.env (preferred) or clerk-keys.local.env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [ -n "${1:-}" ]; then
  echo "$1"
  exit 0
fi

for candidate in \
  "$ROOT/env/clerk.env" \
  "$SCRIPT_DIR/clerk-keys.local.env"; do
  if [ -f "$candidate" ]; then
    echo "$candidate"
    exit 0
  fi
done

echo "Missing Clerk env. Copy env/clerk.env.example → env/clerk.env and fill keys." >&2
exit 1
