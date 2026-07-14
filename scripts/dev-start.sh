#!/usr/bin/env bash
# Start Porterchain local slices detached from the parent process group.
# Survives Cursor agent shell abort (uses a new session via Python).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

# Default: website slice. Pass names to override: api website merchant admin driver customer worker
SERVICES=("$@")
if [[ ${#SERVICES[@]} -eq 0 ]]; then
  SERVICES=(api website merchant admin driver customer)
fi

port_for() {
  case "$1" in
    api) echo 8001 ;;
    website) echo 3000 ;;
    merchant) echo 3001 ;;
    admin) echo 3002 ;;
    driver) echo 3003 ;;
    customer) echo 3004 ;;
    worker) echo 0 ;;
    *) echo "" ;;
  esac
}

cmd_for() {
  case "$1" in
    api) echo "pnpm dev:api" ;;
    website) echo "pnpm dev:website" ;;
    merchant) echo "pnpm dev:merchant" ;;
    admin) echo "pnpm dev:admin" ;;
    driver) echo "pnpm dev:driver" ;;
    customer) echo "pnpm dev:customer" ;;
    worker) echo "pnpm dev:worker" ;;
    *) echo "" ;;
  esac
}

is_listening() {
  local port=$1
  [[ "$port" == "0" ]] && return 1
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

start_detached() {
  local svc=$1
  local cmd
  cmd="$(cmd_for "$svc")"
  [[ -n "$cmd" ]] || {
    echo "  unknown service: $svc" >&2
    return 1
  }

  local port
  port="$(port_for "$svc")"
  if [[ "$port" != "0" ]] && is_listening "$port"; then
    echo "  already up $svc (port $port)" >&2
    return 0
  fi

  local log="$LOG_DIR/dev-$svc.log"
  local pidfile="$LOG_DIR/dev-$svc.pid"
  : >"$log"

  # New session + no controlling TTY so Cursor/agent shell teardown cannot kill us.
  python3 - "$ROOT" "$cmd" "$log" "$pidfile" <<'PY'
import os, subprocess, sys

root, cmd, log_path, pid_path = sys.argv[1:5]
os.chdir(root)
log_f = open(log_path, "ab", buffering=0)
proc = subprocess.Popen(
    ["/bin/bash", "-lc", cmd],
    stdin=subprocess.DEVNULL,
    stdout=log_f,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    close_fds=True,
)
with open(pid_path, "w", encoding="utf-8") as pf:
    pf.write(str(proc.pid))
print(proc.pid)
PY
}

# Ambient shell may still export Doppler/live CLERK_* from a prior session.
# Local slices must use env/clerk.env + app .env.local (pk_test) — strip live exports.
while IFS= read -r key; do
  [[ -n "$key" ]] || continue
  unset "$key" 2>/dev/null || true
done < <(env | awk -F= '/^(CLERK_|NEXT_PUBLIC_CLERK_)/ {print $1}')
if [[ -f "$ROOT/env/clerk.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/env/clerk.env"
  set +a
  echo "  clerk: using env/clerk.env (test keys for local)"
fi

echo "Porterchain dev-start (detached local slices)"
for svc in "${SERVICES[@]}"; do
  port="$(port_for "$svc")"
  if [[ "$port" != "0" ]] && is_listening "$port"; then
    echo "  already up $svc (port $port)"
    continue
  fi
  pid="$(start_detached "$svc")"
  echo "  start $svc (pid $pid${port:+, port $port}) → .logs/dev-$svc.log"
done

echo "done — stop with: pnpm dev:stop"
