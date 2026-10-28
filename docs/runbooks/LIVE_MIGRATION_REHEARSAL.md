# Live migration rehearsal — cw0 → dm4 (2026-10-28)

A full local rehearsal of the pending migrations and the new code against a copy of
the live Ubuntu database. Nothing live was written; every container was removed afterwards.

## Environment

| Item              | Value                                                                                                                                     |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Source            | `porterchain-postgres` (postgres:18-alpine3.24), DB `porterchain`, 127 MB, no PostGIS                                                     |
| Data              | 2,680 orders · 968 packages · 2,016 merchants                                                                                             |
| Starting revision | `ba0attach0001`                                                                                                                           |
| Dump              | read-only `pg_dump -Fc`, 2.3 s, 10 MB (chmod 600, deleted after)                                                                          |
| Copy              | `pcd-rehearsal-pg` same image, 127.0.0.1:55532, restore 6.4 s                                                                             |
| Side services     | throwaway Redis :56579, SpiceDB :55151 (schema loaded, 226 users synced), Mailpit SMTP :51025                                             |
| App               | API :18001, worker, admin :13002 (merchant :13001 / driver :13003 — see issue 8)                                                          |
| Sanitised on copy | `merchant_webhooks.url` → local sink (38), `notification_devices.fcm_token` (63), `shopify_shops` tokens nulled (582), dead HTTP(S) proxy |

## Timings (each includes ~1.4 s alembic start-up)

| Migration                 | Time   | Notes                                                                                    |
| ------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| cw0corrwide0001           | 1.54 s |                                                                                          |
| bf0focusauth1a2b          | 1.53 s |                                                                                          |
| dm1driftfix0001           | 1.63 s | 0 blog backup rows archived                                                              |
| dm2fkorphan0002           | 1.88 s | one 0.22 s slow query on a concurrent `orders` probe; no errors                          |
| dm3custody0003            | 1.55 s | no unknown package statuses                                                              |
| dm4nocod0004              | 1.51 s | archived 8 COD orders (all `collected`), 17 `cod_enabled`, 9 `stripe_connect_account_id` |
| downgrade → ba0attach0001 | 1.98 s | checksums identical to live                                                              |
| re-upgrade                | 1.94 s | `alembic check` clean                                                                    |

dm2 orphan handling (final run): `abandoned_checkouts.quote_id` moved 6 ·
`crm_companies.merchant_id` nulled 20 · `crm_referral_credits.company_id` nulled 3 ·
`crm_leads.company_id/quote_id/booking_draft_id/order_id` nulled 3/10/3/4 ·
`pricing_fsa_rates.merchant_id` **moved 42**. No FK left NOT VALID.

## Smoke results

- `run_e2e_validation.py`: 99 pass, 1 warning (Nominatim not running), 0 fail.
- HTTP: health, merchant `me`, orders list, public tracking (no recipient email in body),
  quote with `cod_amount_cents` → 422, Shopify webhook bad HMAC → 401 / good HMAC → 200.
- In-process: driver scan resolves a partner barcode; delivered → manifested refused and audited;
  Interac approve records the payment and (after fix) marks the invoice `paid`.
- Stripe: skipped — no test keys on the machine, `STRIPE_MOCK=true` only.
- Notifications: email went to Mailpit sinks only (no relay), SMS deferred (no provider), push tokens sanitised.
- Playwright admin `@p0` (live, :13002): 41 pass, 5 fail (issue 9).

## Issues

| #   | Issue                                                                                                                                                                                                               | Cause                                                                                                                                                                             | Fix                                                                                             | Type                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| 1   | **dm2 would have nulled 42 live `pricing_fsa_rates.merchant_id`** for deleted merchants, turning private rates into platform-wide prices                                                                            | blanket SET NULL for orphans                                                                                                                                                      | CASCADE/NOT NULL orphans are moved to `fk_orphan_quarantine`; RESTRICT only reported (4dbbee1f) | code, fixed                                     |
| 2   | Interac/offline payment left `invoices.status = 'open'` when fully paid (21 such rows on live)                                                                                                                      | `record_payment` never called `persist_invoice_status`                                                                                                                            | now persisted, test added (ad83e063)                                                            | code, fixed; live step for the 21 existing rows |
| 3   | Local SMTP always forced to localhost:1025 (≈87 rehearsal mails landed in dev Mailpit, no relay, nothing left the machine)                                                                                          | override ignored explicit loopback host/port                                                                                                                                      | explicit loopback honoured (583f26e2)                                                           | code, fixed                                     |
| 4   | Defaults point at live side services (SpiceDB localhost:50051, Redis localhost:6379)                                                                                                                                | config defaults                                                                                                                                                                   | always set `SPICEDB_*`, `REDIS_URL` explicitly                                                  | live-run step                                   |
| 5   | Live worker has not been running — first run fires a backlog: 14 credit holds + 14 hold mails, 13 churn mails, 49 SLA breaches, 4 lead nurture, 25 lead SLA escalations, 22 draft expiries, 1 failed standing order | stalled worker                                                                                                                                                                    | review lists, pause sweeps for the window                                                       | live-run step                                   |
| 6   | 54 test blog posts on live; 3 drafts with past `scheduled_publish_at` would be published publicly on first worker run                                                                                               | test data in prod                                                                                                                                                                 | delete or unschedule before worker start                                                        | live-run step                                   |
| 7   | Smoke paths: Shopify is `/v1/integrations/shopify/webhooks`; driver scan `/driver-api/v1/orders/{id}/packages/scan`, `/driver-api/v1/scan/lookup`; Interac approve needs step-up                                    | rehearsal script                                                                                                                                                                  | documented                                                                                      | n/a                                             |
| 8   | Merchant/driver portals 500 locally without a Clerk publishable key even with `NEXT_PUBLIC_CLERK_DEV_BYPASS=true`                                                                                                   | `clerkMiddleware` / provider throws when keys missing                                                                                                                             | not fixed — needs a `pk_test` key or a bypass branch in middleware                              | open (dev only)                                 |
| 9   | Admin e2e UI-LEAD-001/2/3, UI-OPS-006 ×2 fail: "Continue as Local Super Admin" click never sends the POST (API endpoint itself returns 200)                                                                         | likely click before hydration in `next dev`                                                                                                                                       | not fixed — retry against `next start` build                                                    | open (test harness)                             |
| 10  | Worker had no way to pause outbound/backlog sweeps on a copy of live data                                                                                                                                           | only merchant ops had a flag                                                                                                                                                      | `WORKER_PAUSED_SWEEPS=name,…` or `all` (8d57fc67); use it for the first live start too          | code, fixed                                     |
| 11  | Persona/driver auth specs assume Clerk seats; local bypass is always the owner                                                                                                                                      | test assumption                                                                                                                                                                   | skip seat-hide / redirect checks under bypass (c70ad1aa)                                        | test, fixed                                     |
| 12  | Portals fetch Google Fonts at build/dev time; offline/proxied boxes log warnings and fall back                                                                                                                      | `next/font/google`                                                                                                                                                                | allow fonts.googleapis.com/gstatic in NO_PROXY or ignore                                        | dev note                                        |
| 13  | 3 pytest cases failed on re-runs (partner barcode, blog scheduled publish, Shopify four-click)                                                                                                                      | services commit, so rows from earlier runs leak in the shared test DB; the live blog posts `wait-*`/`due-*` match these test slugs, so the suite has been run against live before | tests use unique values / tolerate leftovers; never point `DATABASE_URL` for pytest at live     | test fixed + live step                          |

Persistent local environment: see `docs/runbooks/LOCAL_STACK.md`.

## Pre-flight checklist

- [ ] Fresh read-only `pg_dump` of live kept off-box-safe (chmod 600) as the restore point.
- [ ] Confirm live is at `ba0attach0001`: `alembic current`.
- [ ] Explicit `DATABASE_URL`, `REDIS_URL`, `SPICEDB_ENDPOINT`/key in the service env.
- [ ] Blog: delete/unschedule test posts (`wait-*`, `due-*`, `by-author-*`), esp. the 3 overdue drafts.
- [ ] Export and review the merchant ops sweep hold/churn list and SLA backlog; pause those sweeps for the window.
- [ ] Note the 21 fully paid `open` invoices (`select id from invoices where status='open' and amount_paid_cents>=amount_cents`).
- [ ] Quiet window agreed (no drivers on route, no merchant billing run).

## Live order

1. Deploy code (all commits up to and including ad83e063) — new code tolerates the old schema.
2. Stop the worker.
3. `alembic upgrade head` (≈10 s total).
4. Check `fk_orphan_quarantine` counts match the rehearsal (±new rows); confirm 42 `pricing_fsa_rates` moved, not nulled.
5. Fix the 21 stale invoices: re-run `persist_invoice_status` for them (one-off script, staff-reviewed).
6. Start the worker with `WORKER_PAUSED_SWEEPS=all` (or the outbound list), then clear it after review.

dm4 drops COD columns — data is archived first, but treat it as the point of no easy return.

## Rollback

- `alembic downgrade ba0attach0001` (rehearsed: 1.98 s, data identical), then redeploy the previous code.
- If past dm4 with new writes: restore from the pre-flight dump.

## Post-checks

- `alembic current` = head, `alembic check` clean.
- `/health`, merchant `me`, public tracking, quote with COD → 422.
- Driver scan and partner barcode lookup; refusal audit rows written.
- Interac approve → invoice `paid`.
- Worker logs: no errors; notification counts in expected range.
