#!/usr/bin/env bash
# Boot PorterChain local core: Postgres, Redis, Mailpit, SpiceDB, API, website.
# Safe to rerun. Routing tiles (Valhalla/OSRM) stay off; local quotes use haversine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/.cursor/cloud-agent-lib.sh"

ensure_dockerd

docker compose -f infrastructure/docker/docker-compose.yml --profile core up -d

echo "waiting for postgres"
ready=0
for _ in $(seq 1 60); do
  if docker exec porterchain-postgres pg_isready -U porterchain -d porterchain >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != "1" ]]; then
  echo "postgres did not become ready" >&2
  docker compose -f infrastructure/docker/docker-compose.yml --profile core ps >&2 || true
  exit 1
fi

echo "waiting for redis"
ready=0
for _ in $(seq 1 30); do
  if docker exec porterchain-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != "1" ]]; then
  echo "redis did not become ready" >&2
  exit 1
fi

(
  cd apps/api
  # shellcheck disable=SC1091
  source .venv/bin/activate
  export PYTHONPATH="src:../../shared/python:../../services/python:../../services/pricing-engine:../../services/event-bus:../../services/driver-platform"
  export APP_ENV=local
  alembic upgrade head
)

start_session() {
  local session="$1"
  local port="$2"
  local cmd="$3"
  if port_listening "$port"; then
    echo "already listening ${session} :${port}"
    return 0
  fi
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session" || true
  fi
  tmux new-session -d -s "$session" -c "$ROOT" -- bash -lc "export PATH=/usr/local/node/bin:/usr/local/cargo/bin:\$PATH; exec ${cmd}"
  echo "started ${session}"
}

start_session porterchain-api 8001 "pnpm dev:api"
start_session porterchain-website 3000 "pnpm dev:website"

echo "waiting for API"
ready=0
for _ in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:8001/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != "1" ]]; then
  echo "API did not become ready" >&2
  tmux capture-pane -pt porterchain-api -S -80 >&2 || true
  exit 1
fi

echo "waiting for website"
ready=0
for _ in $(seq 1 180); do
  if curl -sf -o /dev/null "http://127.0.0.1:3000/"; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != "1" ]]; then
  echo "website did not become ready" >&2
  tmux capture-pane -pt porterchain-website -S -80 >&2 || true
  exit 1
fi

echo "start ok"
