# Performance Audit — Porterchain Platform

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §16 (Observability)

> **Database detail:** [POSTGRESQL_PERFORMANCE.md](./POSTGRESQL_PERFORMANCE.md) · **DB audit:** [DATABASE_AUDIT.md](./DATABASE_AUDIT.md)

---

## Executive verdict

| Area                 | Status                                                   |
| -------------------- | -------------------------------------------------------- |
| Connection pool      | **PASS**                                                 |
| PostgreSQL indexes   | **PARTIAL** — core + CRM GIN applied; more JSONB pending |
| Caching              | **PARTIAL** — Redis queues/events; no global HTTP cache  |
| Background workers   | **PASS**                                                 |
| API latency patterns | **ACCEPTABLE**                                           |
| Query optimization   | **PARTIAL**                                              |

---

## Connection pool

| Setting                      | Implementation                 |
| ---------------------------- | ------------------------------ |
| Engine                       | SQLAlchemy + psycopg           |
| `pool_pre_ping`              | ✅                             |
| `pool_size` / `max_overflow` | 10 / 20 defaults — `config.py` |
| SQLite                       | Rejected at startup            |

---

## Database performance

### Indexes applied (Alembic `m1`, `n2`)

| Index                            | Purpose               |
| -------------------------------- | --------------------- |
| `ix_orders_state_created_at`     | Control tower / queue |
| `ix_orders_merchant_state`       | Merchant lists        |
| `ix_domain_events_type_occurred` | Event queries         |
| `ix_fleetbase_sync_jobs_pending` | Retry drain (partial) |
| GIN on CRM JSONB                 | Company/lead search   |
| `uq_orders_quote_id`             | Retail idempotency    |

### Open gaps

| ID    | Severity | Issue                                                          |
| ----- | -------- | -------------------------------------------------------------- |
| P-M01 | Medium   | JSONB rollout incomplete for non-CRM tables                    |
| P-M02 | Medium   | Missing FK indexes on newer tables (route center, invitations) |
| P-L01 | Low      | String UUID vs native UUID                                     |

---

## Caching

| Layer                               | Status                                            |
| ----------------------------------- | ------------------------------------------------- |
| Redis — events, queues, idempotency | ✅                                                |
| Clerk JWKS                          | ✅ Cached in auth module                          |
| HTTP response cache                 | ⚠️ Not global                                     |
| Valhalla/OSRM route results         | ⚠️ No short-TTL cache (Route Center repeats legs) |

**P-M03:** Recommend Redis cache for repeated route matrix lookups in Route Center.

---

## Background workers

| Component       | Role                                          |
| --------------- | --------------------------------------------- |
| `apps/worker/`  | Event bus consume, queue drain                |
| Fleetbase retry | `process_retry_queue` (~60s)                  |
| Queues          | email, SMS, push, billing, webhooks, dispatch |

Diagnostics expose queue depth and DLQ.

---

## API performance patterns

### Good

- Thin routers on quotes, webhooks, booking drafts
- Admin list caps (max 500 on route center plans)
- Live map WS + poll fallback

### Concerns

| ID    | Severity | Issue                              | Location               |
| ----- | -------- | ---------------------------------- | ---------------------- |
| P-H01 | High     | Large `driver.py` router surface   | `routers/driver.py`    |
| P-M04 | Medium   | Admin pricing N+1 merchant lookups | `routers/admin.py`     |
| P-M05 | Medium   | CRM list without cursor pagination | `crm_sales_service.py` |

---

## Homepage latency (fixed)

Anonymous `GET /v1/booking-drafts/active` no longer returns slow 404 — returns `200 null` with sessionStorage hint on website.

---

## Observability (§16)

| Requirement                  | Status                    |
| ---------------------------- | ------------------------- |
| Structured logging           | ✅                        |
| Correlation IDs              | ⚠️ Partial HTTP → event   |
| Queue / DLQ monitoring       | ✅ Diagnostics            |
| Integration health dashboard | ✅                        |
| Webhook success rate         | ⚠️ Manual via diagnostics |

---

## Recommended actions

1. **High** — Refactor `driver.py` router
2. **Medium** — Route result caching for Route Center
3. **Medium** — Valhalla/OSRM readiness probes for routing-dependent deploys
4. **Low** — Continue JSONB + index rollout

---

## Related

| Document                                                           | Purpose                |
| ------------------------------------------------------------------ | ---------------------- |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) | Platform gates         |
| [ROUTE_CENTER_PERFORMANCE.md](./ROUTE_CENTER_PERFORMANCE.md)       | Route Center specifics |
