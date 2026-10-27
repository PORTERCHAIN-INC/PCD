#!/usr/bin/env bash
# Throwaway test infrastructure for pytest. Never the live dev stack.
#   bash scripts/test-infra.sh up    # start Postgres(PostGIS) :55432, Redis :56379, SpiceDB :55051
#   bash scripts/test-infra.sh down  # remove them (data is discarded)
# apps/api/tests/conftest.py defaults to these ports and refuses the live ones.
set -euo pipefail
PG=pcd-test-postgres; RD=pcd-test-redis; SP=pcd-test-spicedb
case "${1:-up}" in
  up)
    docker rm -f "$PG" "$RD" "$SP" >/dev/null 2>&1 || true
    docker run -d --name "$PG" -p 127.0.0.1:55432:5432 \
      -e POSTGRES_USER=porterchain -e POSTGRES_PASSWORD=porterchain -e POSTGRES_DB=porterchain_test \
      postgis/postgis:16-3.4 >/dev/null
    docker run -d --name "$RD" -p 127.0.0.1:56379:6379 redis:7-alpine >/dev/null
    docker run -d --name "$SP" -p 127.0.0.1:55051:50051 authzed/spicedb:v1.56.0 \
      serve --grpc-preshared-key porterchain-spicedb-test-key --datastore-engine memory >/dev/null
    for _ in $(seq 1 60); do
      docker exec "$PG" pg_isready -U porterchain -d porterchain_test >/dev/null 2>&1 && break; sleep 1
    done
    echo "test infra up: postgres 127.0.0.1:55432 redis 127.0.0.1:56379 spicedb 127.0.0.1:55051"
    ;;
  down) docker rm -f "$PG" "$RD" "$SP" >/dev/null 2>&1 || true; echo "test infra removed" ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
