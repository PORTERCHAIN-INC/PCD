#!/usr/bin/env bash
# Throwaway Garage (S3) for media tests. Never the live pch-infra-garage-1 (:3900).
#   bash scripts/test-media.sh up    # Garage S3 on 127.0.0.1:53900, bucket pod-test; writes /tmp/pcd-test-garage/env
#   bash scripts/test-media.sh down
set -euo pipefail
N=pcd-test-garage; D=/tmp/pcd-test-garage
case "${1:-up}" in
  up)
    docker rm -f "$N" >/dev/null 2>&1 || true; rm -rf "$D"; mkdir -p "$D/meta" "$D/data"
    cat > "$D/garage.toml" <<TOML
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "sqlite"
replication_factor = 1
rpc_bind_addr = "[::]:3901"
rpc_public_addr = "127.0.0.1:3901"
rpc_secret = "$(openssl rand -hex 32)"
[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:3900"
root_domain = ".s3.garage.localhost"
TOML
    docker run -d --name "$N" -p 127.0.0.1:53900:3900 -v "$D/garage.toml:/etc/garage.toml" \
      -v "$D/meta:/var/lib/garage/meta" -v "$D/data:/var/lib/garage/data" dxflrs/garage:v2.5.0 >/dev/null
    G="docker exec $N /garage"
    for _ in $(seq 1 30); do $G status >/dev/null 2>&1 && break; sleep 1; done
    NODE=$($G node id -q | cut -d@ -f1)
    $G layout assign -z dc1 -c 1G "$NODE" >/dev/null
    $G layout apply --version 1 >/dev/null
    $G bucket create pod-test >/dev/null
    OUT=$($G key create pod-test-key)
    KID=$(echo "$OUT" | awk '/Key ID/ {print $NF}'); SEC=$(echo "$OUT" | awk '/Secret key/ {print $NF}')
    $G bucket allow --read --write pod-test --key pod-test-key >/dev/null
    umask 077
    printf 'POD_S3_ENDPOINT=http://127.0.0.1:53900\nPOD_S3_BUCKET=pod-test\nPOD_S3_REGION=garage\nPOD_S3_ACCESS_KEY_ID=%s\nPOD_S3_SECRET_ACCESS_KEY=%s\n' "$KID" "$SEC" > "$D/env"
    echo "test garage up: 127.0.0.1:53900 bucket pod-test (env in $D/env)"
    ;;
  down) docker rm -f "$N" >/dev/null 2>&1 || true; rm -rf "$D"; echo "test garage removed" ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
