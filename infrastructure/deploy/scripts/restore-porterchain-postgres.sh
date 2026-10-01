#!/usr/bin/env bash
# Restore Porterchain Postgres from a gzip SQL dump — DESTRUCTIVE (§5.1.7 drill).
# Loads into porterchain_restore, then swaps that database over porterchain
# only after the load succeeds. The spicedb database is not touched.
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-paths.sh
source "$SCRIPT_DIR/deploy-paths.sh"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${POSTGRES_USER:-porterchain}"
DB_NAME="${POSTGRES_DB:-porterchain}"
RESTORE_DB="${DB_NAME}_restore"
DUMP="$1"
OLD_DB="${DB_NAME}_old"

if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ || ! "$DB_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  echo "Refusing unsafe database name or user"
  exit 1
fi

if [[ ! -f "$DUMP" ]]; then
  echo "Missing dump file: $DUMP"
  exit 1
fi

gzip -t "$DUMP"

psql_postgres() {
  docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
    psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "$1"
}

echo "Restoring $DUMP via $RESTORE_DB, then swapping onto $DB_NAME ..."
psql_postgres "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$RESTORE_DB' AND pid <> pg_backend_pid();"
psql_postgres "DROP DATABASE IF EXISTS $RESTORE_DB;"
psql_postgres "CREATE DATABASE $RESTORE_DB OWNER $DB_USER;"

gunzip -c "$DUMP" | docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  psql -U "$DB_USER" -d "$RESTORE_DB" -v ON_ERROR_STOP=1

# Rename the live database aside first. If the swap fails, put it back.
psql_postgres "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"
psql_postgres "ALTER DATABASE $DB_NAME RENAME TO $OLD_DB;"
if ! psql_postgres "ALTER DATABASE $RESTORE_DB RENAME TO $DB_NAME;"; then
  echo "Swap failed; returning $OLD_DB to $DB_NAME"
  psql_postgres "ALTER DATABASE $OLD_DB RENAME TO $DB_NAME;" || true
  exit 1
fi
psql_postgres "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$OLD_DB' AND pid <> pg_backend_pid();"
psql_postgres "DROP DATABASE $OLD_DB;"

echo "Restore complete. $DB_NAME replaced. spicedb was not changed."
