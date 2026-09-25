#!/usr/bin/env bash
# Local E2E wire checks for website ↔ API marketing paths.
# Requires: API on :8001, website on :3000 (or override bases).
set -euo pipefail

API_BASE="${PORTERCHAIN_API_BASE:-http://127.0.0.1:8001}"
WEB_BASE="${PORTERCHAIN_WEBSITE_BASE:-http://127.0.0.1:3000}"
failures=0

pass() { printf 'OK  %s\n' "$1"; }
fail() { printf 'FAIL %s — %s\n' "$1" "$2"; failures=$((failures + 1)); }

check_http() {
  local name="$1" url="$2" expect="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" || echo "000")
  if [[ "$code" == "$expect" ]]; then
    pass "$name ($code)"
  else
    fail "$name" "expected $expect got $code ($url)"
  fi
}

echo "Website E2E wire — API=$API_BASE WEB=$WEB_BASE"
echo

check_http "API health" "$API_BASE/health" 200
check_http "Public blog list" "$API_BASE/v1/public/blog/posts?locale=en&limit=5" 200
check_http "Public blog authors" "$API_BASE/v1/public/blog/authors" 200
check_http "Website home EN" "$WEB_BASE/en" 200
check_http "Website blog EN" "$WEB_BASE/en/blog" 200
check_http "Website authors EN" "$WEB_BASE/en/authors" 200
check_http "Website contact EN" "$WEB_BASE/en/contact" 200

# Lead routes: 404 = missing; 401/403/422/503 = wired (auth/validation/provider)
check_route() {
  local name="$1" url="$2"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
    -X POST "$url" \
    -H 'Content-Type: application/json' \
    -d '{}' || echo "000")
  case "$code" in
    200|201|400|401|403|422|503) pass "$name ($code)" ;;
    *) fail "$name" "unexpected $code ($url)" ;;
  esac
}

check_route "Public inquiries" "$API_BASE/v1/public/inquiries"
check_route "Guide leads" "$API_BASE/v1/public/guide/leads"
check_route "Meta lead webhook" "$API_BASE/v1/public/leads/webhooks/meta"

echo
if [[ "$failures" -gt 0 ]]; then
  echo "FAILED: $failures check(s)"
  exit 1
fi
echo "All wire checks passed."
echo
echo "Manual follow-ups (browser):"
echo "  1. Admin → Blog → create draft → Open website preview"
echo "  2. Publish post → appears on /en/blog"
echo "  3. Contact form → lead in admin CRM"
echo "  4. Newsletter / guide lead forms → LeadIngest"
echo "  5. Phone FAB visible on marketing pages; stack order OK on mobile"
echo "  6. PUBLIC_INGEST_API_KEY matches website + API .env"
