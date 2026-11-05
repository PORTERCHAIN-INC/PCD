#!/usr/bin/env bash
# Complete ISOLATED local stack on this Ubuntu box (plain http, LAN reachable). Never the live stack:
# own containers (pcd-ls-*), own network, own volumes, own ports. Live 5432/6379/50051, pch-keycloak,
# porterchain-*/pch-infra-* containers are never touched.
#   bash scripts/local-stack.sh up      # build nothing; run images pcd-*:lan (see /tmp/lsbuild.sh), migrate, seed
#   bash scripts/local-stack.sh status
#   bash scripts/local-stack.sh down    # remove containers + volumes (data discarded)
# Secrets/passwords: $LS_DIR (mode 700, outside the repo). Passwords are never printed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LS_DIR=${LS_DIR:-/home/pcd/.pcd-local-stack}
IP=${LS_IP:-$(hostname -I | awk '{print $1}')}
NET=pcd-ls; P=pcd-ls
PG_PORT=56432 RD_PORT=56380 SP_PORT=56051 KC_PORT=18280 S3_PORT=53910 VH_PORT=58012 VR_PORT=53010
SMTP_PORT=51026 MAILUI_PORT=58026 API_PORT=58001 MER_PORT=53001 ADM_PORT=53002 DRV_PORT=53003 CUS_PORT=53004 WEB_PORT=53005
VH_IMG=ghcr.io/valhalla/valhalla-scripted@sha256:9ba06c00f41fabec8d3cb2e7ec3c39023be7a410d245049d76af3b494e1ce674
VR_IMG=ghcr.io/vroom-project/vroom-docker:v1.14.0
TILES=${VALHALLA_TILES_SRC:-/home/pcd/pcd-local/infrastructure/docker/valhalla/data}
CONTAINERS="translate api worker admin merchant driver customer website vroom valhalla mailpit garage keycloak spicedb redis postgres"
PYP="src:../../shared/python:../../services/python:../../services/pricing-engine:../../services/event-bus:../../services/driver-platform:../../apps/worker"

down() {
  for c in $CONTAINERS; do docker rm -f "$P-$c" >/dev/null 2>&1 || true; done
  docker volume rm "$P-pg" "$P-garage" "$P-mail" >/dev/null 2>&1 || true
  # Keycloak data ($P-kc: users, TOTP, sessions) is kept unless KC_WIPE=yes is set explicitly
  [ "${KC_WIPE:-}" = yes ] && docker volume rm "$P-kc" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  echo "local stack removed (containers, volumes, network). Secrets kept in $LS_DIR"
}

secrets() {
  mkdir -p "$LS_DIR"; chmod 700 "$LS_DIR"; umask 077
  if [ ! -f "$LS_DIR/stack.env" ]; then
    r() { openssl rand -hex 24; }
    cat > "$LS_DIR/stack.env" <<EOF
PG_PASSWORD=$(r)
SPICEDB_KEY=$(r)
KC_ADMIN_PASSWORD=$(r)
KC_API_ADMIN_SECRET=$(r)
AUTH_SESSION_SECRET=$(r)$(r)
JWT_SECRET=$(r)$(r)
AUDIT_SIGNING_KEY=$(r)
EOF
  fi
  if [ ! -f "$LS_DIR/demo-logins.env" ]; then
    pw() { echo "Ls-$(openssl rand -hex 8)-Aa9!"; }
    cat > "$LS_DIR/demo-logins.env" <<EOF
# Local test-stack logins only (Keycloak on http://$IP:$KC_PORT). Never real accounts.
ADMIN_EMAIL=admin@porterchain.com
ADMIN_PASSWORD=$(pw)
MERCHANT_EMAIL=merchant@porterchain.com
MERCHANT_PASSWORD=$(pw)
DRIVER_EMAIL=marco@porterchain.com
DRIVER_PASSWORD=$(pw)
CUSTOMER_EMAIL=customer@porterchain.com
CUSTOMER_PASSWORD=$(pw)
REVIEWER_CUSTOMER_EMAIL=reviewer.customer@local.test
REVIEWER_CUSTOMER_PASSWORD=$(pw)
REVIEWER_DRIVER_EMAIL=reviewer.driver@local.test
REVIEWER_DRIVER_PASSWORD=$(pw)
EOF
  fi
  set -a; . "$LS_DIR/stack.env"; . "$LS_DIR/demo-logins.env"; set +a
}

# Free OSS new-device email code extension (github.com/for-keycloak/email-otp-authenticator, Unlicense)
EOTP_JAR=email-otp-authenticator-v1.8.1-kc-26.8.1.jar
EOTP_SHA256=8013758fe4f24dfb561d57f83c0853387fb18c9b35925c77fb60ccd9af7cedea
eotp_jar_ok() { echo "$EOTP_SHA256  $ROOT/infrastructure/keycloak/providers/$EOTP_JAR" | sha256sum -c --status; }

# Add provider jars to the EXISTING Keycloak container (no recreate: users, TOTP, realm stay in its H2 data),
# restart it only if something new was copied, then apply the new-device email code flow.
kc_ext() {
  secrets
  eotp_jar_ok || { echo "bad/missing $EOTP_JAR (sha256 mismatch)" >&2; exit 1; }
  local c="$P-keycloak" changed=0
  docker inspect "$c" >/dev/null 2>&1 || { echo "$c not running; use: $0 up" >&2; exit 1; }
  if ! docker exec "$c" test -f "/opt/keycloak/providers/$EOTP_JAR"; then
    docker cp "$ROOT/infrastructure/keycloak/providers/$EOTP_JAR" "$c:/opt/keycloak/providers/$EOTP_JAR"; changed=1
  fi
  # theme (login + branded email): containers created before the theme mount get a fresh copy (dev mode picks it up, no restart)
  if ! docker inspect "$c" --format '{{range .Mounts}}{{.Destination}} {{end}}' | grep -q /opt/keycloak/themes/porterchain; then
    docker cp "$ROOT/infrastructure/keycloak/themes/porterchain/." "$c:/opt/keycloak/themes/porterchain/"
  fi
  if [ $changed = 1 ]; then docker restart "$c" >/dev/null; sleep 5; fi
  wait_http "http://127.0.0.1:$KC_PORT/realms/porterchain/.well-known/openid-configuration" keycloak 120
  LS_DIR="$LS_DIR" KC_CONTAINER="$c" bash "$ROOT/scripts/keycloak-email-otp-setup.sh"
}

# Keycloak dev H2 DB lives in named volume $P-kc (/opt/keycloak/data/h2) so recreates keep users + TOTP.
# --import-realm only imports when the realm does not exist yet (Keycloak skips existing realms).
kc_run() {
  docker volume inspect "$P-kc" >/dev/null 2>&1 || { docker volume create "$P-kc" >/dev/null
    docker run --rm -u 0 -v "$P-kc:/h2" alpine:3 chown 1000:0 /h2 >/dev/null; }
  run keycloak -p 0.0.0.0:$KC_PORT:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD="$KC_ADMIN_PASSWORD" \
    -e KC_HOSTNAME="http://$IP:$KC_PORT" -e KC_HTTP_ENABLED=true -v "$P-kc:/opt/keycloak/data/h2" \
    -v "$LS_DIR/kc:/opt/keycloak/data/import:ro" -v "$ROOT/infrastructure/keycloak/themes/porterchain:/opt/keycloak/themes/porterchain:ro" -v "$ROOT/infrastructure/keycloak/providers/apple-identity-provider-1.17.0.jar:/opt/keycloak/providers/apple-identity-provider-1.17.0.jar:ro" -v "$ROOT/infrastructure/keycloak/providers/$EOTP_JAR:/opt/keycloak/providers/$EOTP_JAR:ro" quay.io/keycloak/keycloak:26.8.1 start-dev --import-realm --features=token-exchange,admin-fine-grained-authz:v1
}
kc_recreate() {
  secrets; eotp_jar_ok || { echo "bad/missing $EOTP_JAR" >&2; exit 1; }
  [ -f "$LS_DIR/kc/porterchain-realm.json" ] || { echo "missing realm import; run up once" >&2; exit 1; }
  run() { local n=$1; shift; docker rm -f "$P-$n" >/dev/null 2>&1 || true; docker run -d --name "$P-$n" --network "$NET" --restart unless-stopped "$@" >/dev/null; }
  kc_run
  wait_http "http://127.0.0.1:$KC_PORT/realms/porterchain/.well-known/openid-configuration" keycloak 120
  echo "pcd-ls-keycloak recreated (data kept in volume $P-kc)"
}

wait_http() { for _ in $(seq 1 "${3:-90}"); do curl -fsS -o /dev/null "$1" 2>/dev/null && return 0; sleep 2; done; echo "timeout: $2" >&2; return 1; }

up() {
  secrets
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  run() { local n=$1; shift; docker rm -f "$P-$n" >/dev/null 2>&1 || true; docker run -d --name "$P-$n" --network "$NET" --restart unless-stopped "$@" >/dev/null; }

  if [ -z "${APPS_ONLY:-}" ]; then eotp_jar_ok || { echo "bad/missing $EOTP_JAR" >&2; exit 1; }; fi
  if [ -z "${APPS_ONLY:-}" ]; then  # `apps` skips the data plane + Keycloak (keeps admin TOTP)
  # --- data plane
  run postgres -p 127.0.0.1:$PG_PORT:5432 -v $P-pg:/var/lib/postgresql/data \
    -e POSTGRES_USER=porterchain -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB=porterchain postgis/postgis:16-3.4
  run redis -p 127.0.0.1:$RD_PORT:6379 redis:7-alpine
  run spicedb -p 127.0.0.1:$SP_PORT:50051 authzed/spicedb:v1.56.0 serve --grpc-preshared-key "$SPICEDB_KEY" --datastore-engine memory
  # Self-hosted LibreTranslate (merchant/customer free text -> English for admin). Model volume kept on `down`.
  run translate -p 127.0.0.1:58090:5000 -v $P-lt:/home/libretranslate/.local -e LT_LOAD_ONLY=en,fr libretranslate/libretranslate:latest
  run mailpit -p 127.0.0.1:$SMTP_PORT:1025 -p 0.0.0.0:$MAILUI_PORT:8025 -v $P-mail:/data -e MP_DATABASE=/data/mailpit.db axllent/mailpit:v1.30.3

  # --- Garage (S3 for POD photos/signatures)
  mkdir -p "$LS_DIR/garage"
  [ -f "$LS_DIR/garage/garage.toml" ] || cat > "$LS_DIR/garage/garage.toml" <<TOML
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "sqlite"
replication_factor = 1
rpc_bind_addr = "[::]:3901"
rpc_public_addr = "127.0.0.1:3901"
rpc_secret = "$(openssl rand -hex 32)"
[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:3900"
root_domain = ".s3.garage.localhost"
TOML
  chmod 644 "$LS_DIR/garage/garage.toml"; chmod 755 "$LS_DIR/garage"; chmod 711 "$LS_DIR"
  run garage -p 127.0.0.1:$S3_PORT:3900 -v "$LS_DIR/garage/garage.toml:/etc/garage.toml:ro" -v $P-garage:/var/lib/garage dxflrs/garage:v2.5.0
  G="docker exec $P-garage /garage"
  for _ in $(seq 1 30); do $G status >/dev/null 2>&1 && break; sleep 1; done
  if ! $G bucket info pod-local >/dev/null 2>&1; then
    NODE=$($G node id -q | cut -d@ -f1)
    $G layout assign -z dc1 -c 2G "$NODE" >/dev/null; $G layout apply --version 1 >/dev/null
    $G bucket create pod-local >/dev/null
    OUT=$($G key create pod-local-key)
    KID=$(echo "$OUT" | awk '/Key ID/ {print $NF}'); SEC=$(echo "$OUT" | awk '/Secret key/ {print $NF}')
    $G bucket allow --read --write pod-local --key pod-local-key >/dev/null
    umask 077; printf 'POD_S3_ACCESS_KEY_ID=%s\nPOD_S3_SECRET_ACCESS_KEY=%s\n' "$KID" "$SEC" > "$LS_DIR/garage.env"
  fi
  set -a; . "$LS_DIR/garage.env"; set +a

  # --- Valhalla + VROOM (tiles COPIED, read-only)
  mkdir -p "$LS_DIR/valhalla" "$LS_DIR/vroom"; chmod 755 "$LS_DIR/valhalla" "$LS_DIR/vroom"
  [ -f "$LS_DIR/valhalla/valhalla_tiles.tar" ] || cp "$TILES/valhalla_tiles.tar" "$LS_DIR/valhalla/"
  cp "$ROOT/infrastructure/docker/valhalla/valhalla.gta-ram.json" "$LS_DIR/valhalla/valhalla.json"
  python3 - "$TILES/valhalla.json" "$LS_DIR/valhalla/valhalla.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
for k in ("auto", "truck"):
    c["service_limits"][k]["max_matrix_location_pairs"] = 40000
json.dump(c, open(sys.argv[2], "w"), indent=1)
PY
  chmod 644 "$LS_DIR/valhalla/"*
  run valhalla -p 0.0.0.0:$VH_PORT:8002 -v "$LS_DIR/valhalla:/custom_files:ro" --entrypoint valhalla_service "$VH_IMG" /custom_files/valhalla.json 2
  docker run --rm --entrypoint cat "$VR_IMG" /vroom-express/config.yml | python3 -c "
import sys; s=sys.stdin.read().replace(\"router: 'osrm'\", \"router: 'valhalla'\"); i=s.index('  valhalla:')
print(s[:i]+'  valhalla:\n'+''.join(f\"    {p}:\n      host: '$P-valhalla'\n      port: '8002'\n\" for p in ('auto','truck')))" > "$LS_DIR/vroom/config.yml"
  chmod 644 "$LS_DIR/vroom/config.yml"
  run vroom -p 127.0.0.1:$VR_PORT:3000 -v "$LS_DIR/vroom:/conf" -e VROOM_ROUTER=valhalla "$VR_IMG"

  # --- Keycloak (realm imported, http on LAN; issuer fixed to http://$IP:$KC_PORT)
  mkdir -p "$LS_DIR/kc"; chmod 755 "$LS_DIR/kc"
  GOOGLE_IDP_ENABLED=false APPLE_IDP_ENABLED=false GOOGLE_CLIENT_ID=x GOOGLE_CLIENT_SECRET=x \
    KEYCLOAK_ADMIN_CLIENT_SECRET="$KC_API_ADMIN_SECRET" ALLOW_PLACEHOLDERS=true \
    bash "$ROOT/infrastructure/keycloak/render-realm.sh" "$LS_DIR/kc/porterchain-realm.json" >/dev/null
  python3 - "$LS_DIR/kc/porterchain-realm.json" "$IP" <<PY
import json, sys
p, ip = sys.argv[1], sys.argv[2]
r = json.load(open(p))
ports = {"pc-merchant-portal": $MER_PORT, "pc-admin": $ADM_PORT, "pc-driver-portal": $DRV_PORT, "pc-customer-portal": $CUS_PORT, "pc-website": $WEB_PORT}
for c in r["clients"]:
    if c["clientId"] in ports:
        o = [f"http://{h}:{ports[c['clientId']]}" for h in ("localhost", "127.0.0.1", ip)]
        c["redirectUris"] = list(c.get("redirectUris") or []) + [x + "/auth/callback" for x in o] + [x + "/*" for x in o]
        c["webOrigins"] = list(c.get("webOrigins") or []) + o
        c.setdefault("attributes", {})["post.logout.redirect.uris"] = "+"
r["sslRequired"] = "none"   # plain-http LAN test stack only
json.dump(r, open(p, "w"))
PY
  chmod 644 "$LS_DIR/kc/porterchain-realm.json"
  # PorterChain login theme (same look as the former Clerk sign-in) + EN/FR
  python3 - "$LS_DIR/kc/porterchain-realm.json" <<'PY2'
import json,sys
p=sys.argv[1];r=json.load(open(p))
r.update(loginTheme="porterchain",internationalizationEnabled=True,supportedLocales=["en","fr"],defaultLocale="en")
json.dump(r,open(p,"w"),indent=1)
PY2
  kc_run

  fi
  set -a; . "$LS_DIR/garage.env"; set +a
  # --- migrate + seed (host venv, against OUR postgres only)
  for _ in $(seq 1 60); do docker exec $P-postgres pg_isready -U porterchain -d porterchain >/dev/null 2>&1 && break; sleep 1; done
  sleep 2
  DBURL="postgresql+psycopg://porterchain:${PG_PASSWORD}@127.0.0.1:${PG_PORT}/porterchain"
  ( cd "$ROOT/apps/api" && DATABASE_URL="$DBURL" PYTHONPATH="$PYP" .venv/bin/alembic upgrade head >/dev/null )
  if [ ! -f "$LS_DIR/.seeded" ]; then
    ( cd "$ROOT/apps/api" && export DATABASE_URL="$DBURL" PYTHONPATH="$PYP" PCD_SEED_ALLOWED_PORTS=$PG_PORT APP_ENV=local
      .venv/bin/python "$ROOT/scripts/local_stack_seed.py" db
      .venv/bin/python scripts/reset_local_personas.py >"$LS_DIR/seed.log" 2>&1
      .venv/bin/python scripts/seed_pcdc_demo.py >>"$LS_DIR/seed.log" 2>&1 )
    touch "$LS_DIR/.seeded"
  fi
  wait_http "http://127.0.0.1:$KC_PORT/realms/porterchain/.well-known/openid-configuration" keycloak 120
  [ -n "${APPS_ONLY:-}" ] || LS_DIR="$LS_DIR" KC_CONTAINER="$P-keycloak" bash "$ROOT/scripts/keycloak-email-otp-setup.sh" >/dev/null
  [ -n "${APPS_ONLY:-}" ] || ( export KEYCLOAK_URL="http://127.0.0.1:$KC_PORT" KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD="$KC_ADMIN_PASSWORD"
    python3 "$ROOT/infrastructure/keycloak/seed_reviewers.py" >/dev/null
    python3 "$ROOT/scripts/local_stack_seed.py" keycloak )

  # --- app plane
  H="http://$IP"
  CORS="$(for p in $MER_PORT $ADM_PORT $DRV_PORT $CUS_PORT $WEB_PORT; do printf 'http://localhost:%s,http://127.0.0.1:%s,%s:%s,' $p $p $H $p; done)"
  APIENV=(-e APP_ENV=local -e APP_DEBUG=false -e AUTH_DEV_BYPASS=false -e IDP_DEV_BYPASS=false
    -e DATABASE_URL="postgresql+psycopg://porterchain:${PG_PASSWORD}@$P-postgres:5432/porterchain" -e REDIS_URL=redis://$P-redis:6379/0
    -e SPICEDB_ENABLED=true -e SPICEDB_REQUIRED=false -e SPICEDB_ENDPOINT=$P-spicedb:50051 -e SPICEDB_PRESHARED_KEY="$SPICEDB_KEY"
    -e KEYCLOAK_URL="$H:$KC_PORT" -e KEYCLOAK_INTERNAL_URL=http://$P-keycloak:8080 -e KEYCLOAK_REALM=porterchain
    -e KEYCLOAK_ADMIN_CLIENT_SECRET="$KC_API_ADMIN_SECRET" -e JWT_SECRET="$JWT_SECRET" -e AUDIT_SIGNING_KEY="$AUDIT_SIGNING_KEY"
    -e STRIPE_MOCK=true -e STRIPE_SECRET= -e CORS_ORIGINS="${CORS%,}"
    -e PORTERCHAIN_API_URL="$H:$API_PORT" -e WEBSITE_URL="$H:$WEB_PORT" -e ADMIN_PORTAL_URL="$H:$ADM_PORT"
    -e MERCHANT_PORTAL_URL="$H:$MER_PORT" -e DRIVER_PORTAL_URL="$H:$DRV_PORT" -e DRIVER_PORTAL_BASE_URL="$H:$DRV_PORT" -e CUSTOMER_PORTAL_URL="$H:$CUS_PORT"
    -e PORTERCHAIN_TRACKING_URL="$H:$CUS_PORT/track/"
    -e MAIL_TRANSPORT=smtp -e MAIL_HOST=$P-mailpit -e MAIL_PORT=1025 -e MAIL_USERNAME= -e MAIL_PASSWORD= -e MAIL_FROM_ADDRESS=noreply@local.test
    -e ROUTING_ENGINE=valhalla -e VALHALLA_BASE_URL=http://$P-valhalla:8002 -e VROOM_URL=http://$P-vroom:3000 -e OSRM_HOST=
    -e POD_S3_ENDPOINT=http://$P-garage:3900 -e POD_S3_BUCKET=pod-local -e POD_S3_REGION=garage
    -e POD_S3_ACCESS_KEY_ID="$POD_S3_ACCESS_KEY_ID" -e POD_S3_SECRET_ACCESS_KEY="$POD_S3_SECRET_ACCESS_KEY"
    -e PORTERCHAIN_PUSH_ENABLED=false -e FEATURE_AI=false -e SHOPIFY_FULFILLMENT_SERVICE_ENABLED=false
    -e PCD_TRANSLATE_URL=http://$P-translate:5000
    -e REVIEWER_ACCOUNTS_ENABLED=true -e REVIEWER_DRIVER_EMAILS="$REVIEWER_DRIVER_EMAIL")
  # Stripe TEST mode (optional): keys only from $LS_DIR/stripe.env (sk_test_/pk_test_, never echoed);
  # the webhook signing secret from `stripe listen` goes in $LS_DIR/stripe-webhook.env. Live keys are refused.
  if [ -f "$LS_DIR/stripe.env" ]; then
    STRIPE_SECRET_KEY=; STRIPE_PUBLISHABLE_KEY=; STRIPE_WEBHOOK_SECRET=
    . "$LS_DIR/stripe.env"; [ -f "$LS_DIR/stripe-webhook.env" ] && . "$LS_DIR/stripe-webhook.env"
    case "$STRIPE_SECRET_KEY" in
      sk_test_*) APIENV+=(-e STRIPE_MOCK=false -e MERCHANT_CARD_PAYMENTS_ENABLED=true -e STRIPE_SECRET="$STRIPE_SECRET_KEY" -e STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET") ;;
      "") ;;
      *) echo "stripe.env: only sk_test_ keys are allowed on the local stack; keeping Stripe mock" >&2 ;;
    esac
  fi
  # Shopify dev app (optional): values come only from $LS_DIR/shopify.env and are never echoed.
  if [ -f "$LS_DIR/shopify.env" ]; then
    SHOPIFY_CLIENT_ID=; SHOPIFY_CLIENT_SECRET=; SHOPIFY_SHOP_DOMAIN=
    . "$LS_DIR/shopify.env"
    [ -n "$SHOPIFY_CLIENT_ID" ] && APIENV+=(-e SHOPIFY_API_KEY="$SHOPIFY_CLIENT_ID" -e SHOPIFY_API_SECRET="$SHOPIFY_CLIENT_SECRET")
  fi
  run api -p 0.0.0.0:$API_PORT:8001 "${APIENV[@]}" pcd-api:lan
  run worker -w /app/apps/worker "${APIENV[@]}" -e LATE_PENALTY_INTERVAL_SECONDS="${LATE_PENALTY_INTERVAL_SECONDS:-60}" pcd-api:lan python run.py
  web() { local n=$1 img=$2 port=$3 inner=$4 client=$5 pl=1; [ "$n" = admin ] && pl=0
    run "$n" -e OIDC_PROMPT_LOGIN=$pl -e AUTH_COOKIE_NAME=pc_session_$n -p 0.0.0.0:$port:$inner -e KEYCLOAK_URL="$H:$KC_PORT" -e KEYCLOAK_INTERNAL_URL=http://$P-keycloak:8080 \
      -e KEYCLOAK_REALM=porterchain -e KEYCLOAK_CLIENT_ID="$client" -e NEXT_PUBLIC_KEYCLOAK_CLIENT_ID="$client" \
      -e AUTH_SESSION_SECRET="$AUTH_SESSION_SECRET" -e APP_URL="$H:$port" -e AUTH_COOKIE_SECURE=false \
      -e PC_PORTAL_URL_ADMIN="$H:$ADM_PORT" -e PC_PORTAL_URL_MERCHANT="$H:$MER_PORT" -e PC_PORTAL_URL_DRIVER="$H:$DRV_PORT" -e PC_PORTAL_URL_CUSTOMER="$H:$CUS_PORT" -e PC_SITE_SIGN_IN_URL="$H:$WEB_PORT/login" \
      -e PORTERCHAIN_API_URL="http://$P-api:8001" -e PORTERCHAIN_API_INTERNAL_URL="http://$P-api:8001" "$img"; }
  web admin pcd-admin:lan $ADM_PORT 3002 pc-admin
  web merchant pcd-merchant-portal:lan $MER_PORT 3001 pc-merchant-portal
  web driver pcd-driver-portal:lan $DRV_PORT 3003 pc-driver-portal
  web customer pcd-customer:lan $CUS_PORT 3004 pc-customer-portal
  web website pcd-website:lan $WEB_PORT 3000 pc-website
  wait_http "http://127.0.0.1:$API_PORT/health" api 90
  status
}

status() {
  H="http://${IP}"
  cat <<EOF
PorterChain LOCAL STACK (isolated) — LAN $H, also http://localhost
  API        $H:$API_PORT  (health: /health, docs: /docs)
  Admin      $H:$ADM_PORT
  Merchant   $H:$MER_PORT
  Driver     $H:$DRV_PORT
  Customer   $H:$CUS_PORT
  Website    $H:$WEB_PORT  (marketing site)
  Keycloak   $H:$KC_PORT  (realm porterchain)
  Mailpit    $H:$MAILUI_PORT  (all email lands here)
  Valhalla   $H:$VH_PORT   VROOM 127.0.0.1:$VR_PORT   Garage S3 127.0.0.1:$S3_PORT
  Postgres 127.0.0.1:$PG_PORT  Redis 127.0.0.1:$RD_PORT  SpiceDB 127.0.0.1:$SP_PORT
  Logins: usernames + passwords in $LS_DIR/demo-logins.env
EOF
  docker ps --filter "name=^$P-" --format '  {{.Names}}\t{{.Status}}'
}

case "${1:-}" in
  up) up ;;
  apps) APPS_ONLY=1 up ;;  # recreate api/worker/web containers only
  down) down ;;
  status) status ;;
  kc-ext) kc_ext ;;  # add Keycloak extensions + new-device email code to the running Keycloak (no recreate)
  kc-recreate) kc_recreate ;;  # recreate ONLY pcd-ls-keycloak, reusing its persistent data volume
  *) echo "usage: $0 up|apps|kc-ext|kc-recreate|status|down   (no default; pick one)" >&2; exit 2 ;;
esac
