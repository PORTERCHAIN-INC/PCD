#!/usr/bin/env bash
# Roll a full deploy back to the pre-migrate snapshot.
# Pulls the recorded image tags first. When the manifest has a dump, loads it
# into a side database and swaps that over porterchain. Does not migrate.
# The spicedb database is left alone. A manifest with image refs and no DUMP
# pins images only.
set -euo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "yes" ]]; then
  echo "Refusing rollback without CONFIRM_RESTORE=yes" >&2
  echo "Usage: CONFIRM_RESTORE=yes $0 [manifest]" >&2
  echo "Default manifest: backups/pre-migrate-latest.manifest" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-paths.sh
source "$SCRIPT_DIR/deploy-paths.sh"

MANIFEST="${1:-$BACKUP_DIR/pre-migrate-latest.manifest}"
if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing pre-migrate manifest: $MANIFEST" >&2
  exit 1
fi

DUMP=""
API_IMAGE=""
WEB_IMAGE=""
ADMIN_IMAGE=""
MERCHANT_IMAGE=""
DRIVER_IMAGE=""
CUSTOMER_IMAGE=""

while IFS='=' read -r key value; do
  case "$key" in
    DUMP | API_IMAGE | WEB_IMAGE | ADMIN_IMAGE | MERCHANT_IMAGE | DRIVER_IMAGE | CUSTOMER_IMAGE)
      printf -v "$key" '%s' "$value"
      ;;
  esac
done <"$MANIFEST"

if [[ -n "$DUMP" && ! -f "$DUMP" ]]; then
  echo "Manifest $MANIFEST points at a missing dump: $DUMP" >&2
  exit 1
fi

for key in API_IMAGE WEB_IMAGE ADMIN_IMAGE MERCHANT_IMAGE DRIVER_IMAGE CUSTOMER_IMAGE; do
  if [[ -z "${!key}" ]]; then
    echo "Manifest $MANIFEST is missing $key." >&2
    echo "Refusing rollback so compose does not fall through to :latest (that tag is this release)." >&2
    exit 1
  fi
done

export_if_set() {
  local key="$1"
  local value="$2"
  if [[ -n "$value" ]]; then
    export "$key=$value"
    echo "Pin $key=$value"
  else
    echo "No recorded $key — compose will use its default image" >&2
  fi
}

export_if_set API_IMAGE "$API_IMAGE"
export_if_set WEB_IMAGE "$WEB_IMAGE"
export_if_set ADMIN_IMAGE "$ADMIN_IMAGE"
export_if_set MERCHANT_IMAGE "$MERCHANT_IMAGE"
export_if_set DRIVER_IMAGE "$DRIVER_IMAGE"
export_if_set CUSTOMER_IMAGE "$CUSTOMER_IMAGE"

echo "Pulling pinned images before any database change (needs a GHCR login if the tag was pruned)..."
docker compose -f "$COMPOSE_FILE" pull api worker web admin merchant driver customer

if [[ -n "$DUMP" ]]; then
  echo "Stopping app writers before database swap..."
  docker compose -f "$COMPOSE_FILE" stop api worker web admin merchant driver customer
  CONFIRM_RESTORE=yes bash "$SCRIPT_DIR/restore-porterchain-postgres.sh" "$DUMP"
else
  echo "Manifest has no DUMP — pinning recorded images only. Database was not changed."
fi

bash "$SCRIPT_DIR/recover-prod-stack.sh"

echo "Waiting for API health after rollback..."
healthy=0
for _ in $(seq 1 18); do
  if docker compose -f "$COMPOSE_FILE" exec -T api curl -fsS http://localhost:8001/health >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 5
done
if [[ "$healthy" != 1 ]]; then
  echo "Rollback finished but the API did not become healthy (dump=${DUMP:-none})" >&2
  exit 1
fi

echo "Rollback complete from $MANIFEST (no migration was run)"
