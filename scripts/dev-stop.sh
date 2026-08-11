#!/usr/bin/env bash
# Stop Porterchain dev processes. Run slices (dev:api, dev:website, …) — not `pnpm dev` / turbo all-apps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEEP=()

usage() {
  echo "Usage: dev-stop.sh [--keep api|website|merchant|driver|customer|admin|worker]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --keep)
      shift
      [[ $# -gt 0 ]] || usage
      KEEP+=("$1")
      shift
      ;;
    -h | --help) usage ;;
    *) usage ;;
  esac
done

should_keep() {
  local svc=$1
  # Bash 3.2 + `set -u`: empty array expansion is unbound without a guard.
  if ((${#KEEP[@]} == 0)); then
    return 1
  fi
  for k in "${KEEP[@]}"; do
    [[ "$k" == "$svc" ]] && return 0
  done
  return 1
}

stop_port() {
  local port=$1 svc=$2
  if should_keep "$svc"; then
    echo "  keep $svc (port $port)"
    return
  fi
  local pids
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "  stop $svc (port $port)"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
  fi
}

echo "Porterchain dev-stop (slice discipline — avoid turbo dev for daily work)"

stop_port 8001 api
stop_port 3000 website
stop_port 3001 merchant
stop_port 3002 admin
stop_port 3003 driver
stop_port 3004 customer

if should_keep worker; then
  echo "  keep worker"
else
  if pkill -f 'apps/worker.*python run.py' 2>/dev/null \
    || pkill -f 'pnpm dev:worker' 2>/dev/null; then
    echo "  stop worker"
  fi
fi

# Orphan pnpm dev:* wrappers (after port listeners exit)
if [[ ${#KEEP[@]} -eq 0 ]]; then
  pkill -f 'pnpm dev:(api|website|merchant|driver|customer|admin|worker)' 2>/dev/null || true
fi

sleep 1
echo "done"
