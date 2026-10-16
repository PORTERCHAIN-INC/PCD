#!/usr/bin/env bash
# Build the free map + address-search artifacts for GTA +150 km. Run on the HOME BUILD
# SERVER (never on the droplet: the Photon import needs ~4 GB heap). No Docker, no root:
# a user-space JDK, photon.jar and go-pmtiles are fetched into $WORK/bin.
#
# Output ($WORK/out):
#   tiles/gta-150km.pmtiles   Protomaps basemap, z0-15, clipped to the GTA bbox
#   tiles/fonts, tiles/sprites  glyphs + sprites so the map makes no third-party calls
#   photon/photon_data + photon.jar  Photon (OpenSearch) index, places within 155 km of downtown
#
# Then publish with publish-geo-artifacts.sh (rsync to the droplet).
set -euo pipefail
WORK=${WORK:-$HOME/pcd-geo}
BBOX=${BBOX:--81.245,42.306,-77.521,45.000}          # same as prepare-valhalla-gta.sh
BUILD=${BUILD:-$(date -u -d '2 days ago' +%Y%m%d)}     # Protomaps daily planet build
PHOTON_VERSION=${PHOTON_VERSION:-1.3.0}
PHOTON_SHA256=${PHOTON_SHA256:-a89707c0045e4807b2a1180e132e68e108d998709f48b6c94b98a6e281f571a5}
PMTILES_VERSION=${PMTILES_VERSION:-1.31.2}
DUMP_URL=${DUMP_URL:-https://download1.graphhopper.com/public/north-america/canada/photon-dump-canada-1.0-latest.jsonl.zst}
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$WORK"/{bin,dl,out/tiles,out.new}
cd "$WORK/bin"
[ -x jdk/bin/java ] || { curl -fsSL -o jdk.tgz "https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse"; tar xzf jdk.tgz; rm jdk.tgz; ln -sfn "$(ls -d jdk-*-jre | head -1)" jdk; }
[ -f "photon-$PHOTON_VERSION.jar" ] || curl -fsSL -o "photon-$PHOTON_VERSION.jar" "https://github.com/komoot/photon/releases/download/$PHOTON_VERSION/photon-$PHOTON_VERSION.jar"
echo "$PHOTON_SHA256  photon-$PHOTON_VERSION.jar" | sha256sum -c -
[ -x pmtiles ] || curl -fsSL "https://github.com/protomaps/go-pmtiles/releases/download/v$PMTILES_VERSION/go-pmtiles_${PMTILES_VERSION}_Linux_x86_64.tar.gz" | tar xz pmtiles

echo "== tiles (Protomaps build $BUILD)"
./pmtiles extract "https://build.protomaps.com/$BUILD.pmtiles" "$WORK/out.new/gta-150km.pmtiles" --bbox="$BBOX" --maxzoom=15 --download-threads=8
./pmtiles verify "$WORK/out.new/gta-150km.pmtiles"
curl -fsSL https://github.com/protomaps/basemaps-assets/archive/refs/heads/main.tar.gz | tar xz -C "$WORK/out.new"

echo "== photon (Canada dump -> 155 km filter -> index)"
curl -fsSL -C - -o "$WORK/dl/canada.jsonl.zst" "$DUMP_URL" || curl -fsSL -o "$WORK/dl/canada.jsonl.zst" "$DUMP_URL"
rm -rf "$WORK/out.new/photon"; mkdir -p "$WORK/out.new/photon"
zstd -dc "$WORK/dl/canada.jsonl.zst" | python3 "$HERE/filter_photon_gta.py" \
  | ./jdk/bin/java -Xmx4g -jar "photon-$PHOTON_VERSION.jar" import -import-file - \
      -data-dir "$WORK/out.new/photon" -languages en,fr -country-codes ca

echo "== smoke test"
./jdk/bin/java -Xmx512m -jar "photon-$PHOTON_VERSION.jar" serve -data-dir "$WORK/out.new/photon" -listen-port 23222 & P=$!
for i in $(seq 1 60); do curl -fs "http://127.0.0.1:23222/api?q=toronto&limit=1" >/dev/null && break; sleep 2; done
curl -fs "http://127.0.0.1:23222/api?q=8500+Mount+Pleasant+Way+Milton&limit=1" | grep -q Milton
kill $P; wait $P 2>/dev/null || true

rm -rf "$WORK/out.prev"; [ -d "$WORK/out" ] && mv "$WORK/out" "$WORK/out.prev"
mkdir -p "$WORK/out/tiles"
mv "$WORK/out.new/gta-150km.pmtiles" "$WORK/out/tiles/"
mv "$WORK/out.new/basemaps-assets-main/fonts" "$WORK/out.new/basemaps-assets-main/sprites" "$WORK/out/tiles/"
mv "$WORK/out.new/photon" "$WORK/out/photon"; cp "$WORK/bin/photon-$PHOTON_VERSION.jar" "$WORK/out/photon/photon.jar"
rm -rf "$WORK/out.new"
du -sh "$WORK/out/tiles/gta-150km.pmtiles" "$WORK/out/tiles/fonts" "$WORK/out/photon"
echo "built: $BUILD $(date -u +%FT%TZ)" > "$WORK/out/BUILD_INFO"
