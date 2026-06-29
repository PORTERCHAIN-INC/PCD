#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT/infrastructure/docker/docker-compose.yml"
ENV_FILE="$ROOT/infrastructure/docker/.env"

cd "$ROOT/infrastructure/docker"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating $ENV_FILE from .env.example — edit secrets before production use."
  cp .env.example "$ENV_FILE"
fi

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --profile core "$@"
