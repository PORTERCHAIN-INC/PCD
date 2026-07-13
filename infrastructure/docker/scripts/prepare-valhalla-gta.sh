#!/usr/bin/env bash
# Prepare a ~150 km GTA downtown OSM extract for local Valhalla (no full Ontario).
# Downtown Toronto centre: 43.6532 N, 79.3832 W → ±150 km bbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DATA_DIR="$ROOT/infrastructure/docker/valhalla/data"
OUT_PBF="$DATA_DIR/gta-150km.osm.pbf"

# 150 km around downtown Toronto (Nathan Phillips / Yonge–Dundas)
SW_LNG=-81.245
SW_LAT=42.306
NE_LNG=-77.521
NE_LAT=45.000
CITY="PorterChain-GTA-150km"
EMAIL="${BBBIKE_EMAIL:-nobody}"

mkdir -p "$DATA_DIR"

if [[ -f "$OUT_PBF" ]] && [[ "${FORCE_REFRESH:-0}" != "1" ]]; then
  echo "Already have $OUT_PBF ($(du -h "$OUT_PBF" | awk '{print $1}')) — set FORCE_REFRESH=1 to re-fetch"
  exit 0
fi

echo "Requesting BBBike extract for GTA ~150 km ($SW_LNG,$SW_LAT → $NE_LNG,$NE_LAT)…"
HTML=$(curl -sL -G 'https://extract.bbbike.org/' \
  --data-urlencode 'lang=en' \
  --data-urlencode 'format=osm.pbf' \
  --data-urlencode "sw_lng=$SW_LNG" \
  --data-urlencode "sw_lat=$SW_LAT" \
  --data-urlencode "ne_lng=$NE_LNG" \
  --data-urlencode "ne_lat=$NE_LAT" \
  --data-urlencode "city=$CITY" \
  --data-urlencode "email=$EMAIL" \
  --data-urlencode 'submit=extract' \
  --data-urlencode 'layers=B0000000FT' \
  --data-urlencode 'as=1.0' \
  --data-urlencode "coords=${SW_LNG},${SW_LAT}|${NE_LNG},${SW_LAT}|${NE_LNG},${NE_LAT}|${SW_LNG},${NE_LAT}|${SW_LNG},${SW_LAT}")

URL=$(echo "$HTML" | sed -n 's/.*bbbike_extract_download_url: \([^ ]*\) -->.*/\1/p' | head -1)
if [[ -z "$URL" ]]; then
  echo "BBBike did not return a download URL. Response snippet:" >&2
  echo "$HTML" | head -40 >&2
  exit 1
fi

echo "Extract queued: $URL"
echo "Waiting for BBBike (usually 2–7 minutes)…"
for i in $(seq 1 60); do
  code=$(curl -sI -L --max-time 30 "$URL" | awk 'BEGIN{c=""} /^HTTP/{c=$2} END{print c}')
  len=$(curl -sI -L --max-time 30 "$URL" | awk 'tolower($1)=="content-length:"{print $2}' | tr -d '\r' | tail -1)
  echo "  poll $i: HTTP $code size=${len:-?}"
  if [[ "$code" == "200" && -n "${len:-}" && "$len" -gt 1000000 ]]; then
    echo "Downloading → $OUT_PBF"
    curl -fL --max-time 900 -o "$OUT_PBF.partial" "$URL"
    mv "$OUT_PBF.partial" "$OUT_PBF"
    ls -lah "$OUT_PBF"
    echo "Done. Start Valhalla with: pnpm docker:up:routing"
    exit 0
  fi
  sleep 15
done

echo "Timed out waiting for BBBike extract. Check: https://download2.bbbike.org/osm/extract" >&2
exit 1
