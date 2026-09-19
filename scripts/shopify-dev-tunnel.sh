#!/usr/bin/env bash
# Expose local API (:8001) + merchant portal (:3001) over HTTPS for Shopify OAuth.
# Requires: cloudflared (brew install cloudflare/cloudflare/cloudflared)
# Usage: bash scripts/shopify-dev-tunnel.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Install cloudflared first:" >&2
  echo "  brew install cloudflare/cloudflare/cloudflared" >&2
  exit 1
fi

need_port() {
  local port=$1 name=$2
  if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Start $name on :$port first (e.g. bash scripts/dev-start.sh api merchant)" >&2
    exit 1
  fi
}

need_port 8001 api
need_port 3001 merchant-portal

API_LOG="$LOG_DIR/shopify-tunnel-api.log"
PORTAL_LOG="$LOG_DIR/shopify-tunnel-portal.log"
: >"$API_LOG"
: >"$PORTAL_LOG"

cloudflared tunnel --url http://127.0.0.1:8001 --no-autoupdate >"$API_LOG" 2>&1 &
API_PID=$!
cloudflared tunnel --url http://127.0.0.1:3001 --no-autoupdate >"$PORTAL_LOG" 2>&1 &
PORTAL_PID=$!

cleanup() {
  kill "$API_PID" "$PORTAL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Prefer grep -Eo (always on macOS). Do not depend on ripgrep being on PATH.
extract_url() {
  local log=$1
  # cloudflared prints: |  https://….trycloudflare.com                             |
  grep -Eo 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$log" 2>/dev/null | head -1 || true
}

pick_url() {
  local log=$1 label=$2
  local url=""
  local i
  for i in $(seq 1 60); do
    if ! kill -0 "$API_PID" 2>/dev/null && [[ "$label" == "API" ]]; then
      echo "cloudflared API process exited early. See $log" >&2
      return 1
    fi
    if ! kill -0 "$PORTAL_PID" 2>/dev/null && [[ "$label" == "portal" ]]; then
      echo "cloudflared portal process exited early. See $log" >&2
      return 1
    fi
    url="$(extract_url "$log")"
    if [[ -n "${url:-}" ]]; then
      echo "$url"
      return 0
    fi
    sleep 0.5
  done
  echo "Timed out waiting for $label tunnel URL. Tail of $log:" >&2
  tail -n 30 "$log" >&2 || true
  return 1
}

echo "Waiting for Cloudflare quick tunnels…" >&2
API_URL="$(pick_url "$API_LOG" API)" || exit 1
PORTAL_URL="$(pick_url "$PORTAL_LOG" portal)" || exit 1

cat <<EOF

Shopify Partner → App setup (paste these while tunnel is running):

  App URL:                    ${PORTAL_URL}/shopify
  Allowed redirection URL(s): ${API_URL}/v1/integrations/shopify/callback

Also set local API env for this session (restart API after):

  PORTERCHAIN_API_URL=${API_URL}
  MERCHANT_PORTAL_URL=${PORTAL_URL}

Install test:

  ${API_URL}/v1/integrations/shopify/install?shop=YOURSHOP.myshopify.com

Tunnels running (Ctrl+C to stop). Logs:
  $API_LOG
  $PORTAL_LOG

EOF

wait
