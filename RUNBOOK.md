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
| Orders accept, no dispatch motion | `apps/worker` running · Optimize preview/accept · day-plan scorecard on Control Tower / diagnostics        |
| Stale live map / route            | Redis `last_known` · driver on duty · Valhalla `:8002`                                                     |
| Bad quotes / distances            | Valhalla `:8002` · production `OSRM_HOST` stays empty · look for source `haversine` in distance resolution |
| Auth failures                     | Clerk portal keys · Staff IdP (admin) · SpiceDB · ensure bypass only when `APP_ENV=local`                  |
| Webhook issues                    | Stripe/Shopify signature verify · idempotency · handler logs                                               |
| Event lag                         | Redis stream `porterchain:events` / DLQ `porterchain:events:dlq`                                           |

### Dispatch (PorterChain day plan)

- Assign and Optimize live in PorterChain. OR-Tools in `dispatch_engine` orders one van’s stops; Valhalla is the road cost; Redis `last_known` is the pin.
- Worker must run so optimize jobs and event consumers drain. There is no vendor console or VROOM client.
- Boundary: [`.cursor/rules/fleetbase-first-policy.mdc`](./.cursor/rules/fleetbase-first-policy.mdc) · architecture: [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## SPOF map

| SPOF     | If down             | Action                                                              |
| -------- | ------------------- | ------------------------------------------------------------------- |
| Postgres | Writes fail         | Fail closed; restore per deploy runbooks                            |
| Redis    | EventBus/cache hurt | Restore Redis; commercial rows still in Postgres; redrive consumers |
| Worker   | Optimize + events   | Restart worker; inspect job age                                     |
| Valhalla | Day plan / ETA lag  | Keep current stop list; communicate dispatch delay                  |
| SpiceDB  | Deny authz          | Restore; do not add Check allow-cache                               |

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
- Rollback: deploy README § Rolling deploy / rollback. After a full deploy, schema rollback is `CONFIRM_RESTORE=yes bash scripts/rollback-prod.sh` on the droplet (pre-migrate dump + image pin). Image pin alone leaves a migrated schema in place.

### Email notifications: deploy prerequisites

Receiver/customer delivery emails are on by default (email only). Before a deploy that ships them:

1. **`ZEPTOMAIL_WEBHOOK_SECRET`** in Doppler `pcd/prd` (long random string). In ZeptoMail → Mail Agent → Webhooks, point bounce + complaint events at `https://api.porterchain.com/v1/public/mail/zeptomail` with custom header `X-Porterchain-Mail-Webhook: <same secret>`. Without the secret the endpoint returns **503** outside local (it used to accept anyone, who could then suppress real customer addresses).
2. `MAIL_TRANSPORT=https`, ZeptoMail token, and a from-address on a domain with SPF + DKIM + DMARC passing (check one sample in Gmail "Show original").
3. `UNSUBSCRIBE_MAILBOX` (optional, default `unsubscribe@porterchain.com`) must exist or forward to a monitored inbox: it is the `mailto:` half of `List-Unsubscribe` on marketing/CRM mail.
4. `support@porterchain.com` (or each merchant's `tracking.support_email`) must be monitored: it is the "Report a problem" target in receiver emails.
5. `OPS_WATCH_EMAILS` must include the address that should get admin emails (failed delivery, reschedule, notification-health alert). Staff email only goes to that list; the bell works regardless.
6. Run `alembic upgrade head` (adds `notification_records.idempotency_key` + `dedupe_family`). Downgrade restores the old JSON expression index.

After deploy: Admin → Notifications shows `held` (quiet hours) and `dead_letter` rows; dead letters replay from there. Ops gets one bell + email alert per hour when ≥5 dead letters or ≥20% send failures (≥10 sends) happen in an hour.

---

## Related

[`docs/architecture/FAILURE_POSTURE.md`](./docs/architecture/FAILURE_POSTURE.md) · [`EVENT_BUS.md`](./EVENT_BUS.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md)

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
| Day-plan optimize | Admin Optimize → preview / accept (or re-run after a failed worker job)  |
| Notifications     | `POST /v1/admin/notifications/retry/{notification_id}`                   |
| Merchant webhooks | `POST /v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry` |
| Event bus         | Redis stream `porterchain:events:dlq`                                    |

### G2 — Day-plan scorecard

Target: Optimize runs finish with an explainable scorecard (assigned, unassigned with reason, meters/seconds). Diagnostics and Control Tower surface day-plan failures, not a vendor sync SLO. Guard: `python3 scripts/verify_fleetbase_sync_slo.py` (day-plan modules + no retired sync health).
