# Porterchain Operations Runbook

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Day-2 procedures for the Porterchain monorepo and the self-hosted Fleetbase stack.

---

## Porterchain platform — daily checks

```bash
pnpm docker:up              # PostgreSQL :5432, Redis :6379, Mailpit :8025
pnpm db:migrate             # Alembic at head
pnpm dev:api                # API :8001
pnpm dev:worker             # Event bus + queues
pnpm ports                  # Port conflict check
```

Confirm:

- API health: `curl http://localhost:8001/health`
- PostgreSQL reachable on `127.0.0.1:5432`
- Redis reachable on `127.0.0.1:6379`
- Worker consuming queues (no error spam in logs)

Frontends (host, hot reload): `pnpm dev:website` (:3000), `pnpm dev:merchant` (:3001), `pnpm dev:admin` (:3002), `pnpm dev:driver` (:3003), `pnpm dev:customer` (:3004).

Production deploy: see [infrastructure/deploy/README.md](./infrastructure/deploy/README.md).

---

## Load testing (DD-17)

Published API latency SLOs (local/staging baseline; tune after first prod run):

| Endpoint                | p95 target | k6 script                |
| ----------------------- | ---------- | ------------------------ |
| `GET /health`           | < 200 ms   | `tests/load/booking.js`  |
| `POST /v1/quotes`       | < 3 s      | `tests/load/booking.js`  |
| `POST /webhooks/stripe` | < 1 s      | `tests/load/webhooks.js` |

```bash
brew install k6
pnpm docker:up && pnpm db:migrate
pnpm dev:api   # separate terminal

pnpm load:booking
STRIPE_WEBHOOK_SECRET=whsec_... pnpm load:webhooks   # from stripe listen --print-secret
```

Details: [tests/load/README.md](./tests/load/README.md). Breached thresholds fail the run (`k6 run` exit code 99).

**Prometheus:** scrape `GET /metrics` on the API for queue depth and request counters between k6 runs.

---

## Prod webhook secrets (§0.6.3 / §0.1.8 — set at deploy)

Inbound webhooks must be signed in production. Local dev may omit secrets when bridges are disabled.

| Secret                     | Endpoint                                               | Where to set                                    | Verify                                    |
| -------------------------- | ------------------------------------------------------ | ----------------------------------------------- | ----------------------------------------- |
| `FLEETBASE_WEBHOOK_SECRET` | `POST /webhooks/fleetbase`                             | Doppler / droplet `.env`, GitHub Actions secret | `pnpm validate:p0` G3 · signed POST → 200 |
| `STRIPE_WEBHOOK_SECRET`    | `POST /webhooks/stripe`                                | Doppler · Stripe dashboard live mode            | `pnpm validate:p0:prod` G8                |
| `FIREBASE_WEBHOOK_SECRET`  | Firebase HTTP v1 device/webhook callbacks (if enabled) | Doppler · Firebase console                      | Signed POST → 200                         |

**Cutover checklist (prod):**

1. Generate Fleetbase HMAC secret; register `https://api.porterchain.com/webhooks/fleetbase` in Fleetbase console.
2. Register Stripe live webhook → `https://porterchain.com/webhooks/stripe` (Caddy → API).
3. Set all secrets in Doppler; redeploy API + worker; confirm `GET /health/ready` → `fleetbase_webhook: configured`.
4. Run `pnpm validate:p0:prod` (G3/G8).

Until prod cutover, items §0.6.3 and §0.1.8 remain open — this section is the **documented** path only.

---

## Device push test (§0.1.3)

Prod Firebase is live when `GET /health/ready` → `checks.firebase: "ok"`.

1. Sign in on physical device (driver app) — push registers automatically on dashboard load.
2. Confirm device row exists (droplet):

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U porterchain -d porterchain -c \
  "SELECT platform, left(fcm_token,20), last_seen_at FROM notification_devices WHERE user_role='driver' ORDER BY last_seen_at DESC LIMIT 5;"
```

3. Send test push:

```bash
pnpm push:test -- --email priya.sharma@porterchain.com
# on droplet:
docker compose exec -T -w /app/apps/api api python scripts/send_test_push.py --email priya.sharma@porterchain.com
```

4. Notification should appear on the device. Requires `PORTERCHAIN_PUSH_SEND=true` and APNs key in Firebase Console for iOS.

---

## Fleetbase stack — daily checks

```bash
pnpm docker:fleetbase:verify
```

Confirm:

- API http://localhost:8000 responds
- Console http://localhost:4200 loads
- Queue worker healthy (`redis` driver)
- No containers in restart loop: `docker ps --filter name=porterchain-fleetbase`

---

## Start / stop

### Start

```bash
pnpm docker:fleetbase:up
```

### Stop (preserve data)

```bash
pnpm docker:fleetbase:down
```

### Stop and wipe data (destructive)

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml down -v
```

---

## View logs

```bash
# All services
pnpm docker:fleetbase:logs

# Single service
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml logs -f application
```

| Service       | When to tail                     |
| ------------- | -------------------------------- |
| `application` | API errors, Laravel exceptions   |
| `queue`       | Failed jobs, dispatch delays     |
| `httpd`       | 502/504, nginx                   |
| `database`    | Connection issues                |
| `socket`      | WebSocket disconnects in console |

---

## Redeploy / migrations

After env changes or version upgrade:

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -T application bash -c "./deploy.sh"

docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml up -d
```

`deploy.sh` runs: `mysql:createdb`, `migrate`, `sandbox:migrate`, `fleetbase:seed`, permissions, cache clear, `registry:init`.

---

## MySQL access

| From         | Connection                                                                                   |
| ------------ | -------------------------------------------------------------------------------------------- |
| Host         | `127.0.0.1:3307`, user `fleetbase`, password in `apps/fleetbase/docker-compose.override.yml` |
| Inside stack | host `database`, port `3306`                                                                 |

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -it database mysql -ufleetbase -p fleetbase
```

---

## Redis access

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -it cache redis-cli
```

---

## Queue management

```bash
# Status
docker compose ... exec -T queue php artisan queue:status

# Restart workers after deploy
docker compose ... exec -T application php artisan queue:restart

# Restart queue container
docker compose ... restart queue
```

---

## Scheduler

Cron runs in `scheduler` container via `go-crond`. After deploy, sync tasks:

```bash
docker compose ... exec -T application php artisan schedule-monitor:sync
docker compose ... exec -T application php artisan schedule-monitor:list
```

---

## WebSocket / Console issues

1. Confirm `socket` container running on port `38000`
2. Check `apps/fleetbase/console/fleetbase.config.json`:
   - `API_HOST`: `http://localhost:8000`
   - `SOCKETCLUSTER_HOST`: `localhost`
   - `SOCKETCLUSTER_PORT`: `38000`
3. Verify `SOCKETCLUSTER_OPTIONS` origins in `docker-compose.override.yml` include `localhost`

Restart console + socket:

```bash
docker compose ... restart socket console
```

---

## Routing (OSRM / Valhalla)

| Engine              | When to use                                         |
| ------------------- | --------------------------------------------------- |
| OSRM public         | Fallback when Valhalla is building or unreachable   |
| Valhalla local      | Start Porterchain routing: `pnpm docker:up:routing` |
| Valhalla production | `pcd-valhalla` in prod compose (Ontario tiles)      |

Application env (via override): `VALHALLA_BASE_URL=http://host.docker.internal:8002`

Test Valhalla: `curl http://127.0.0.1:8002/status`

**Production:** API and website use `VALHALLA_BASE_URL=http://valhalla:8002` on the internal Docker network. First boot downloads Ontario OSM and builds tiles (~20–60 min on the droplet); quotes fall back to OSRM public until `/status` is healthy.

```bash
# On droplet (/opt/porterchain)
docker compose -f docker-compose.prod.yml logs -f valhalla
bash scripts/verify-routing.sh
curl -s https://api.porterchain.com/health/ready | jq '.checks.routing'
```

---

## Porterchain bridge

Porterchain API syncs orders to Fleetbase — **merchants never call Fleetbase directly**.

| Porterchain env                  | Purpose                   |
| -------------------------------- | ------------------------- |
| `FLEETBASE_API_URL`              | `http://localhost:8000`   |
| `FLEETBASE_DISPATCH_BRIDGE`      | `true`                    |
| `FLEETBASE_DEFAULT_COMPANY_UUID` | From Fleetbase onboarding |

Verify bridge (Porterchain API running):

```bash
curl http://localhost:8001/health
# Create test merchant booking — order should reach DISPATCH_READY + Fleetbase sync
```

---

## Port conflicts

| Port                             | Owner                              | Resolution                                                          |
| -------------------------------- | ---------------------------------- | ------------------------------------------------------------------- |
| 3306                             | Porterchain MySQL OR legacy stacks | Fleetbase uses **3307** on host                                     |
| Legacy stacks on 8000/4200/38000 | Stop before starting Fleetbase     | `docker ps` → identify project → `docker compose -p <project> down` |

---

## Backup

Porterchain **Postgres** (orders, merchants, billing) — scripts and **quarterly restore drill** (DD-28) in [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

```bash
# Prod droplet
./infrastructure/deploy/scripts/backup-porterchain-postgres.sh /var/backups/porterchain-$(date +%F).sql.gz

# Local dev
COMPOSE_FILE=infrastructure/docker/docker-compose.yml \
  ./infrastructure/deploy/scripts/backup-porterchain-postgres.sh
```

### Fleetbase MySQL

```bash
docker exec porterchain-fleetbase-mysql mysqldump -uroot -p<ROOT_PASS> \
  --databases fleetbase fleetbase_sandbox > fleetbase-backup-$(date +%F).sql
```

### Storage volume

```bash
docker run --rm -v porterchain-fleetbase-api-storage:/data -v $(pwd):/backup alpine \
  tar czf /backup/fleetbase-storage-$(date +%F).tar.gz -C /data .
```

---

## Incident response

| Symptom              | Action                                                                     |
| -------------------- | -------------------------------------------------------------------------- |
| API 502              | Check `application` + `httpd` logs; restart both                           |
| Migrations failed    | Grant MySQL privileges (install script step 6b); fresh volume if corrupted |
| Queue backlog        | Scale queue workers (duplicate `queue` service in override for prod)       |
| Console blank        | Rebuild console: `docker compose ... up -d --build console`                |
| Dispatch not syncing | Verify Porterchain `FLEETBASE_*` env + company UUID                        |

---

## Async runtime (Option A — current default)

Porterchain uses **Option A** (masterrule Appendix D4):

| Component                  | Role                                                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **API** (`apps/api`)       | Publishes domain events; registers handlers for in-process sync when Redis is absent                                    |
| **Worker** (`apps/worker`) | Consumes Redis stream `porterchain:events` (group `porterchain-workers`) + drains task queues, retries, and cron drains |

Local / prod: run both `pnpm dev:api` and `pnpm dev:worker` (or `pcd-worker`) so stream handlers and queue jobs run. The worker calls `ensure_handlers_registered()` then `consume_once()` each loop before draining named queues (`emails`, `billing`, `webhooks`, `dispatch`, …).

Production compose must include the worker service; sync-only mode (no worker) leaves stream events and queues unprocessed when Redis is up.

---

## D1 P0 — production loop checklist

Run locally after `pnpm docker:up`, Fleetbase (`pnpm docker:fleetbase:up`), and `apps/api/.env` configured:

```bash
pnpm db:migrate
pnpm dev:api                    # separate terminal
pnpm fleetbase:replay           # G2 — clear dead letters + sync orders
pnpm validate:p0                # G1–G9 gates
pnpm validate:e2e:reports       # full markdown reports (optional)
```

| Gate | What                          | Pass criteria                                                                     |
| ---- | ----------------------------- | --------------------------------------------------------------------------------- |
| G1   | API health + `booking_drafts` | `GET /health` 200; table exists; draft smoke POST                                 |
| G2   | Fleetbase sync                | ≥98% orders have `fleetbase_order_id` (excludes cancelled/refunded)               |
| G2b  | Merchant webhook delivery     | ≥99% final delivery success (`merchant_webhook_deliveries`, 7-day window)         |
| G2c  | Deploy frequency              | ≥2/week via [Deploy workflow](../.github/workflows/deploy.yml) on green CI `main` |
| G3   | Auto-dispatch                 | ≥90% pipeline orders with driver or Fleetbase link (`business_metrics`)           |
| G4   | On-time delivery              | ≥95% delivered within `scheduled_at` + 30m grace                                  |
| G5   | Support first response        | <4h average on tickets with `first_response_at`                                   |

See [PRIORITY_TODOS.md](docs/PRIORITY_TODOS.md) for dashboard paths and Prometheus series.
| G3 | Webhook secret | `FLEETBASE_WEBHOOK_SECRET` set; signed POST `/webhooks/fleetbase` |
| G8 | Stripe webhook (prod) | `STRIPE_WEBHOOK_SECRET` set; POST `/webhooks/stripe` ≠ 503 |
| G8b | Stripe dashboard URL | Webhook endpoint lists `porterchain.com/webhooks/stripe` |
| G8c | Stripe → invoice row | Recent row in `invoices` after live payment (droplet SQL) |
| G9 | Push live (prod) | `PORTERCHAIN_PUSH_SEND=true`; readiness `firebase: ok` |
| G4–G9 | E2E framework | `scripts/verify_p0_loop.py` (wraps `E2EValidationService`) |

**Prod droplet:** deploy workflow runs G1 smoke after migrate. Until `api.porterchain.com` is live, G1 prod stays open — see [infrastructure/deploy/README.md](./infrastructure/deploy/README.md).

```bash
pnpm validate:p0:prod   # G1/G8/G9 against https://api.porterchain.com
# G8b (Stripe dashboard): needs live key — does not read apps/api/.env mock mode
STRIPE_MOCK=false STRIPE_SECRET=sk_live_… pnpm validate:p0:prod
pnpm validate:p0        # full local G1–G9 including E2E phases
```

**G9 (notifications):** Prod requires `PORTERCHAIN_PUSH_ENABLED=true`, `PORTERCHAIN_PUSH_SEND=true`, and Firebase credentials. Confirm with `pnpm validate:p0:prod` (G9). **Device test:** register FCM token on driver/customer app, trigger a dispatch notification, confirm delivery on device.

---

## Prod vs local environment (§0.1.11)

| Variable / setting                      | Local (default)                   | Production (droplet)                                                |
| --------------------------------------- | --------------------------------- | ------------------------------------------------------------------- |
| `APP_ENV`                               | `local`                           | `production`                                                        |
| `STRIPE_MOCK`                           | `true`                            | `false`                                                             |
| `CLERK_DEV_BYPASS`                      | often `true`                      | `false`                                                             |
| Clerk keys                              | single `CLERK_*` or per-portal    | `CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_*` in Doppler               |
| `FLEETBASE_DISPATCH_BRIDGE`             | `true` (local Fleetbase :8000)    | `false` until prod Fleetbase + secrets                              |
| `FLEETBASE_API_URL`                     | `http://localhost:8000`           | Fleetbase prod URL (not localhost)                                  |
| `PORTERCHAIN_PUSH_SEND`                 | often `false` / log-only          | `true` (GitHub var)                                                 |
| `JWT_SECRET`                            | dev default allowed               | must be non-default (boot guard)                                    |
| `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` | optional                          | set in GitHub secrets for API + portals                             |
| `DATABASE_URL`                          | `localhost:5432`                  | in-compose `postgres:5432`                                          |
| `REDIS_URL`                             | `localhost:6379`                  | in-compose `redis:6379`                                             |
| Worker                                  | `pnpm dev:worker` (optional)      | `pcd-worker` container + heartbeat                                  |
| Valhalla / OSRM                         | local `:8002` (profile `routing`) | `pcd-valhalla` in compose; `VALHALLA_BASE_URL=http://valhalla:8002` |
| `ROUTING_ENGINE`                        | `valhalla` (API)                  | `valhalla` (API + website)                                          |

Templates: [`env/`](./env/README.md) · deploy secrets: [infrastructure/deploy/SECRETS.md](./infrastructure/deploy/SECRETS.md).

---

## Secret manager (DD-14)

| Store                       | Purpose                                                              |
| --------------------------- | -------------------------------------------------------------------- |
| **Doppler** (`pcd` / `prd`) | Production runtime secrets SSOT                                      |
| **GitHub Actions**          | `DEPLOY_*`, `DOPPLER_TOKEN`, build-time public keys                  |
| **Droplet**                 | Generated `/opt/porterchain/.env` (mode `600`) — do not edit by hand |

Each deploy runs `bash sync-secrets.sh` on the droplet. To rotate a secret: update Doppler → re-run Deploy workflow.

```bash
gh secret set DOPPLER_TOKEN -b "dp.st.prd.xxxx"
```

### Secrets rotation (§5.1.8)

| Secret class             | Cadence                         | Procedure                                                             |
| ------------------------ | ------------------------------- | --------------------------------------------------------------------- |
| `JWT_SECRET`             | 90 days                         | Doppler `prd` → Deploy workflow → verify `/health/ready`              |
| `CLERK_*` / JWKS         | on compromise or Clerk rotation | `pnpm clerk:sync` locally; Doppler prod keys → redeploy portals + API |
| `STRIPE_*`               | Stripe dashboard rotation       | Update Doppler + GitHub secrets; replay one test payment              |
| `FLEETBASE_*`            | 90 days or on leak              | Rotate in Fleetbase console + Doppler; `pnpm fleetbase:replay`        |
| `POSTGRES_PASSWORD`      | annual or on leak               | `ALTER USER` + update Doppler + rolling API restart                   |
| Firebase service account | annual                          | New key in Firebase → mount path on droplet → redeploy API            |

After any rotation: `pnpm validate:p0:prod` (when droplet live) and spot-check affected portal login.

---

## External uptime monitoring (§5.1.10)

Configure an external probe (UptimeRobot, Better Stack, or Pingdom) — **not** only Docker healthchecks.

| Probe           | URL                                        | Interval | Alert         |
| --------------- | ------------------------------------------ | -------- | ------------- |
| API liveness    | `https://api.porterchain.com/health`       | 1 min    | email + Slack |
| API readiness   | `https://api.porterchain.com/health/ready` | 5 min    | email + Slack |
| Website         | `https://porterchain.com`                  | 5 min    | email         |
| Merchant portal | `https://merchant.porterchain.com`         | 15 min   | email         |

**EXE-G2 target:** 30-day rolling uptime ≥99.5% on API liveness. Track in provider dashboard; export monthly screenshot to ops folder.

Local smoke (no external monitor): `curl -fsS http://localhost:8001/health/ready`.

---

## Incident drill (EXE-G3)

**Cadence:** semi-annual tabletop + annual live failover drill.

### Tabletop (60 min)

1. Scenario: API returns 502 for 10 minutes during peak dispatch.
2. On-call acknowledges alert (uptime monitor).
3. Walk through [Incident response](#incident-response) table + `pnpm validate:p0:fast` on staging.
4. Document gaps in ops ticket; link post-mortem template.

### Live drill (annual, staging)

1. Restore latest Postgres backup per [RUNBOOK.md](RUNBOOK.md).
2. Run `pnpm validate:p0` against restored stack.
3. Record RTO achieved vs 4h target in [SECURITY.md](./SECURITY.md).

---

## D3 — Phase 1 feature matrix

After D2 deletion pass, prove essential features are wired (Fowler: _make the walking skeleton boring_).

```bash
pnpm validate:d3        # static: API routes + client contracts (9 rows)
pnpm validate:d3:e2e    # static + E2E phase mapping (~10s)
```

| Row                              | Maps to E2E phase                            |
| -------------------------------- | -------------------------------------------- |
| Merchant dashboard               | `phase_3_merchant`                           |
| Driver / customer surfaces       | `phase_2_forward_logistics`                  |
| Dispatch, POD, tracking, billing | `phase_2` (+ `phase_3` for billing/merchant) |
| Routing                          | `phase_1_system_layer`                       |
| Partner API                      | `phase_3_merchant`                           |

Manual smoke (optional): book on `website` → pay → track on `apps/customer`; merchant bulk on `merchant-portal`; driver POD on `driver-portal` / mobile.

```bash
pnpm validate:d3:prod   # automated prod URL + quote smoke (Sprint F)
```

**G9 (Firebase push):** set repository variables `PORTERCHAIN_PUSH_ENABLED=true` and `PORTERCHAIN_PUSH_SEND=true` plus Firebase GitHub secrets. `/health/ready` reports `firebase: ok` when live send is enabled.

---

## D4 — Async runtime (prod)

Production runs a dedicated **`pcd-worker`** container (DD-04) that consumes the domain event stream and drains Redis queues; the API publishes events/jobs and reports queue depth + heartbeat on `/health/ready`.

| Mode      | When                                                                     | Compose                                                            |
| --------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Prod**  | API + worker; worker heartbeat required for `queues: ok`                 | `infrastructure/deploy/docker-compose.prod.yml` — `api` + `worker` |
| **Local** | `pnpm dev:worker` alongside `pnpm dev:api` (required when Redis is used) | Same stream + queue names as prod                                  |

Local dev: run `pnpm dev:worker` whenever Redis is up so `order.dispatch_ready`, webhooks, billing enqueue, and notifications are processed. See [infrastructure/deploy/README.md](./infrastructure/deploy/README.md).

---

### Fleetbase API key (local)

If sync jobs fail with `fleetbase_order_id_not_returned`, Fleetbase likely has no API credential:

```bash
docker exec porterchain-fleetbase-application php artisan tinker --execute="
\$c = \\Fleetbase\\Models\\Company::first();
\$cred = \\Fleetbase\\Models\\ApiCredential::create([
  'company_uuid' => \$c->uuid,
  'name' => 'porterchain-local',
  'key' => 'flb_live_' . bin2hex(random_bytes(16)),
]);
echo \$cred->key;
"
```

Set `FLEETBASE_API_KEY`, `FLEETBASE_DEFAULT_COMPANY_UUID`, and `FLEETBASE_DISPATCH_BRIDGE=true` in `apps/api/.env`.

### Queue backpressure (§3.4.5)

Worker queues are Redis lists (`porterchain:queue:*`). Monitor depth before consumers fall behind.

| Signal                       | Threshold   | Action                                                                                             |
| ---------------------------- | ----------- | -------------------------------------------------------------------------------------------------- |
| **Total depth** (all queues) | **> 1,000** | Diagnostics worker probe → `warning`. Scale `pcd-worker` replicas or investigate stuck consumer.   |
| **Single queue**             | **> 500**   | Check processor logs for that queue (`emails`, `sms`, `push`, `webhooks`, `billing`, `fleetbase`). |
| **Fleetbase retry pending**  | **≥ 500**   | `GET /v1/admin/operations/sync/health` — replay or fix credentials before backlog grows.           |
| **Event bus DLQ stream**     | **growing** | Inspect `porterchain:events:dlq` (Redis stream, max ~50k entries).                                 |

**Monitor:**

```bash
# Prometheus (scrape API /metrics)
porterchain_queue_depth{queue="emails"} 12

# Admin control tower (Clerk admin JWT)
GET /v1/admin/operations/queues

# Diagnostics bundle (includes queue_depths + recent event DLQ entries)
GET /v1/admin/diagnostics/workflows/event-pipeline
```

**Worker required:** queues drain only when `pnpm dev:worker` (local) or `pcd-worker` (prod) is running. API enqueue paths do not process jobs inline.

See [EVENT_BUS.md](./EVENT_BUS.md) for event-bus retry → DLQ semantics.

### Dead-letter replay (G2 + §2.3.6)

Porterchain has **four DLQ surfaces**. Fix the root cause (credentials, SMTP/FCM, webhook URL, Fleetbase down, bad event handler) before replaying.

| Surface               | Storage / signal                                 | List failed                                    | Replay                                                                                                                 |
| --------------------- | ------------------------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Fleetbase sync**    | `fleetbase_sync_jobs` (Postgres)                 | `GET /v1/admin/operations/sync/health`         | `pnpm fleetbase:replay` · `POST /v1/admin/operations/sync/requeue/{job_id}` · `POST /v1/admin/operations/sync/process` |
| **Notifications**     | `notification_records` (`failed`, `dead_letter`) | `GET /v1/admin/notifications/failed`           | `POST /v1/admin/notifications/retry/{notification_id}` (re-queues via worker `emails`/`sms`/`push`)                    |
| **Merchant webhooks** | `merchant_webhook_deliveries`                    | Merchant portal → Integrations → delivery logs | `POST /v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry`                                               |
| **Event bus**         | Redis stream `porterchain:events:dlq`            | Diagnostics `event-pipeline` workflow          | Fix handler + redeploy; replay manually from stream entry (no auto-replay yet)                                         |

**Worker required:** queued notification and webhook retries drain only when `pnpm dev:worker` (local) or `pcd-worker` (prod) is running. API inline handlers do not replace the worker loop.

```bash
# Fleetbase — CLI (all dead letters → pending, push unlinked orders, drain retry queue)
pnpm fleetbase:replay

# Fleetbase — Admin API (Clerk admin JWT)
POST /v1/admin/operations/sync/requeue/{job_id}
POST /v1/admin/operations/sync/process
GET  /v1/admin/operations/sync/health

# Notifications — Admin API
GET  /v1/admin/notifications/failed
POST /v1/admin/notifications/retry/{notification_id}

# Merchant outbound webhooks — Merchant portal API (Clerk merchant session)
POST /v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry
```

Monitor after replay: `GET /v1/diagnostics/fleetbase-sync` (admin), notification dashboard (`/v1/admin/notifications/dashboard`), merchant webhook delivery logs.

---

## Manual dispatch mode (prod — §0.1.5)

When **`FLEETBASE_DISPATCH_BRIDGE=false`** (current prod default until Fleetbase host + `FLEETBASE_*` secrets):

| Step                             | Owner                                              | SLA                        |
| -------------------------------- | -------------------------------------------------- | -------------------------- |
| Order confirmed (Stripe webhook) | API                                                | Automatic                  |
| Assign driver                    | Admin ops via `/v1/admin/dispatch/*`               | **≤15 min** business hours |
| Customer tracking                | Public `/track` + WS                               | Automatic after assign     |
| POD → DELIVERED                  | Driver portal + Fleetbase webhook (when bridge on) | Same day                   |

**Enable bridge when ready:** set Doppler `FLEETBASE_*`, `FLEETBASE_DISPATCH_BRIDGE=true`, redeploy API+worker. Verify `GET /health/ready` → `fleetbase: bridge_enabled` and `fleetbase_sync.meets_slo: true`.

Until then: document exceptions in admin ops runbook; target **≥90%** orders manually dispatched within SLA.

---

- Fleetbase upstream issues: https://github.com/fleetbase/fleetbase/issues
- Porterchain bridge: `apps/api/src/porterchain_api/fleetbase_engine/`
- Do **not** patch Fleetbase core — extend via Porterchain API layer only

---

## Related

- [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md)
- [DOCKER_SETUP.md](./DOCKER_SETUP.md)
- [SERVICE_STATUS.md](./SERVICE_STATUS.md)
- [PRODUCTION_READINESS_REPORT.md](docs/archive/reports-2026-08/PRODUCTION_READINESS_REPORT.md)
- [PRIORITY_TODOS.md](docs/PRIORITY_TODOS.md)

---
