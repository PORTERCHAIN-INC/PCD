#!/usr/bin/env bash
# Record the running app images, then dump Postgres, before repair_and_migrate.py.
# Full deploy calls capture-images before pull, and capture-database after the
# data plane is up and before migrate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy-paths.sh
source "$SCRIPT_DIR/deploy-paths.sh"

PENDING="$BACKUP_DIR/pre-migrate-pending.manifest"
KEEP_DUMPS=3

usage() {
  echo "Usage: $0 capture-images | capture-database" >&2
  exit 2
}

# Read running images from container labels, not `docker compose ps`: compose
# interpolates the *new* compose file against the *old* .env here (the new file is
# already copied, secrets are not synced yet), and a missing required var aborted
# the 2026-11-04 deploy before anything was recorded.
image_for() {
  local service="$1"
  docker ps --filter "label=com.docker.compose.service=${service}" --filter status=running \
    --format '{{.Image}}' | head -n1
}

# Pre-deploy config (.env, compose file, Caddyfile) staged by deploy.yml *before*
# the new files are copied. Moved under a stamped dir so rollback restores it.
STAGED_CONFIG="$BACKUP_DIR/pre-deploy-config-staged"

capture_config() {
  local stamp="$1" dest
  dest="$BACKUP_DIR/pre-deploy-config-$stamp"
  if [[ -d "$STAGED_CONFIG" ]]; then
    rm -rf "$dest"
    mv "$STAGED_CONFIG" "$dest"
  else
    echo "::warning::no staged pre-deploy config; snapshotting current files (may already be the new release)" >&2
    mkdir -p "$dest"
    for f in .env docker-compose.prod.yml Caddyfile; do
      [[ -f "$DEPLOY_DIR/$f" ]] && cp -a "$DEPLOY_DIR/$f" "$dest/$f"
    done
  fi
  chmod 700 "$dest"
  echo "$dest"
}

write_image_line() {
  local key="$1"
  local service="$2"
  local image
  image="$(image_for "$service" || true)"
  printf '%s=%s\n' "$key" "$image"
}

capture_images() {
  mkdir -p "$BACKUP_DIR"
  local stamp
  stamp="$(date +%F-%H%M%S)"
  {
    echo "# Running images before this full deploy. Database dump is added by capture-database."
    echo "STAMP=$stamp"
    write_image_line API_IMAGE api
    write_image_line WEB_IMAGE web
    write_image_line ADMIN_IMAGE admin
    write_image_line MERCHANT_IMAGE merchant
    write_image_line DRIVER_IMAGE driver
    write_image_line CUSTOMER_IMAGE customer
    echo "CONFIG_DIR=$(capture_config "$stamp")"
  } >"$PENDING"
  if grep -q '=$' "$PENDING"; then
    echo "A running app image is missing in $PENDING." >&2
    echo "Full deploy needs api, web, admin, merchant, driver, and customer up so rollback can pin them." >&2
    exit 1
  fi
  echo "Recorded running images in $PENDING"
}

capture_database() {
  if [[ ! -f "$PENDING" ]]; then
    echo "Missing $PENDING — run capture-images before pull." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$PENDING"
  if [[ -z "${STAMP:-}" ]]; then
    echo "Pending manifest has no STAMP: $PENDING" >&2
    exit 1
  fi

  local dump manifest
  dump="$BACKUP_DIR/pre-migrate-$STAMP.sql.gz"
  manifest="$BACKUP_DIR/pre-migrate-$STAMP.manifest"
  bash "$SCRIPT_DIR/backup-porterchain-postgres.sh" "$dump"
  chmod 600 "$dump"
  local bytes
  bytes="$(wc -c <"$dump" | tr -d ' ')"
  if [[ "$bytes" -lt 1024 ]]; then
    echo "Refusing pre-migrate dump under 1024 bytes ($bytes): $dump" >&2
    exit 1
  fi

  {
    echo "# Pre-migrate snapshot. rollback-prod.sh restores DUMP and these image refs."
    echo "STAMP=$STAMP"
    echo "DUMP=$dump"
    echo "API_IMAGE=${API_IMAGE:-}"
    echo "WEB_IMAGE=${WEB_IMAGE:-}"
    echo "ADMIN_IMAGE=${ADMIN_IMAGE:-}"
    echo "MERCHANT_IMAGE=${MERCHANT_IMAGE:-}"
    echo "DRIVER_IMAGE=${DRIVER_IMAGE:-}"
    echo "CUSTOMER_IMAGE=${CUSTOMER_IMAGE:-}"
    echo "CONFIG_DIR=${CONFIG_DIR:-}"
  } >"$manifest"
  cp "$manifest" "$BACKUP_DIR/pre-migrate-latest.manifest"
  rm -f "$PENDING"

  local old
  # Keep the newest KEEP_DUMPS dumps and their manifests. latest.manifest is a copy.
  # shellcheck disable=SC2012
  old="$(ls -1t "$BACKUP_DIR"/pre-migrate-*.sql.gz 2>/dev/null | tail -n +"$((KEEP_DUMPS + 1))" || true)"
  if [[ -n "$old" ]]; then
    while IFS= read -r path; do
      [[ -z "$path" ]] && continue
      rm -f "$path" "${path%.sql.gz}.manifest"
      rm -rf "$BACKUP_DIR/pre-deploy-config-$(basename "${path%.sql.gz}" | sed 's/^pre-migrate-//')"
      echo "Pruned old pre-migrate snapshot $path"
    done <<<"$old"
  fi

  echo "Pre-migrate snapshot ready: $manifest"
}

case "${1:-}" in
  capture-images) capture_images ;;
  capture-database) capture_database ;;
  *) usage ;;
esac
