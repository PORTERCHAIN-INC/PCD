#!/usr/bin/env bash
# Install Fleetbase on the PorterChain production droplet (same host as Caddy).
# Requires: 4GB+ RAM, Docker, /opt/porterchain with porterchain-prod_edge network.
#
# Usage (on droplet as root):
#   bash /opt/porterchain/scripts/install-fleetbase-prod.sh
set -euo pipefail

FLEETBASE_DIR="${FLEETBASE_DIR:-/opt/fleetbase}"
PORTERCHAIN_DIR="${PORTERCHAIN_DIR:-/opt/porterchain}"
TAG="${FLEETBASE_TAG:-v0.7.40}"
REPO="${FLEETBASE_REPO:-https://github.com/fleetbase/fleetbase.git}"
OVERRIDE="$PORTERCHAIN_DIR/fleetbase.prod.override.yml"

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

if [[ ! -f "$OVERRIDE" ]]; then
  err "Missing $OVERRIDE — copy fleetbase.prod.override.yml from the repo first"
  exit 1
fi

if ! docker network inspect porterchain-prod_edge >/dev/null 2>&1; then
  err "Network porterchain-prod_edge not found — start PorterChain stack first"
  exit 1
fi

# Free RAM: single API replica during install
if [[ -f "$PORTERCHAIN_DIR/.env" ]]; then
  if grep -q '^API_REPLICAS=' "$PORTERCHAIN_DIR/.env"; then
    sed -i 's/^API_REPLICAS=.*/API_REPLICAS=1/' "$PORTERCHAIN_DIR/.env"
  else
    echo 'API_REPLICAS=1' >>"$PORTERCHAIN_DIR/.env"
  fi
  (cd "$PORTERCHAIN_DIR" && docker compose -f docker-compose.prod.yml up -d --scale api=1 api) || true
fi

# Optionally pause Valhalla during heavy pulls (restarted at end)
VALHALLA_WAS_UP=0
if docker ps --format '{{.Names}}' | grep -qx pcd-valhalla; then
  VALHALLA_WAS_UP=1
  info "Stopping Valhalla temporarily to free RAM…"
  docker stop pcd-valhalla || true
fi

if [[ ! -f "$FLEETBASE_DIR/docker-compose.yml" ]]; then
  info "Cloning Fleetbase $TAG → $FLEETBASE_DIR"
  git clone --depth 1 --branch "$TAG" "$REPO" "$FLEETBASE_DIR"
else
  ok "Fleetbase already present at $FLEETBASE_DIR"
fi

cd "$FLEETBASE_DIR"

if [[ ! -f docker-compose.override.yml ]]; then
  info "Running official Fleetbase docker-install.sh (non-interactive)…"
  bash scripts/docker-install.sh --non-interactive
else
  ok "docker-compose.override.yml exists"
fi

# Force production public URLs into override (idempotent-ish)
python3 - <<'PY'
from pathlib import Path
p = Path("docker-compose.override.yml")
text = p.read_text()
replacements = {
    'APP_URL: "http://localhost:8000"': 'APP_URL: "https://console.porterchain.com"',
    'ENVIRONMENT: "development"': 'ENVIRONMENT: "production"',
    'APP_DEBUG: "true"': 'APP_DEBUG: "false"',
    'SESSION_DOMAIN: "localhost"': 'SESSION_DOMAIN: "console.porterchain.com"',
}
for a, b in replacements.items():
    text = text.replace(a, b)
p.write_text(text)
print("updated docker-compose.override.yml URLs for production")
PY

info "Writing production console runtime config…"
mkdir -p "$FLEETBASE_DIR/console"
cat >"$FLEETBASE_DIR/console/fleetbase.config.json" <<'JSON'
{
  "API_HOST": "https://console.porterchain.com",
  "SOCKETCLUSTER_HOST": "console.porterchain.com",
  "SOCKETCLUSTER_PORT": "443",
  "SOCKETCLUSTER_SECURE": "true"
}
JSON

info "Pulling / starting Fleetbase stack…"
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f "$OVERRIDE" \
  up -d --pull missing

info "Waiting for MySQL…"
DB_ID=$(docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$OVERRIDE" ps -q database)
for i in $(seq 1 60); do
  st=$(docker inspect -f '{{.State.Health.Status}}' "$DB_ID" 2>/dev/null || echo starting)
  if [[ "$st" == "healthy" ]]; then
    ok "MySQL healthy"
    break
  fi
  if [[ "$i" -eq 60 ]]; then err "MySQL health timeout ($st)"; exit 1; fi
  sleep 5
done

ROOT_PASS=$(grep MYSQL_ROOT_PASSWORD docker-compose.override.yml | head -1 | cut -d'"' -f2)
docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$OVERRIDE" \
  exec -T database mysql -uroot -p"$ROOT_PASS" -e \
  "GRANT ALL PRIVILEGES ON *.* TO 'fleetbase'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;" \
  2>/dev/null || true

info "Running deploy.sh (migrations / seed)…"
docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$OVERRIDE" \
  exec -T application bash -c "./deploy.sh"

docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$OVERRIDE" up -d

if [[ "$VALHALLA_WAS_UP" -eq 1 ]]; then
  info "Restarting Valhalla…"
  (cd "$PORTERCHAIN_DIR" && docker compose -f docker-compose.prod.yml up -d valhalla) || docker start pcd-valhalla || true
fi

ok "Fleetbase containers up"
docker compose -f docker-compose.yml -f docker-compose.override.yml -f "$OVERRIDE" ps
echo ""
echo "Enable the PorterChain API dispatch bridge (separate compose project):"
echo "  cd $PORTERCHAIN_DIR && docker compose -f docker-compose.prod.yml -f docker-compose.prod.fleetbase-bridge.yml up -d api worker"
echo "Doppler must have FLEETBASE_API_KEY, FLEETBASE_WEBHOOK_SECRET, FLEETBASE_DEFAULT_COMPANY_UUID."
