#!/usr/bin/env bash
# Build local OSRM graphs from the same GTA ±150 km PBF as Valhalla.
# Coverage is intentionally ±150 km around downtown Toronto — not full Ontario.
#
#   bash infrastructure/docker/scripts/prepare-valhalla-gta.sh   # PBF once
#   bash infrastructure/docker/scripts/prepare-osrm-gta.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PBF="${PBF:-$ROOT/infrastructure/docker/valhalla/data/gta-150km.osm.pbf}"
OSRM_DIR="${OSRM_DIR:-$ROOT/infrastructure/docker/osrm/data}"
IMAGE="ghcr.io/project-osrm/osrm-backend:v5.27.1"

if [[ ! -f "$PBF" ]]; then
  echo "Missing $PBF — run infrastructure/docker/scripts/prepare-valhalla-gta.sh first" >&2
  exit 1
fi

mkdir -p "$OSRM_DIR"
cp -f "$PBF" "$OSRM_DIR/gta-150km.osm.pbf"

if [[ -f "$OSRM_DIR/gta-150km.osrm" ]] && [[ "${FORCE_REFRESH:-0}" != "1" ]]; then
  echo "Already have $OSRM_DIR/gta-150km.osrm — set FORCE_REFRESH=1 to rebuild"
  exit 0
fi

echo "Extracting OSRM MLD graph from GTA ±150 km PBF ($IMAGE)…"
docker run --rm -t -v "$OSRM_DIR:/data" "$IMAGE" osrm-extract -p /opt/car.lua /data/gta-150km.osm.pbf
docker run --rm -t -v "$OSRM_DIR:/data" "$IMAGE" osrm-partition /data/gta-150km.osrm
docker run --rm -t -v "$OSRM_DIR:/data" "$IMAGE" osrm-customize /data/gta-150km.osrm
echo "OSRM graph ready in $OSRM_DIR — start with docker compose --profile routing up -d osrm"
