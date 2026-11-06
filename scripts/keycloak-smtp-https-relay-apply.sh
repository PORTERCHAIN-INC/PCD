#!/usr/bin/env bash
# Point realm porterchain SMTP at pcd-kc-mail-relay (ZeptoMail HTTPS sidecar).
# Never recreates Keycloak. Never prints secrets.
set -euo pipefail
C=${KC_CONTAINER:-pcd-keycloak}
REALM=${KC_REALM:-porterchain}
SF=${KC_SMTP_FROM:-no-reply@porterchain.com}
SH=${KC_SMTP_HOST:-pcd-kc-mail-relay}
SP=${KC_SMTP_PORT:-1025}
docker exec "$C" sh -c 'true' >/dev/null
docker exec -e R="$REALM" -e SH="$SH" -e SP="$SP" -e SF="$SF" "$C" bash -s <<'IN'
set -e
K=/opt/keycloak/bin/kcadm.sh
$K config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
$K update realms/$R -s emailTheme=porterchain \
  -s "smtpServer.host=$SH" -s "smtpServer.port=$SP" -s "smtpServer.from=$SF" \
  -s "smtpServer.fromDisplayName=Porterchain" \
  -s "smtpServer.auth=false" -s "smtpServer.user=" -s "smtpServer.password=" \
  -s "smtpServer.starttls=false" -s "smtpServer.ssl=false"
$K get realms/$R --fields smtpServer,emailTheme | sed -E 's/"password"[[:space:]]*:[[:space:]]*"[^"]*"/"password":"***"/g'
IN
echo "realm $REALM SMTP → $SH:$SP (ZeptoMail HTTPS relay)"
