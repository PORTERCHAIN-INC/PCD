#!/usr/bin/env bash
# Boot / recover Porterchain prod on the droplet without touching DB volumes destructively.
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$DEPLOY_DIR/docker-compose.prod.yml}"
cd "$DEPLOY_DIR"

wait_postgres() {
  local attempts="${1:-60}"
  echo "Waiting for Postgres (up to $((attempts * 5))s)..."
  for _ in $(seq 1 "$attempts"); do
    if docker exec pcd-postgres pg_isready -U porterchain -d porterchain >/dev/null 2>&1; then
      echo "Postgres ready"
      return 0
    fi
    sleep 5
  done
  echo "::error::Postgres failed to become ready"
  docker logs pcd-postgres --tail 120 || true
  return 1
}

wait_redis() {
  local attempts="${1:-24}"
  echo "Waiting for Redis..."
  for _ in $(seq 1 "$attempts"); do
    if docker exec pcd-redis redis-cli ping 2>/dev/null | grep -q PONG; then
      echo "Redis ready"
      return 0
    fi
    sleep 5
  done
  echo "::error::Redis failed to become ready"
  docker logs pcd-redis --tail 80 || true
  return 1
}

echo "=== Recover data plane (no force-recreate) ==="
docker compose -f docker-compose.prod.yml up -d postgres redis valhalla
wait_postgres 60
wait_redis 24

echo "=== Roll app tier ==="
docker compose -f docker-compose.prod.yml up -d --remove-orphans --force-recreate --pull missing \
  --scale api="${API_REPLICAS:-2}" \
  web api worker admin merchant driver customer caddy

wait_postgres 24
wait_redis 12

echo "=== Stack recovery complete ==="
docker compose -f docker-compose.prod.yml ps
