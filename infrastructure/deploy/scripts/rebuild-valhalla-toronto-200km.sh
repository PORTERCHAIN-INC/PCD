#!/usr/bin/env bash
# Replace full-Ontario Valhalla tiles with a Toronto ±200 km extract.
# Safe on the 4GB droplet: removes the 925MB Ontario PBF before rebuilding.
#
# Usage (on droplet as root):
#   bash /opt/porterchain/scripts/rebuild-valhalla-toronto-200km.sh
set -euo pipefail

PORTERCHAIN_DIR="${PORTERCHAIN_DIR:-/opt/porterchain}"
EXTRACT_DIR="${EXTRACT_DIR:-$PORTERCHAIN_DIR/valhalla-extract}"
OUT_PBF="$EXTRACT_DIR/gta-200km.osm.pbf"
PREPARE="$PORTERCHAIN_DIR/scripts/prepare-valhalla-gta.sh"
VOLUME="porterchain-prod_valhalla-tiles"
COMPOSE="$PORTERCHAIN_DIR/docker-compose.prod.yml"

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

if [[ ! -f "$PREPARE" ]]; then
  err "Missing $PREPARE — copy prepare-valhalla-gta.sh to $PORTERCHAIN_DIR/scripts/ first"
  exit 1
fi

mkdir -p "$EXTRACT_DIR"
info "Fetching Toronto ±200 km OSM extract (not full Ontario)…"
FORCE_REFRESH="${FORCE_REFRESH:-0}" DATA_DIR="$EXTRACT_DIR" OUT_PBF="$OUT_PBF" bash "$PREPARE"
if [[ ! -f "$OUT_PBF" ]]; then
  err "Extract missing at $OUT_PBF"
  exit 1
fi
ok "Extract $(du -h "$OUT_PBF" | awk '{print $1}')"

info "Stopping Valhalla…"
docker stop pcd-valhalla >/dev/null 2>&1 || true

info "Replacing Ontario graph with Toronto 200 km PBF…"
docker run --rm \
  -v "${VOLUME}:/custom_files" \
  -v "${OUT_PBF}:/incoming/gta-200km.osm.pbf:ro" \
  alpine:3.22.2 \
  sh -c 'rm -rf /custom_files/* && cp /incoming/gta-200km.osm.pbf /custom_files/gta-200km.osm.pbf'

ok "Volume now has only the Toronto extract"
docker run --rm -v "${VOLUME}:/custom_files" alpine:3.22.2 \
  sh -c 'du -sh /custom_files /custom_files/gta-200km.osm.pbf'

info "Rebuilding Valhalla tiles (GTA clip — a few minutes)…"
cd "$PORTERCHAIN_DIR"
docker compose -f "$COMPOSE" up -d --no-deps --pull never valhalla

info "Waiting for Valhalla /status (tile build)…"
for i in $(seq 1 90); do
  if docker exec pcd-valhalla curl -sf -m 5 http://localhost:8002/status 2>/dev/null | grep -q '"route"'; then
    ok "Valhalla serving Toronto ±200 km tiles"
    docker exec pcd-valhalla sh -c 'du -sh /custom_files /custom_files/* 2>/dev/null'
    exit 0
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx pcd-valhalla; then
    err "Valhalla container exited — likely OOM. Check: docker logs pcd-valhalla"
    docker logs pcd-valhalla --tail 40 || true
    exit 1
  fi
  echo "  wait $i/90…"
  sleep 10
done

err "Timed out waiting for Valhalla. Logs:"
docker logs pcd-valhalla --tail 60 || true
exit 1
