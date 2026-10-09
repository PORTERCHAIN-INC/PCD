#!/usr/bin/env bash
# Porterchain — fetch, decrypt, verify and restore an off-site Postgres backup into a
# SEPARATE database (default <db>_restore_check). Never overwrites the live database;
# promoting a verified restore is a manual step (docs/runbooks/postgres-backup-restore.md).
#
# Usage:
#   restore-offsite-postgres.sh <backup-name-or-local-path> [target_db]
#   e.g. restore-offsite-postgres.sh porterchain-porterchain-20261009T071500Z.dump.age
# Env: same OFFSITE_TARGET / BACKUP_SOURCE / POSTGRES_* as the backup script, plus
#   AGE_IDENTITY_FILE (age private key)  or  BACKUP_PASSPHRASE_FILE / gpg keyring for .gpg files.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-paths.sh
source "$SCRIPT_DIR/deploy-paths.sh"
BACKUP_SOURCE="${BACKUP_SOURCE:-compose}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${POSTGRES_USER:-porterchain}"
OFFSITE_TARGET="${OFFSITE_TARGET:-}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-}"
WORK_DIR="${BACKUP_WORK_DIR:-$BACKUP_DIR/offsite}/restore"

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }
[[ $# -ge 1 ]] || die "usage: $0 <backup-name-or-path> [target_db]"
SRC="$1"
name="$(basename "$SRC")"
[[ "$name" =~ ^(.+)-([A-Za-z0-9_]+)-([0-9]{8}T[0-9]{6}Z)\.dump\.(age|gpg)$ ]] || die "unexpected backup name: $name"
SRC_DB="${BASH_REMATCH[2]}"; EXT="${BASH_REMATCH[4]}"
TARGET_DB="${2:-${SRC_DB}_restore_check}"
[[ "$TARGET_DB" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "unsafe target db"
if [[ "$TARGET_DB" == "$SRC_DB" && "${CONFIRM_OVERWRITE_LIVE:-}" != "yes" ]]; then
  die "target equals the live database name; restore to a separate DB and promote manually (see runbook)"
fi

mkdir -p "$WORK_DIR"
enc="$WORK_DIR/$name"; sumf="$WORK_DIR/${name%."$EXT"}.sha256"
fetch() { # $1=name $2=dest
  case "$OFFSITE_TARGET" in
    rclone:*) rclone copyto "${OFFSITE_TARGET#rclone:}/$1" "$2" ;;
    s3://*)   aws s3 cp ${S3_ENDPOINT_URL:+--endpoint-url "$S3_ENDPOINT_URL"} --only-show-errors "$OFFSITE_TARGET/$1" "$2" ;;
    file://*) cp "${OFFSITE_TARGET#file://}/$1" "$2" ;;
    *) die "OFFSITE_TARGET required to fetch $1" ;;
  esac
}
if [[ -f "$SRC" ]]; then
  cp "$SRC" "$enc"; [[ -f "${SRC%."$EXT"}.sha256" ]] && cp "${SRC%."$EXT"}.sha256" "$sumf"
else
  fetch "$name" "$enc"; fetch "${name%."$EXT"}.sha256" "$sumf" || log "warning: no checksum file"
fi

raw="$WORK_DIR/${name%."$EXT"}"
case "$EXT" in
  age) age -d -i "${AGE_IDENTITY_FILE:?AGE_IDENTITY_FILE required}" -o "$raw" "$enc" ;;
  gpg) if [[ -n "${BACKUP_PASSPHRASE_FILE:-}" ]]; then
         gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" -o "$raw" --decrypt "$enc"
       else gpg --batch --yes -o "$raw" --decrypt "$enc"; fi ;;
esac
if [[ -f "$sumf" ]]; then
  want="$(cut -d' ' -f1 "$sumf")"
  got="$(if command -v sha256sum >/dev/null; then sha256sum "$raw"; else shasum -a 256 "$raw"; fi | cut -d' ' -f1)"
  [[ "$want" == "$got" ]] || die "checksum mismatch (want $want got $got)"
  log "checksum OK"
fi

psql_admin() {
  case "$BACKUP_SOURCE" in
    compose)   docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -Atc "$1" ;;
    container) docker exec -i "${BACKUP_CONTAINER:?}" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -Atc "$1" ;;
    url)       psql "${BACKUP_DATABASE_URL_BASE:?}/postgres" -v ON_ERROR_STOP=1 -Atc "$1" ;;
  esac
}
psql_target() {
  case "$BACKUP_SOURCE" in
    compose)   docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" psql -U "$DB_USER" -d "$TARGET_DB" -Atc "$1" ;;
    container) docker exec -i "$BACKUP_CONTAINER" psql -U "$DB_USER" -d "$TARGET_DB" -Atc "$1" ;;
    url)       psql "$BACKUP_DATABASE_URL_BASE/$TARGET_DB" -Atc "$1" ;;
  esac
}
restore_into() {
  case "$BACKUP_SOURCE" in
    compose)   docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" pg_restore -U "$DB_USER" -d "$TARGET_DB" --no-owner --no-acl --exit-on-error <"$raw" ;;
    container) docker exec -i "$BACKUP_CONTAINER" pg_restore -U "$DB_USER" -d "$TARGET_DB" --no-owner --no-acl --exit-on-error <"$raw" ;;
    url)       pg_restore -d "$BACKUP_DATABASE_URL_BASE/$TARGET_DB" --no-owner --no-acl --exit-on-error "$raw" ;;
  esac
}

log "restoring $name into $TARGET_DB"
psql_admin "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TARGET_DB' AND pid <> pg_backend_pid();" >/dev/null
psql_admin "DROP DATABASE IF EXISTS $TARGET_DB;" >/dev/null
psql_admin "CREATE DATABASE $TARGET_DB OWNER $DB_USER;" >/dev/null
restore_into
tables="$(psql_target "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');")"
alembic="$(psql_target "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo n/a)"
log "restore OK: $TARGET_DB tables=$tables alembic=$alembic"
rm -f "$raw" "$enc"
echo "tables=$tables alembic=$alembic"
