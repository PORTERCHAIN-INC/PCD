#!/usr/bin/env bash
# Porterchain Postgres backup — local dev or prod droplet (§5.1.7, DD-28).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/infrastructure/deploy/docker-compose.prod.yml}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${POSTGRES_USER:-porterchain}"
DB_NAME="${POSTGRES_DB:-porterchain}"
STAMP="$(date +%F-%H%M%S)"
OUTPUT="${1:-$ROOT/backups/porterchain-$STAMP.sql.gz}"

mkdir -p "$(dirname "$OUTPUT")"

echo "Backing up $DB_NAME from compose service $SERVICE ..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl | gzip -9 >"$OUTPUT"

BYTES="$(wc -c <"$OUTPUT" | tr -d ' ')"
echo "Wrote $OUTPUT ($BYTES bytes)"
echo "Verify: gunzip -c \"$OUTPUT\" | head -5"
