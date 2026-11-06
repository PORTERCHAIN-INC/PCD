#!/usr/bin/env bash
# New-device email code (step-up) on an EXISTING Keycloak realm via kcadm. Never recreates Keycloak.
# Needs the free OSS extension email-otp-authenticator (for-keycloak, Unlicense) in /opt/keycloak/providers/
#   (infrastructure/keycloak/providers/email-otp-authenticator-v1.8.1-kc-26.8.1.jar, sha256 checked by local-stack.sh).
# What it does (idempotent):
#   pc-forms -> new CONDITIONAL subflow "pc-new-device-code":
#     Condition - user role  mfa_required, NEGATED  (staff/admin skip it; they keep TOTP in pc-staff-otp)
#     Email OTP form          device trust ON (cookie per user+realm, 180 days), IP trust OFF, 6 digits, 10 min,
#                             60 s resend cooldown, max 5 codes / 15 min
#   => code only on a browser without a valid trust cookie; never on every login.
#   realm emailTheme=porterchain (branded EN/FR code email) + SMTP:
#     KC_MAIL_PROVIDER=mailpit (default, local)
#       | zeptomail (smtp.zeptomail.ca:587 — NOT for DigitalOcean Droplets)
#       | zeptomail_https (prod DO: pcd-kc-mail-relay:1025 → ZeptoMail HTTPS; see
#         docs/runbooks/KEYCLOAK_MAIL_HTTPS.md)
# Usage: KC_CONTAINER=pcd-ls-keycloak bash scripts/keycloak-email-otp-setup.sh
set -euo pipefail
C=${KC_CONTAINER:-pcd-ls-keycloak}; REALM=${KC_REALM:-porterchain}; LS_DIR=${LS_DIR:-/home/pcd/.pcd-local-stack}
set -a; . "$LS_DIR/stack.env"; set +a
case "${KC_MAIL_PROVIDER:-mailpit}" in
  mailpit)   SH=${KC_SMTP_HOST:-pcd-ls-mailpit}; SP=${KC_SMTP_PORT:-1025}; SU=""; SPW=""; TLS=false ;;
  # Direct ZeptoMail SMTP — works only where outbound 587 is open (NOT DigitalOcean Droplets).
  zeptomail) SH=${KC_SMTP_HOST:-smtp.zeptomail.ca}; SP=${KC_SMTP_PORT:-587}; SU=${KC_SMTP_USER:-emailapikey}
             SPW=${KC_SMTP_PASSWORD:?KC_SMTP_PASSWORD (ZeptoMail token) required}; TLS=true ;;
  # Prod on DigitalOcean: Keycloak → pcd-kc-mail-relay:1025 → ZeptoMail HTTPS :443.
  # Token lives in the relay env file, not in Keycloak SMTP password.
  zeptomail_https|https_relay)
             SH=${KC_SMTP_HOST:-pcd-kc-mail-relay}; SP=${KC_SMTP_PORT:-1025}; SU=""; SPW=""; TLS=false ;;
  *) echo "KC_MAIL_PROVIDER must be mailpit, zeptomail, or zeptomail_https" >&2; exit 2 ;;
esac
SF=${KC_SMTP_FROM:-no-reply@porterchain.com}
docker exec "$C" sh -c 'ls /opt/keycloak/providers/email-otp-authenticator-*.jar' >/dev/null 2>&1 || { echo "email-otp-authenticator jar missing in $C (run: bash scripts/local-stack.sh kc-ext)" >&2; exit 1; }
docker exec -i -e P="$KC_ADMIN_PASSWORD" -e R="$REALM" -e SH="$SH" -e SP="$SP" -e SU="$SU" -e SPW="$SPW" -e TLS="$TLS" -e SF="$SF" \
  "$C" bash -s <<'IN'
set -e; K=/opt/keycloak/bin/kcadm.sh
$K config credentials --server http://localhost:8080 --realm master --user admin --password "$P" >/dev/null 2>&1
AUTH=false; [ -n "$SU" ] && AUTH=true
$K update realms/$R -s emailTheme=porterchain -s "smtpServer.host=$SH" -s "smtpServer.port=$SP" -s "smtpServer.from=$SF" \
  -s "smtpServer.fromDisplayName=Porterchain" -s "smtpServer.auth=$AUTH" -s "smtpServer.user=$SU" -s "smtpServer.password=$SPW" \
  -s "smtpServer.starttls=$TLS" -s "smtpServer.ssl=false"
ex() { $K get authentication/flows/$1/executions -r $R; }
id_of() { ex "$1" | tr -d '\n' | sed -E 's/\}, *\{/}\n{/g' | grep "\"$2\" : \"$3\"" | grep -o '"id" : "[^"]*"' | head -1 | cut -d'"' -f4; }
SUB=$(id_of pc-forms displayName pc-new-device-code)
if [ -z "$SUB" ]; then
  $K create authentication/flows/pc-forms/executions/flow -r $R -s alias=pc-new-device-code -s type=basic-flow \
    -s description="Email code on a new/unrecognised browser (not staff)" >/dev/null
  SUB=$(id_of pc-forms displayName pc-new-device-code)
  $K create authentication/flows/pc-new-device-code/executions/execution -r $R -s provider=conditional-user-role >/dev/null
  $K create authentication/flows/pc-new-device-code/executions/execution -r $R -s provider=email-otp-form >/dev/null
fi
$K update authentication/flows/pc-forms/executions -r $R -b "{\"id\":\"$SUB\",\"requirement\":\"CONDITIONAL\"}" >/dev/null
COND=$(id_of pc-new-device-code providerId conditional-user-role); OTP=$(id_of pc-new-device-code providerId email-otp-form)
for i in $COND $OTP; do $K update authentication/flows/pc-new-device-code/executions -r $R -b "{\"id\":\"$i\",\"requirement\":\"REQUIRED\"}" >/dev/null; done
cfg() { # execution-id alias json-config ; replace existing config
  local old; old=$(ex pc-new-device-code | tr -d '\n' | sed -E 's/\}, *\{/}\n{/g' | grep "\"id\" : \"$1\"" | grep -o '"authenticationConfig" : "[^"]*"' | cut -d'"' -f4)
  [ -n "$old" ] && $K delete authentication/config/$old -r $R >/dev/null
  $K create authentication/executions/$1/config -r $R -b "{\"alias\":\"$2\",\"config\":$3}" >/dev/null; }
cfg "$COND" pc-not-staff '{"condUserRole":"mfa_required","negate":"true"}'
cfg "$OTP" pc-new-device-code-cfg '{"code-length":"6","code-alphabet":"0123456789","code-lifetime":"600","device-trust-enabled":"true","device-trust-duration":"180","ip-trust-enabled":"false","trust-only-when-sole":"false","resend-cooldown":"60","issuance-limit":"5","issuance-limit-window":"900"}'
$K get authentication/flows/pc-browser/executions -r $R --fields displayName,requirement,level
IN
