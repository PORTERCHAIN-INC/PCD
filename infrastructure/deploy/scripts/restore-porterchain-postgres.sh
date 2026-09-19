#!/usr/bin/env bash
# Restore Porterchain Postgres from gzip SQL dump — DESTRUCTIVE (§5.1.7 drill).
set -euo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "yes" ]]; then
  echo "Refusing restore without CONFIRM_RESTORE=yes"
  echo "Usage: CONFIRM_RESTORE=yes $0 /path/to/porterchain-YYYY-MM-DD.sql.gz"
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: CONFIRM_RESTORE=yes $0 /path/to/backup.sql.gz"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/infrastructure/deploy/docker-compose.prod.yml}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${POSTGRES_USER:-porterchain}"
DB_NAME="${POSTGRES_DB:-porterchain}"
DUMP="$1"

if [[ ! -f "$DUMP" ]]; then
  echo "Missing dump file: $DUMP"
  exit 1
fi

echo "Restoring $DUMP into $DB_NAME (service $SERVICE) ..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" || true

gunzip -c "$DUMP" | docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1

echo "Restore complete. Run: curl -fsS http://localhost:8001/health/ready"
