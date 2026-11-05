#!/usr/bin/env bash
# Read-only prod smoke for sign-in: each portal's /auth/login must redirect to Keycloak with its own
# client_id, and Keycloak must render the one shared PorterChain "Sign in" page (no portal names).
# NEVER rolls back or restores anything: on failure it prints what failed and exits 1.
set -uo pipefail
KC=${KC:-https://auth.porterchain.com}
fail=0
check() { # host client_id
  local host=$1 cid=$2 loc page
  if [ "${KC_ONLY:-0}" = 1 ]; then  # theme only, bypass the portal (e.g. before the portal images are deployed)
    loc="$KC/realms/porterchain/protocol/openid-connect/auth?client_id=$cid&response_type=code&scope=openid&code_challenge_method=S256&code_challenge=smoke0000000000000000000000000000000000000000&redirect_uri=https%3A%2F%2F$host%2Fauth%2Fcallback"
  else
    loc=$(curl -s -o /dev/null -w '%{redirect_url}' "https://$host/auth/login")
  fi
  case "$loc" in "$KC"/realms/porterchain/protocol/openid-connect/auth*"client_id=$cid"*) ;;
    *) echo "FAIL $host: /auth/login redirect='$loc' (want client_id=$cid)"; fail=1; return;; esac
  page=$(curl -s "$loc")
  for want in 'class="pc-wordmark"' 'data-k="pcSignInTitle"' 'porterchain.css'; do
    grep -q "$want" <<<"$page" || { echo "FAIL $host: themed page missing $want"; fail=1; return; }
  done
  # visible text only (Keycloak's own URLs carry client_id=pc-<portal>)
  if sed 's/<[^>]*>//g' <<<"$page" | grep -v 'client_id=' | grep -qiE '\b(admin|merchant|customer|driver|staff|partner)\b'; then
    echo "FAIL $host: sign-in page names a portal"; fail=1; return
  fi
  echo "ok   $host -> $cid (shared sign-in)"
}
check admin.porterchain.com    pc-admin
check merchant.porterchain.com pc-merchant-portal
check driver.porterchain.com   pc-driver-portal
check customer.porterchain.com pc-customer-portal
[ $fail = 0 ] && echo "LOGIN SMOKE PASSED" || { echo "LOGIN SMOKE FAILED (no rollback performed)"; exit 1; }
