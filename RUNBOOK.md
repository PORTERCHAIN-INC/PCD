# Operations Runbook

**Type:** CANONICAL  
**Parent:** [`infrastructure/system.md`](./infrastructure/system.md)  
**Verified against code:** 2026-09-12  
**Lens:** Jeff Dean — day-2 maps to real processes and queues.

---

## Local before production

Test the change on this Mac, then build the touched web images locally (`pnpm --filter <pkg> build`), then push and start CI/CD. Do not dispatch Deploy first. Deploy builds the GitHub commit, not the working tree. Rule: [`.cursor/rules/local-before-production.mdc`](./.cursor/rules/local-before-production.mdc).

## First checks

| Symptom                           | Check (real)                                                                                               |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| API down                          | `:8001` health · Postgres `DATABASE_URL` · Redis                                                           |
| Orders accept, no dispatch motion | `FleetbaseSyncJob` due/dead via `RetryQueue`/`ErrorQueue` · `apps/worker` running · Fleetbase via adapter  |
| Stale live map / route            | GET path · `fleetbase_ops_timeout=2s` · `CircuitBreaker` state                                             |
| Bad quotes / distances            | Valhalla `:8002` · production `OSRM_HOST` stays empty · look for source `haversine` in distance resolution |
| Auth failures                     | Clerk portal keys · Staff IdP (admin) · SpiceDB · ensure bypass only when `APP_ENV=local`                  |
| Webhook issues                    | Stripe/Shopify signature verify · idempotency · handler logs                                               |
| Event lag                         | Redis stream `porterchain:events` / DLQ `porterchain:events:dlq`                                           |

Manual Fleetbase drain exists via operations sync process endpoint (`limit=1`) in addition to worker loop.

### Fleetbase dispatch bridge (`FLEETBASE_DISPATCH_BRIDGE`)

- **Off (default):** commercial API still books; logistics sync/enqueue stays idle — use for local without Fleetbase or when deliberately freezing dispatch.
- **On:** set `FLEETBASE_DISPATCH_BRIDGE=true` plus API key / webhook secret; `apps/worker` must run so `process_dispatch` + `BookingSyncService` drain `FleetbaseSyncJob` (`kind=order`).
- **Manual path:** Admin operations → process sync retry (`limit=1`) or `pnpm fleetbase:replay` when the worker is behind; never open Fleetbase HTTP from portals.
- Bond / handshake: `pnpm fleetbase:bond` · boundary: [`docs/architecture/FLEETBASE_BOUNDARY.md`](./docs/architecture/FLEETBASE_BOUNDARY.md).

---

## SPOF map

| SPOF      | If down             | Action                                                              |
| --------- | ------------------- | ------------------------------------------------------------------- |
| Postgres  | Writes fail         | Fail closed; restore per deploy runbooks                            |
| Redis     | EventBus/cache hurt | Restore Redis; commercial rows still in Postgres; redrive consumers |
| Worker    | Sync + events stall | Restart worker; inspect job age                                     |
| Fleetbase | Logistics lag       | Commercial API can stay up; communicate dispatch delay              |
| SpiceDB   | Deny authz          | Restore; do not add Check allow-cache                               |

---

## Deploy / secrets

**SSOT:** [`infrastructure/deploy/README.md`](./infrastructure/deploy/README.md) · secrets: [`infrastructure/deploy/SECRETS.md`](./infrastructure/deploy/SECRETS.md) (Doppler `pcd`/`prd`) · connections: [`docs/CONNECTIONS.md`](./docs/CONNECTIONS.md) (`pnpm connections:check`)

| Trigger              | Workflow                   | Result                                                          |
| -------------------- | -------------------------- | --------------------------------------------------------------- |
| PR / push to `main`  | `CI`                       | Static gates (`pnpm validate:ci`) + Admin Vitest + API Postgres |
| PR / push to `main`  | `Security`, `CodeQL`       | Bandit/Trivy + CodeQL (parallel to CI)                          |
| Green `CI` on `main` | `Deploy` (`scope=full`)    | GHCR images → droplet compose + migrate + D3 smoke              |
| Manual               | `Deploy` (`scope=website`) | Website image only + site smoke                                 |
| Cron 11:00 UTC       | `Nightly E2E`              | D3 behavioral matrix (Postgres + Redis + Valhalla stub)         |
| Manual               | `Set Public Ingest Key`    | Ensure `PUBLIC_INGEST_API_KEY` in Doppler; roll `api` + `web`   |

Git push from a laptop uses the deploy key in [`docs/GITHUB_SSH_KEYS.md`](./docs/GITHUB_SSH_KEYS.md) — not Actions sync jobs.

- Prod Postgres image currently **16.10** (dev **18**) — plan migrations before assuming PG18 in prod
- Rollback: deploy README § Rolling deploy / rollback

---

## Related

[`docs/architecture/FAILURE_POSTURE.md`](./docs/architecture/FAILURE_POSTURE.md) · [`EVENT_BUS.md`](./EVENT_BUS.md) · [`docs/architecture/FLEETBASE_BOUNDARY.md`](./docs/architecture/FLEETBASE_BOUNDARY.md)

### Queue backpressure

Worker queues are Redis lists (`porterchain:queue:*`). Monitor depth before consumers fall behind.

| Signal        | Threshold | Action                                        |
| ------------- | --------- | --------------------------------------------- |
| Total depth   | > 1,000   | Scale `pcd-worker` or inspect stuck consumers |
| Single queue  | > 500     | Check processor logs for that queue           |
| Event bus DLQ | growing   | Inspect Redis stream `porterchain:events:dlq` |

```bash
porterchain_queue_depth{queue="emails"} 12
GET /v1/admin/operations/queues
```

### Dead-letter replay

| Surface           | Replay                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| Fleetbase sync    | `pnpm fleetbase:replay`                                                  |
| Notifications     | `POST /v1/admin/notifications/retry/{notification_id}`                   |
| Merchant webhooks | `POST /v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry` |
| Event bus         | Redis stream `porterchain:events:dlq`                                    |

### G2 — Fleetbase sync SLO

Target: **≥98%** of due commercial sync jobs succeed within the RetryQueue window (`FLEETBASE_SYNC_SLO_TARGET_PCT`). Below-SLO fires `build_fleetbase_sync_alerts` on Control Tower / diagnostics and can fail `/health/ready` when `meets_slo` is false. Replay stuck jobs with `pnpm fleetbase:replay` or admin `process_sync_retry`.
