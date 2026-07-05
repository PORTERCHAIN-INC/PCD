# Porterchain Operations Runbook


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Day-2 procedures for the Porterchain monorepo and the self-hosted Fleetbase stack.

---

## Porterchain platform — daily checks

```bash
pnpm docker:up              # PostgreSQL :5432, Redis :6379, Mailhog :8025
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

| Engine         | When to use                                         |
| -------------- | --------------------------------------------------- |
| OSRM public    | Default; no local setup                             |
| Valhalla local | Start Porterchain routing: `pnpm docker:up:routing` |

Application env (via override): `VALHALLA_BASE_URL=http://host.docker.internal:8002`

Test Valhalla: `curl http://127.0.0.1:8002/status`

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

| Port              | Owner                              | Resolution                                                                     |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------------------ |
| 3306              | Porterchain MySQL OR legacy stacks | Fleetbase uses **3307** on host                                                |
| Legacy stacks on 8000/4200/38000 | Stop before starting Fleetbase | `docker ps` → identify project → `docker compose -p <project> down` |

---

## Backup

### MySQL

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

| Component | Role |
| --------- | ---- |
| **API** (`apps/api`) | Registers domain event handlers in FastAPI lifespan; processes inline where cheap |
| **Worker** (`apps/worker`) | Redis queue consumer only — retries, cron, webhook replay; **does not** duplicate handler registry |

Local dev: run both `pnpm dev:api` and `pnpm dev:worker` when testing queues. Production compose must either (a) include the worker service for queue drains, or (b) document sync-only mode if queues are disabled.

Handler registration is **API-only** — the worker loop consumes named queues (`emails`, `billing`, `webhooks`, `dispatch`, …) without re-registering `porterchain_event_bus` handlers.

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

| Gate | What | Pass criteria |
| ---- | ---- | ------------- |
| G1 | API health + `booking_drafts` | `GET /health` 200; table exists; draft smoke POST |
| G2 | Fleetbase sync | ≥90% orders have `fleetbase_order_id` |
| G3 | Webhook secret | `FLEETBASE_WEBHOOK_SECRET` set; signed POST `/webhooks/fleetbase` |
| G4–G9 | E2E framework | `scripts/verify_p0_loop.py` (wraps `E2EValidationService`) |

**Prod droplet:** deploy workflow runs G1 smoke after migrate. Until `api.porterchain.com` is live, G1 prod stays open — see [infrastructure/deploy/README.md](./infrastructure/deploy/README.md).

```bash
pnpm validate:p0:prod   # G1 against https://api.porterchain.com (skips local DB + E2E)
pnpm validate:p0        # full local G1–G9 including E2E phases
```

**G9 (notifications):** local `validate:p0` may show `phase WARNING` when Firebase/FCM is not configured — acceptable for dev. Prod requires `FIREBASE_PROJECT_ID` + credentials; see [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md).

---

## D3 — Phase 1 feature matrix

After D2 deletion pass, prove essential features are wired (Fowler: *make the walking skeleton boring*).

```bash
pnpm validate:d3        # static: API routes + client contracts (9 rows)
pnpm validate:d3:e2e    # static + E2E phase mapping (~10s)
```

| Row | Maps to E2E phase |
| --- | ----------------- |
| Merchant dashboard | `phase_3_merchant` |
| Driver / customer surfaces | `phase_2_forward_logistics` |
| Dispatch, POD, tracking, billing | `phase_2` (+ `phase_3` for billing/merchant) |
| Routing | `phase_1_system_layer` |
| Partner API | `phase_3_merchant` |

Manual smoke (optional): book on `website` → pay → track on `apps/customer`; merchant bulk on `merchant-portal`; driver POD on `driver-portal` / mobile.

---

## D4 — Async runtime (Option A — prod default)

Production uses **sync-only API handlers** (see `ensure_handlers_registered()` in API lifespan). The worker is **not** in `docker-compose.prod.yml` — queue drains run inline in the API process.

| Mode | When | Compose |
| ---- | ---- | ------- |
| **Option A (default prod)** | Event handlers in API lifespan; worker optional locally | `infrastructure/deploy/docker-compose.prod.yml` — no `worker` service |
| **Option B (scale)** | API publishes only; dedicated worker drains queues | Add `worker` service to prod compose + document in this section |

Local dev: run `pnpm dev:worker` alongside `pnpm dev:api` when testing Redis queue drains. See [infrastructure/deploy/README.md](./infrastructure/deploy/README.md#images-built).

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

### Dead-letter replay (G2)

```bash
# CLI (all dead letters → pending, push unlinked orders, drain retry queue)
pnpm fleetbase:replay

# Admin API (requires Clerk admin JWT)
POST /v1/admin/operations/sync/requeue/{job_id}
POST /v1/admin/operations/sync/process
GET  /v1/admin/operations/sync/health
```

Replay only after fixing root cause (missing API key, company UUID, or Fleetbase down). Monitor `fleetbase_sync_jobs` status counts and `GET /v1/diagnostics/fleetbase-sync` (admin).

---

- Fleetbase upstream issues: https://github.com/fleetbase/fleetbase/issues
- Porterchain bridge: `apps/api/src/porterchain_api/fleetbase_engine/`
- Do **not** patch Fleetbase core — extend via Porterchain API layer only

---

## Related

- [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md)
- [DOCKER_SETUP.md](./DOCKER_SETUP.md)
- [SERVICE_STATUS.md](./SERVICE_STATUS.md)
- [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)
- [ROADMAP.md](./ROADMAP.md)
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
