#!/usr/bin/env bash
# Sync the PorterChain login theme to prod Keycloak and set the realm theme/i18n settings.
# Safe: no realm import, no wipe, no DB restore. Run from the repo root on a machine with `ssh porterchain-droplet`.
#   infrastructure/keycloak/deploy/apply-theme.sh            # sync theme files + realm settings
#   RECREATE=1 infrastructure/keycloak/deploy/apply-theme.sh # also recreate pcd-keycloak (first time: adds the theme mount)
set -euo pipefail
SSH=${SSH:-porterchain-droplet}
KC_DIR=/opt/porterchain/keycloak
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
stamp=$(date -u +%Y%m%dT%H%M%SZ)

ssh "$SSH" "mkdir -p $KC_DIR/themes $KC_DIR/../backups/keycloak-theme-$stamp && cp -a $KC_DIR/docker-compose.keycloak.yml $KC_DIR/../backups/keycloak-theme-$stamp/"
rsync -a --delete "$ROOT/infrastructure/keycloak/themes/porterchain/" "$SSH:$KC_DIR/themes/porterchain/"
ssh "$SSH" "chmod -R a+rX $KC_DIR/themes"
scp -q "$ROOT/infrastructure/keycloak/deploy/docker-compose.keycloak.yml" "$SSH:$KC_DIR/docker-compose.keycloak.yml"

if [ "${RECREATE:-0}" = 1 ]; then
  ssh "$SSH" "cd $KC_DIR && docker compose -f docker-compose.keycloak.yml up -d && for i in \$(seq 60); do curl -sf -o /dev/null http://127.0.0.1:58180/realms/porterchain && exit 0; sleep 3; done; exit 1"
fi
# Keycloak caches gzipped theme resources under data/tmp; drop them so CSS/JS edits show without a restart.
ssh "$SSH" "docker exec pcd-keycloak sh -c 'rm -rf /opt/keycloak/data/tmp/kc-gzip-cache/*/login/porterchain'"

ssh "$SSH" 'docker exec pcd-keycloak sh -c "K=/opt/keycloak/bin/kcadm.sh; C=/tmp/kc.cfg
  \$K config credentials --server http://localhost:8080 --realm master --user \"\$KC_BOOTSTRAP_ADMIN_USERNAME\" --password \"\$KC_BOOTSTRAP_ADMIN_PASSWORD\" --config \$C >/dev/null 2>&1
  \$K get realms/porterchain --config \$C --fields loginTheme,emailTheme,internationalizationEnabled,supportedLocales,defaultLocale
  \$K update realms/porterchain --config \$C -s loginTheme=porterchain -s emailTheme=porterchain -s internationalizationEnabled=true -s supportedLocales=[\\\"en\\\",\\\"fr\\\"] -s defaultLocale=en
  \$K get realms/porterchain --config \$C --fields loginTheme,emailTheme,internationalizationEnabled,supportedLocales,defaultLocale"'
echo "theme applied (backup: backups/keycloak-theme-$stamp)"
