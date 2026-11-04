#!/usr/bin/env bash
# Adds/updates Google + Apple sign-in, auto-link by verified email, email verification (SMTP) on an EXISTING
# Keycloak realm via kcadm (never recreates Keycloak). Keys come from env / a SOPS-decrypted env file:
#   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
#   APPLE_SERVICES_ID, APPLE_TEAM_ID, APPLE_KEY_ID, APPLE_P8_FILE (path to the .p8)
# SOCIAL_LOGIN_ENABLED=true turns a provider on ONLY when its keys are present; otherwise it stays disabled (hidden).
# Usage (local): KC_CONTAINER=pcd-ls-keycloak SOCIAL_ENV=$HOME/.pcd-local-stack/social.env bash scripts/keycloak-social-setup.sh
set -euo pipefail
C=${KC_CONTAINER:-pcd-ls-keycloak}; REALM=${KC_REALM:-porterchain}; LS_DIR=${LS_DIR:-/home/pcd/.pcd-local-stack}
set -a; . "$LS_DIR/stack.env"; [ -n "${SOCIAL_ENV:-}" ] && [ -f "$SOCIAL_ENV" ] && . "$SOCIAL_ENV"; set +a
SMTP_HOST=${KC_SMTP_HOST:-pcd-ls-mailpit} SMTP_PORT=${KC_SMTP_PORT:-1025} SMTP_FROM=${KC_SMTP_FROM:-no-reply@porterchain.com}
on() { [ "${SOCIAL_LOGIN_ENABLED:-false}" = true ] && [ -n "$1" ] && echo true || echo false; }
G_ON=$(on "${GOOGLE_OAUTH_CLIENT_SECRET:-}"); A_ON=$(on "${APPLE_KEY_ID:-}")
P8=""; [ -n "${APPLE_P8_FILE:-}" ] && [ -f "$APPLE_P8_FILE" ] && P8=$(cat "$APPLE_P8_FILE")
docker exec -i -e P="$KC_ADMIN_PASSWORD" -e R="$REALM" -e G_ON="$G_ON" -e A_ON="$A_ON" \
  -e GID="${GOOGLE_OAUTH_CLIENT_ID:-not-configured}" -e GSEC="${GOOGLE_OAUTH_CLIENT_SECRET:-not-configured}" \
  -e AID="${APPLE_SERVICES_ID:-not-configured}" -e ATEAM="${APPLE_TEAM_ID:-not-configured}" -e AKEY="${APPLE_KEY_ID:-not-configured}" -e AP8="$P8" \
  -e SH="$SMTP_HOST" -e SP="$SMTP_PORT" -e SF="$SMTP_FROM" -e SU="${KC_SMTP_USER:-}" -e SPW="${KC_SMTP_PASSWORD:-}" \
  "$C" bash -s <<'IN'
set -e; K=/opt/keycloak/bin/kcadm.sh
$K config credentials --server http://localhost:8080 --realm master --user admin --password "$P" >/dev/null 2>&1
AUTH=false; [ -n "$SU" ] && AUTH=true
$K update realms/$R -s verifyEmail=true -s rememberMe=true -s resetPasswordAllowed=true -s loginWithEmailAllowed=true \
  -s duplicateEmailsAllowed=false -s ssoSessionIdleTimeout=604800 -s ssoSessionMaxLifespan=2592000 \
  -s ssoSessionIdleTimeoutRememberMe=2592000 -s ssoSessionMaxLifespanRememberMe=7776000 \
  -s "smtpServer.host=$SH" -s "smtpServer.port=$SP" -s "smtpServer.from=$SF" -s "smtpServer.fromDisplayName=Porterchain" \
  -s "smtpServer.auth=$AUTH" -s "smtpServer.user=$SU" -s "smtpServer.password=$SPW" -s "smtpServer.starttls=$AUTH"
# first broker login: link to an existing account with the same VERIFIED email, else create (no review screen)
if ! $K get authentication/flows -r $R --fields alias | grep -q '"pc-first-broker-login"'; then
  $K create authentication/flows -r $R -s alias=pc-first-broker-login -s providerId=basic-flow -s topLevel=true -s builtIn=false -s description="Auto-link by verified email" >/dev/null
  $K create authentication/flows/pc-first-broker-login/executions/flow -r $R -s alias=pc-link-or-create -s type=basic-flow -s provider=registration-page-form >/dev/null
  $K create authentication/flows/pc-link-or-create/executions/execution -r $R -s provider=idp-create-user-if-unique >/dev/null
  $K create authentication/flows/pc-link-or-create/executions/execution -r $R -s provider=idp-auto-link >/dev/null
  $K get authentication/flows/pc-first-broker-login/executions -r $R > /tmp/ex.json
  grep -o '"id" : "[^"]*"' /tmp/ex.json | cut -d'"' -f4 | while read -r id; do
    $K update authentication/flows/pc-first-broker-login/executions -r $R -b "{\"id\":\"$id\",\"requirement\":\"ALTERNATIVE\"}" >/dev/null 2>&1 || true; done
  # the subflow itself must be REQUIRED
  SID=$(grep -B3 '"displayName" : "pc-link-or-create"' /tmp/ex.json | grep -o '"id" : "[^"]*"' | head -1 | cut -d'"' -f4)
  [ -n "$SID" ] && $K update authentication/flows/pc-first-broker-login/executions -r $R -b "{\"id\":\"$SID\",\"requirement\":\"REQUIRED\"}" >/dev/null
fi
up() { local alias=$1; shift; if $K get identity-provider/instances/$alias -r $R >/dev/null 2>&1; then $K update identity-provider/instances/$alias -r $R "$@" >/dev/null; else $K create identity-provider/instances -r $R -s alias=$alias "$@" >/dev/null; fi; }
up google -s providerId=google -s displayName=Google -s enabled=$G_ON -s trustEmail=true -s firstBrokerLoginFlowAlias=pc-first-broker-login \
  -s "config.clientId=$GID" -s "config.clientSecret=$GSEC" -s "config.defaultScope=openid email profile" -s config.syncMode=IMPORT -s config.guiOrder=1
up apple -s providerId=apple -s displayName=Apple -s enabled=$A_ON -s trustEmail=true -s firstBrokerLoginFlowAlias=pc-first-broker-login \
  -s "config.clientId=$AID" -s "config.teamId=$ATEAM" -s "config.keyId=$AKEY" -s "config.p8Content=$AP8" -s "config.defaultScope=name email" -s config.syncMode=IMPORT -s config.guiOrder=2
$K get identity-provider/instances -r $R --fields alias,enabled,trustEmail,firstBrokerLoginFlowAlias
$K get authentication/flows/pc-first-broker-login/executions -r $R --fields displayName,requirement,level
IN
