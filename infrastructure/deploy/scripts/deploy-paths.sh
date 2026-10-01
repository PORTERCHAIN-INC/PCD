#!/usr/bin/env bash
# Layout for deploy scripts. Caller sets SCRIPT_DIR to its own directory.
# Droplet copy: /opt/porterchain/{scripts,docker-compose.prod.yml,backups}
# Repo checkout: infrastructure/deploy/scripts and <repo>/backups

if [[ -z "${SCRIPT_DIR:-}" ]]; then
  echo "SCRIPT_DIR must be set before sourcing deploy-paths.sh" >&2
  exit 1
fi

DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ -f "$DEPLOY_DIR/../../package.json" ]]; then
  REPO_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
else
  REPO_ROOT="$DEPLOY_DIR"
fi

COMPOSE_FILE="${COMPOSE_FILE:-$DEPLOY_DIR/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
