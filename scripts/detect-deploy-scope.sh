#!/usr/bin/env bash
# Map changed paths → Deploy workflow scope.
# Prints one line: full | website | api | merchant | admin | driver | customer
#
# Usage:
#   git diff --name-only A B | bash scripts/detect-deploy-scope.sh
#   bash scripts/detect-deploy-scope.sh <file-list.txt>
set -euo pipefail

if [[ $# -gt 0 && -f "$1" ]]; then
  mapfile -t FILES < "$1"
else
  mapfile -t FILES
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "full"
  exit 0
fi

need_full=0
want_api=0
want_website=0
want_admin=0
want_merchant=0
want_driver=0
want_customer=0

for f in "${FILES[@]}"; do
  [[ -z "$f" ]] && continue
  case "$f" in
    .github/workflows/deploy.yml|\
    infrastructure/deploy/*|\
    pnpm-lock.yaml|\
    package.json|\
    pnpm-workspace.yaml|\
    packages/*|\
    apps/api/Dockerfile|\
    apps/admin/Dockerfile|\
    apps/merchant-portal/Dockerfile|\
    apps/driver-portal/Dockerfile|\
    apps/customer/Dockerfile|\
    website/Dockerfile)
      need_full=1
      ;;
    apps/api/*|services/pricing-engine/*|services/driver-platform/*|services/fleetbase-adapter/*)
      want_api=1
      ;;
    website/*)
      want_website=1
      ;;
    apps/admin/*)
      want_admin=1
      ;;
    apps/merchant-portal/*)
      want_merchant=1
      ;;
    apps/driver-portal/*)
      want_driver=1
      ;;
    apps/customer/*)
      want_customer=1
      ;;
    apps/mobile-*/*|docs/*|graphify-out/*|.cursor/*|.ripwire*|*.md)
      # Docs / mobile / agent noise — ignore for deploy scope.
      ;;
    *)
      # Unknown path → safe full rebuild.
      need_full=1
      ;;
  esac
done

if [[ "$need_full" -eq 1 ]]; then
  echo "full"
  exit 0
fi

count=0
scope=""
for pair in \
  "want_api:api" \
  "want_website:website" \
  "want_admin:admin" \
  "want_merchant:merchant" \
  "want_driver:driver" \
  "want_customer:customer"
do
  var="${pair%%:*}"
  name="${pair##*:}"
  if [[ "${!var}" -eq 1 ]]; then
    count=$((count + 1))
    scope="$name"
  fi
done

if [[ "$count" -eq 0 ]]; then
  # Only ignored paths changed — skip by emitting website? Prefer no-op as full
  # would waste time; emit "none" and let workflow skip deploy builds.
  echo "none"
  exit 0
fi

if [[ "$count" -gt 1 ]]; then
  echo "full"
  exit 0
fi

echo "$scope"
