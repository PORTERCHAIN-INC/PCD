#!/usr/bin/env bash
# Porterchain Fleetbase install & verify — uses upstream Fleetbase v0.7.40 unchanged.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FLEETBASE_DIR="$ROOT/apps/fleetbase"
COMPOSE_BASE="$FLEETBASE_DIR/docker-compose.yml"
COMPOSE_OVERRIDE="$ROOT/infrastructure/docker/fleetbase.porterchain.override.yml"
TAG="v0.7.40"
REPO="https://github.com/fleetbase/fleetbase.git"

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

# ── 1. Clone if missing ─────────────────────────────────────────────────────
if [[ ! -f "$COMPOSE_BASE" ]]; then
  info "Cloning Fleetbase $TAG into apps/fleetbase..."
  git clone --depth 1 --branch "$TAG" "$REPO" "$FLEETBASE_DIR"
  ok "Cloned Fleetbase $TAG"
else
  ok "Fleetbase already present at apps/fleetbase"
fi

# ── 2. License check ──────────────────────────────────────────────────────────
if [[ -f "$FLEETBASE_DIR/LICENSE.md" ]]; then
  ok "License: AGPL-3.0 (see apps/fleetbase/LICENSE.md)"
else
  err "LICENSE.md not found — aborting"
  exit 1
fi

cd "$FLEETBASE_DIR"

# ── 3. Official non-interactive installer (creates override, api/.env, console config) ──
if [[ ! -f docker-compose.override.yml ]]; then
  info "Running official Fleetbase docker-install.sh (non-interactive)..."
  bash scripts/docker-install.sh --non-interactive
  ok "Fleetbase installer completed"
else
  ok "docker-compose.override.yml exists — skipping installer"
fi

# ── 4. Ensure Porterchain bridge network exists ─────────────────────────────
docker network inspect porterchain_porterchain-internal >/dev/null 2>&1 || \
  docker network create porterchain_porterchain-internal >/dev/null 2>&1 || true

# ── 5. Start stack with Porterchain overlay ─────────────────────────────────
info "Starting Fleetbase stack (this may take several minutes on first run)..."
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$COMPOSE_OVERRIDE" \
  up -d --build

# ── 6. Wait for database ────────────────────────────────────────────────────
info "Waiting for database..."
DB_CONTAINER=$(docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$COMPOSE_OVERRIDE" ps -q database)
SECONDS=0
until docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null | grep -q healthy; do
  if (( SECONDS >= 120 )); then err "Database health timeout"; exit 1; fi
  sleep 3
  SECONDS=$((SECONDS + 3))
done
ok "Database healthy"

# ── 6b. MySQL grants (required for deploy.sh sandbox migrations) ─────────────
ROOT_PASS=$(grep MYSQL_ROOT_PASSWORD docker-compose.override.yml | cut -d'"' -f2)
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$COMPOSE_OVERRIDE" \
  exec -T database mysql -uroot -p"$ROOT_PASS" -e \
  "GRANT ALL PRIVILEGES ON *.* TO 'fleetbase'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;" \
  2>/dev/null || true
ok "MySQL privileges granted for fleetbase user"

# ── 7. Deploy (migrations, seeds, permissions) ─────────────────────────────
info "Running deploy.sh inside application container..."
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$COMPOSE_OVERRIDE" \
  exec -T application bash -c "./deploy.sh"

docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$COMPOSE_OVERRIDE" \
  up -d

ok "Fleetbase install complete"
echo ""
echo "  API:     http://localhost:8000"
echo "  Socket:  ws://localhost:38000"
echo "  MySQL:   127.0.0.1:3307 (host)"
echo ""
echo "Run verification: bash infrastructure/docker/scripts/fleetbase-verify.sh"
