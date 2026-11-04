#!/usr/bin/env bash
# Throwaway Valhalla (:58002) + VROOM (:53000, router: valhalla) for the opt-in 78-stop test.
# Never the live porterchain-valhalla (:8002) / porterchain-osrm (:5000). Tiles are COPIED to /tmp, read-only mount.
#   bash scripts/test-routing.sh up | down
#   PCD_TEST_VALHALLA_URL=http://127.0.0.1:58002 PCD_TEST_VROOM_URL=http://127.0.0.1:53000 pytest tests/test_vrp_live_engines.py
set -euo pipefail
SRC=${VALHALLA_TILES_SRC:-/home/pcd/pcd-local/infrastructure/docker/valhalla/data}
D=/tmp/pcd-test-valhalla; V=/tmp/pcd-test-vroom; NET=pcd-test-route
IMG=ghcr.io/valhalla/valhalla-scripted@sha256:9ba06c00f41fabec8d3cb2e7ec3c39023be7a410d245049d76af3b494e1ce674
VIMG=ghcr.io/vroom-project/vroom-docker:v1.14.0
case "${1:-up}" in
  up)
    docker rm -f pcd-test-valhalla pcd-test-vroom >/dev/null 2>&1 || true
    mkdir -p "$D" "$V"
    [ -f "$D/valhalla_tiles.tar" ] || cp "$SRC/valhalla_tiles.tar" "$D/"
    python3 - "$SRC/valhalla.json" "$D/valhalla.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
for k in ("auto", "truck"):
    c["service_limits"][k]["max_matrix_location_pairs"] = 40000  # 78 stops = ~5k pairs (default 2500)
json.dump(c, open(sys.argv[2], "w"), indent=1)
PY
    docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
    docker run -d --name pcd-test-valhalla --network "$NET" -p 127.0.0.1:58002:8002 -v "$D:/custom_files:ro" \
      --entrypoint valhalla_service "$IMG" /custom_files/valhalla.json 2 >/dev/null
    docker run --rm --entrypoint cat "$VIMG" /vroom-express/config.yml | python3 -c "
import sys; s=sys.stdin.read().replace(\"router: 'osrm'\", \"router: 'valhalla'\"); i=s.index('  valhalla:')
print(s[:i]+'  valhalla:\n'+''.join(f\"    {p}:\n      host: 'pcd-test-valhalla'\n      port: '8002'\n\" for p in ('auto','truck')))" > "$V/config.yml"
    docker run -d --name pcd-test-vroom --network "$NET" -p 127.0.0.1:53000:3000 -v "$V:/conf" -e VROOM_ROUTER=valhalla "$VIMG" >/dev/null
    for _ in $(seq 1 30); do curl -sf -X POST 127.0.0.1:58002/status >/dev/null 2>&1 && break; sleep 1; done
    echo "test routing up: valhalla 127.0.0.1:58002, vroom 127.0.0.1:53000"
    ;;
  down)
    docker rm -f pcd-test-valhalla pcd-test-vroom >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    rm -rf "$D" "$V"; echo "test routing removed (tiles copy deleted)" ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
