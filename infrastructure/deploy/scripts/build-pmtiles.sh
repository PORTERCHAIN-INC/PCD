#!/usr/bin/env bash
# Build the self-hosted map tiles for MapLibre (no Google). Run on the droplet.
# Extracts GTA ±150 km (covers the service area) from the daily Protomaps planet
# build, then copies fonts + sprites so the map never calls a third party.
set -euo pipefail
OUT=${OUT:-/opt/porterchain/tiles}
BBOX=${BBOX:--81.25,42.30,-77.52,45.00}
BUILD=${BUILD:-$(date -u -d yesterday +%Y%m%d 2>/dev/null || date -u -v-1d +%Y%m%d)}
PMTILES_VERSION=${PMTILES_VERSION:-1.28.0}
mkdir -p "$OUT"
cd "$(mktemp -d)"
if ! command -v pmtiles >/dev/null; then
  curl -fsSL "https://github.com/protomaps/go-pmtiles/releases/download/v${PMTILES_VERSION}/go-pmtiles_${PMTILES_VERSION}_Linux_x86_64.tar.gz" | tar xz pmtiles
  PM=./pmtiles
else
  PM=pmtiles
fi
"$PM" extract "https://build.protomaps.com/${BUILD}.pmtiles" ontario.pmtiles --bbox="$BBOX" --maxzoom=15
mv ontario.pmtiles "$OUT/ontario.pmtiles.tmp" && mv "$OUT/ontario.pmtiles.tmp" "$OUT/ontario.pmtiles"
curl -fsSL https://github.com/protomaps/basemaps-assets/archive/refs/heads/main.tar.gz | tar xz
rm -rf "$OUT/fonts" "$OUT/sprites"
cp -r basemaps-assets-main/fonts basemaps-assets-main/sprites "$OUT/"
ls -lh "$OUT"
