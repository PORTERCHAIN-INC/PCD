#!/usr/bin/env bash
# Throwaway Keycloak for integration tests: container pcd-test-keycloak on :18180, no volume.
# Never touches pch-keycloak (8180/8543). Legacy token exchange (native Apple/Google id_token ->
# Keycloak tokens) needs the token-exchange + admin-fine-grained-authz:v1 features. up|down
set -euo pipefail
NAME=pcd-test-keycloak
PORT="${PCD_TEST_KEYCLOAK_PORT:-18180}"
IMAGE="${PCD_TEST_KEYCLOAK_IMAGE:-quay.io/keycloak/keycloak:26.8.1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-up}" in
  up)
    tmp="$(mktemp -d)"; chmod 755 "$tmp"
    GOOGLE_CLIENT_ID=test-google GOOGLE_CLIENT_SECRET=test-google-secret APPLE_IDP_ENABLED=false \
      bash "$ROOT/infrastructure/keycloak/render-realm.sh" "$tmp/porterchain-realm.json" >/dev/null
    chmod 644 "$tmp/porterchain-realm.json"
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8080" \
      -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=test-admin-only \
      -v "$tmp:/opt/keycloak/data/import:ro" "$IMAGE" start-dev --import-realm --features=token-exchange,admin-fine-grained-authz:v1 >/dev/null
    for _ in $(seq 1 90); do
      curl -fsS "http://127.0.0.1:${PORT}/realms/porterchain/.well-known/openid-configuration" >/dev/null 2>&1 && { echo "keycloak up :$PORT"; exit 0; }
      sleep 2
    done
    docker logs --tail 60 "$NAME"; exit 1 ;;
  down) docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "keycloak down" ;;
esac
