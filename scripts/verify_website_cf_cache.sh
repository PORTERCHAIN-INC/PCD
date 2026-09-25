#!/usr/bin/env bash
# Verify Cloudflare HTML edge cache is active for marketing pages.
# Companion to infrastructure/deploy/scripts/cloudflare-html-cache-checklist.sh
#
# Exit 0 when cf-cache-status is present (rules applied + proxied).
# Exit 1 with actionable message when traffic is origin-only (e.g. Caddy via).
set -euo pipefail

BASE="${WEBSITE_PUBLIC_ORIGIN:-https://porterchain.com}"
PATHS=("/en" "/en/blog" "/en/business")

fail=0
for p in "${PATHS[@]}"; do
  headers="$(curl -sI "${BASE}${p}" || true)"
  status="$(printf '%s' "$headers" | awk 'NR==1 {print $2}')"
  cf="$(printf '%s' "$headers" | tr -d '\r' | awk -F': ' 'tolower($1)=="cf-cache-status" {print $2; exit}')"
  via="$(printf '%s' "$headers" | tr -d '\r' | awk -F': ' 'tolower($1)=="via" {print $2; exit}')"
  if [[ -z "$cf" ]]; then
    echo "FAIL ${p}: no cf-cache-status (HTTP ${status:-?} via=${via:-none})"
    fail=1
  else
    echo "OK   ${p}: cf-cache-status=${cf}"
  fi
done

if [[ "$fail" -ne 0 ]]; then
  cat <<'EOF' >&2

Cloudflare HTML edge cache is not active on these paths.
Today porterchain.com is origin-served (via Caddy). Orange-cloud proxy is required first.
Checklist: bash infrastructure/deploy/scripts/cloudflare-html-cache-checklist.sh
Then re-run: bash scripts/verify_website_cf_cache.sh
EOF
  exit 1
fi

echo "Cloudflare HTML cache headers present."
