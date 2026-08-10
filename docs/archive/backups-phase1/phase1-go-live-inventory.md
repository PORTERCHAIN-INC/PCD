# Phase 1 go-live inventory (NAMES + status only — no secret values)

Generated: 2026-07-28 local audit
Stripe policy: FROZEN — verify presence only, do not rotate

## Verdict

- GitHub deploy/build secrets: PRESENT (required set green via pnpm secrets:verify)
- Local Clerk SSOT `env/clerk.env`: TEST keys (pk_test/sk_test) — correct for local; NOT for prod upload
- Live Clerk vault copy: `infrastructure/deploy/scripts/clerk-keys.local.env` + restored `env/clerk.env.prod-live.bak` — all 4 apps pk_live/sk_live
- Doppler CLI: NOT LOGGED IN — remote prd name audit blocked until `doppler login`
- Branches: only `main` / `origin/main` — nothing to prune
- CI/CD workflows: KEEP all 7 (+ Dependabot) — do not delete
- Last Deploy (2026-07-14): skipped/failed after CI failure on main — fix CI before next live cutover
- Postgres backup: NOT RUN (needs droplet docker). Run when SSH ready.

## GitHub Actions secrets (names)

- DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, DOPPLER_TOKEN
- CLERK_CUSTOMER_PUBLISHABLE_KEY, CLERK_MERCHANT_PUBLISHABLE_KEY, CLERK_ADMIN_PUBLISHABLE_KEY, CLERK_DRIVER_PUBLISHABLE_KEY
- NEXT_PUBLIC_GOOGLE_MAPS_API_KEY, NEXT_PUBLIC_GA_MEASUREMENT_ID, NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE
- PCD (legacy/odd — review later)
- Optional gaps: SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN

## GitHub variables

- DOPPLER_PROJECT=pcd, DOPPLER_CONFIG=prd
- NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED, PORTERCHAIN_PUSH_ENABLED, PORTERCHAIN_PUSH_SEND

## Doppler expected names (from SECRETS_MAP — confirm after doppler login)

- POSTGRES_PASSWORD, JWT_SECRET
- CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_{SECRET_KEY,PUBLISHABLE_KEY,JWKS_URL} (12)
- STRIPE_SECRET, STRIPE_WEBHOOK_SECRET (VERIFY ONLY — frozen)
- PUBLIC_INGEST_API_KEY, GOOGLE_MAPS_SERVER_API_KEY
- MAIL_*, PORTERCHAIN_OPS_EMAILS
- FIREBASE__, PORTERCHAIN_PUSH__
- Optional: SENTRY_DSN, FLEETBASE_*

## Local apps/api/.env (names + safe prefix)

- STRIPE_SECRET=sk_live (present — do not change)
- STRIPE_WEBHOOK_SECRET=whsec (present — do not change)
- All CLERK_* = sk_test/pk_test (local)
- GROQ_API_KEY=set, MAIL__=set, FLEETBASE__=set, REDIS/DATABASE=set

## Workflows (preserve)

- ci.yml, deploy.yml, deploy-website.yml, set-public-ingest-key.yml
- security.yml, codeql.yml, nightly-e2e.yml

## Clean decisions (Phase 1C)

- NO branch deletes (only main)
- NO workflow deletes
- NO Doppler Stripe changes
- NO volume wipe
- WIP: large uncommitted Capacity Agent / website / worker set on main — land before Deploy

## Phase 1B — Backup commands (run on droplet or via SSH)

```bash
# On droplet (preferred):
cd /opt/porterchain && bash /path/to/backup-porterchain-postgres.sh
# Or from laptop with compose context pointed at prod (if docker context set):
COMPOSE_FILE=infrastructure/deploy/docker-compose.prod.yml \
  bash infrastructure/deploy/scripts/backup-porterchain-postgres.sh
```

Default recommendation: **app-tier refresh** (Redeploy workflow), not new droplet, unless host is compromised.

## Next (blocked / manual)

1. `doppler login` then `doppler secrets --only-names -p pcd -c prd`
2. Confirm Stripe keys in Doppler match Dashboard (names/presence) — no rotation
3. Before go-live: upload LIVE clerk from clerk.env.prod-live.bak via upload scripts (not test clerk.env)
4. SSH backup postgres
5. Fix CI green on main, then Deploy

## Phase 2 results (2026-07-28)

### Prod gates

- secrets:verify: PASS (optional Sentry + Doppler login gaps)
- docker-compose.prod.yml: CLERK_DEV_BYPASS=false on api+worker; APP_ENV=production
- reject_dev_jwt_secret_in_production: present in Settings
- Local CLERK_DEV_BYPASS=true expected for local only

### Portal intent matrix (code)

- merchant → https://merchant.porterchain.com/sign-in
- driver → https://driver.porterchain.com/login
- admin|staff → https://admin.porterchain.com/sign-in
- default/customer → stay on website /login (customer Clerk)
- Post-auth website: /v1/auth/me must be customer user_type → customer.porterchain.com/dashboard; else wrong_portal

### Portal after-sign-in (monorepo-env defaults)

- customer → /dashboard
- merchant → /onboarding
- admin → /dashboard
- driver → /login + app JWT (distinct)

### Live HTTP smoke (202)

- porterchain.com/en/login 200
- porterchain.com/en/login?intent=merchant 200 (client-side redirect)
- customer/merchant/admin sign-in + driver /login all 200

### Gaps / notes

- Website Docker build does not pass NEXT_PUBLIC_*_PORTAL_URL; production defaults in website/src/lib/env.ts apply (correct hosts). Recommend adding explicit build-args in Phase 3 for fail-proofness.
- Full interactive Clerk login (password) not automated here — requires live keys + human QA in Phase 3.
- website tsc: clean (noEmit)

## Phase 3 results (2026-07-28)

### Live droplet (SSH via ~/.ssh/pcd_deploy → api.porterchain.com A = 68.183.103.49)

- Hostname: ubuntu-s-1vcpu-2gb-nyc1
- Containers Up 13 days / 2 weeks: caddy, website, api-1/2 (healthy), worker, admin, customer, driver, merchant, postgres, redis, valhalla
- /opt/porterchain/.env key NAMES present: CLERK__×12, STRIPE__, JWT_SECRET, POSTGRES_PASSWORD, FIREBASE__, FLEETBASE__, DOPPLER_*, etc.
- CLERK_DEV_BYPASS not in .env name list (good — compose forces false)

### Postgres backup

- Local: backups/porterchain-prod-2026-07-28-125205.sql.gz (~32KB compressed)
- Source: docker exec pcd-postgres pg_dump -U porterchain -d porterchain (PG 16.10)

### Smoke

- validate:p0:prod → 7 pass, 2 warn, 0 fail
- validate:d3:prod → PASS
- /health/ready → status ok, clerk_mode=enterprise, clerk_apps all ok, stripe configured, fleetbase bridge_disabled, worker heartbeat present

### CI/CD diagnosis

- Jul 13–14 failures + Dispatch 30380256446 (2026-07-28): NOT code — GitHub Actions annotation:
  "account payments have failed or your spending limit needs to be increased"
- Jobs exit in ~3–5s without starting runners
- Unblock: GitHub org/user Settings → Billing & plans
- After billing: land WIP on main → green CI → Deploy (or workflow_dispatch)

### Still open

1. GitHub Actions billing / spending limit (BLOCKS Redeploy)
2. doppler login → prd names audit
3. Human portal password login QA (live Clerk)
4. Commit/push Capacity Guide + related WIP before trusting auto-deploy

## Phase 3 resume (2026-07-28 ~13:20)

- Aborted inventory append: already completed earlier (Phase 3 section present)
- Redeploy recheck: workflow_dispatch 30382504592 — still billing/spend-limit blocked
- Droplet: all containers still Up 13d–2w
- validate:d3:prod: PASS again
- Doppler: local + droplet CLI both need token (`doppler login` on laptop); no DOPPLER_TOKEN in droplet .env
