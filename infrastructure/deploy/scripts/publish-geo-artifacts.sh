#!/usr/bin/env bash
# ROLLOUT ONLY (needs Ravi's deploy OK). Copies built geo artifacts from the home build
# server to the droplet. Run on the home server. Atomic: rsync into *.next, then swap.
# Needs an SSH key for the droplet's deploy user on the home server.
set -euo pipefail
WORK=${WORK:-$HOME/pcd-geo}
DROPLET=${DROPLET:-deploy@68.183.103.49}
DEST=${DEST:-/opt/porterchain}
[ -f "$WORK/out/tiles/gta-150km.pmtiles" ] && [ -d "$WORK/out/photon/photon_data" ] || { echo "run build-geo-artifacts.sh first" >&2; exit 1; }
rsync -a --delete --partial --info=progress2 "$WORK/out/tiles/"  "$DROPLET:$DEST/tiles.next/"
rsync -a --delete --partial --info=progress2 "$WORK/out/photon/" "$DROPLET:$DEST/photon.next/"
ssh "$DROPLET" "set -e; cd $DEST
  for d in tiles photon; do rm -rf \$d.prev; [ -d \$d ] && mv \$d \$d.prev; mv \$d.next \$d; done
  docker compose -f docker-compose.prod.yml --profile geo up -d --no-deps photon
  for i in \$(seq 1 60); do docker exec pcd-photon curl -fs 'http://127.0.0.1:2322/api?q=milton&limit=1' >/dev/null && break; sleep 3; done
  docker exec pcd-photon curl -fs 'http://127.0.0.1:2322/api?q=milton&limit=1' >/dev/null && echo photon_ok"
