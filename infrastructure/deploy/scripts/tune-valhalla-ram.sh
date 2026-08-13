#!/usr/bin/env bash
# Apply RAM-tuned Valhalla json on the live tile volume (GTA ±150 km unchanged).
# Restarts pcd-valhalla. Bike/pedestrian graph size needs a later tile rebuild.
#
# Usage (droplet as root):
#   bash /opt/porterchain/scripts/tune-valhalla-ram.sh
set -euo pipefail

PORTERCHAIN_DIR="${PORTERCHAIN_DIR:-/opt/porterchain}"
VOLUME="${VOLUME:-porterchain-prod_valhalla-tiles}"
COMPOSE="${COMPOSE:-$PORTERCHAIN_DIR/docker-compose.prod.yml}"
TUNER="${TUNER:-}"
for cand in \
  "$PORTERCHAIN_DIR/scripts/tune-valhalla-json.py" \
  "$PORTERCHAIN_DIR/docker/scripts/tune-valhalla-json.py"; do
  if [[ -f "$cand" ]]; then
    TUNER="$cand"
    break
  fi
done

info() { echo "ℹ  $*"; }
ok() { echo "✔  $*"; }
err() { echo "✖  $*" >&2; }

if [[ -z "${TUNER}" || ! -f "$TUNER" ]]; then
  err "Missing tune-valhalla-json.py under $PORTERCHAIN_DIR/scripts or docker/scripts"
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

info "Copying valhalla.json from volume $VOLUME…"
docker run --rm -v "${VOLUME}:/custom_files" alpine:3.22.2 \
  cat /custom_files/valhalla.json >"$TMP"
if [[ ! -s "$TMP" ]]; then
  err "No valhalla.json in the tiles volume — start Valhalla once or run rebuild-valhalla-gta.sh"
  exit 1
fi

python3 "$TUNER" "$TMP"
ok "Patched cache=256MiB, LRU on, bike/ped off (next rebuild), smaller reserved labels"

info "Writing json back to volume…"
docker run --rm \
  -v "${VOLUME}:/custom_files" \
  -v "${TMP}:/incoming/valhalla.json:ro" \
  alpine:3.22.2 \
  cp /incoming/valhalla.json /custom_files/valhalla.json

info "Restarting Valhalla…"
cd "$PORTERCHAIN_DIR"
docker compose -f "$COMPOSE" up -d --no-deps --pull never valhalla
ok "Valhalla restarted with RAM-tuned json (GTA ±150 km tiles kept)"
