#!/usr/bin/env bash
# Replace full-Ontario Valhalla tiles with the GTA ±150 km extract.
# Coverage stays ±150 km from downtown Toronto. RAM-tuned valhalla.json is
# copied in before tile build (256 MiB cache, no bike/ped graph).
# Prefer running this on a host with ≥8 GB; tile build still spikes RAM.
#
# Usage (on droplet as root):
#   bash /opt/porterchain/scripts/rebuild-valhalla-gta.sh
set -euo pipefail

PORTERCHAIN_DIR="${PORTERCHAIN_DIR:-/opt/porterchain}"
EXTRACT_DIR="${EXTRACT_DIR:-$PORTERCHAIN_DIR/valhalla-extract}"
OUT_PBF="$EXTRACT_DIR/gta-150km.osm.pbf"
VOLUME="porterchain-prod_valhalla-tiles"
COMPOSE="$PORTERCHAIN_DIR/docker-compose.prod.yml"

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

find_file() {
  local f
  for f in "$@"; do
    if [[ -f "$f" ]]; then
      echo "$f"
      return 0
    fi
  done
  return 1
}

PREPARE="$(find_file \
  "$PORTERCHAIN_DIR/scripts/prepare-valhalla-gta.sh" \
  "$PORTERCHAIN_DIR/docker/scripts/prepare-valhalla-gta.sh" || true)"
TUNER="$(find_file \
  "$PORTERCHAIN_DIR/scripts/tune-valhalla-json.py" \
  "$PORTERCHAIN_DIR/docker/scripts/tune-valhalla-json.py" || true)"
JSON_SRC="$(find_file \
  "$PORTERCHAIN_DIR/valhalla/valhalla.gta-ram.json" \
  "$PORTERCHAIN_DIR/docker/valhalla/valhalla.gta-ram.json" \
  "$PORTERCHAIN_DIR/valhalla/data/valhalla.json" \
  "$PORTERCHAIN_DIR/docker/valhalla/data/valhalla.json" || true)"

if [[ -z "${PREPARE:-}" ]]; then
  err "Missing prepare-valhalla-gta.sh under $PORTERCHAIN_DIR/scripts or docker/scripts"
  exit 1
fi

mkdir -p "$EXTRACT_DIR"
info "Fetching GTA ±150 km OSM extract (not full Ontario)…"
FORCE_REFRESH="${FORCE_REFRESH:-0}" DATA_DIR="$EXTRACT_DIR" OUT_PBF="$OUT_PBF" bash "$PREPARE"
if [[ ! -f "$OUT_PBF" ]]; then
  err "Extract missing at $OUT_PBF"
  exit 1
fi
ok "Extract $(du -h "$OUT_PBF" | awk '{print $1}')"

TUNED_JSON="$(mktemp)"
trap 'rm -f "$TUNED_JSON"' EXIT
if [[ -n "${JSON_SRC:-}" && -n "${TUNER:-}" ]]; then
  python3 "$TUNER" "$JSON_SRC" -o "$TUNED_JSON"
  ok "RAM-tuned valhalla.json ready ($(wc -c < "$TUNED_JSON") bytes)"
elif [[ -n "${JSON_SRC:-}" ]]; then
  cp "$JSON_SRC" "$TUNED_JSON"
  info "No tuner on droplet — using $JSON_SRC as-is"
else
  err "Missing valhalla.json to seed the volume (needed before tile build to avoid 1GB cache)"
  exit 1
fi

info "Stopping Valhalla…"
docker stop pcd-valhalla >/dev/null 2>&1 || true

info "Replacing graph with GTA 150 km PBF + RAM-tuned json…"
docker run --rm \
  -v "${VOLUME}:/custom_files" \
  -v "${OUT_PBF}:/incoming/gta-150km.osm.pbf:ro" \
  -v "${TUNED_JSON}:/incoming/valhalla.json:ro" \
  alpine:3.22.2 \
  sh -c 'rm -rf /custom_files/* && cp /incoming/gta-150km.osm.pbf /custom_files/gta-150km.osm.pbf && cp /incoming/valhalla.json /custom_files/valhalla.json'

ok "Volume has GTA extract + tuned json"
docker run --rm -v "${VOLUME}:/custom_files" alpine:3.22.2 \
  sh -c 'du -sh /custom_files /custom_files/gta-150km.osm.pbf'

info "Rebuilding Valhalla tiles (GTA 150 km — a few minutes)…"
cd "$PORTERCHAIN_DIR"
docker compose -f "$COMPOSE" up -d --no-deps --pull never valhalla

info "Waiting for Valhalla /status (tile build)…"
for i in $(seq 1 90); do
  if docker exec pcd-valhalla curl -sf -m 5 http://localhost:8002/status 2>/dev/null | grep -q '"route"'; then
    ok "Valhalla serving GTA ±150 km tiles"
    info "Removing PBF from tile volume (tiles remain)…"
    docker exec pcd-valhalla sh -c 'rm -f /custom_files/*.osm.pbf /custom_files/*.osm.pbf.partial; if [ -s /custom_files/valhalla_tiles.tar ] && [ -d /custom_files/valhalla_tiles ]; then rm -rf /custom_files/valhalla_tiles; fi; du -sh /custom_files; ls -lh /custom_files'
    # Source PBF stays on the Mac. Do not keep a second copy on the droplet.
    if [[ "$EXTRACT_DIR" == /opt/porterchain || "$EXTRACT_DIR" == /opt/porterchain/* ]]; then
      info "Removing droplet extract at $EXTRACT_DIR"
      rm -rf "$EXTRACT_DIR"
    fi
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
