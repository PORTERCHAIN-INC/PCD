# PostgreSQL Performance Report

**Date:** July 1, 2026  
**Scope:** Porterchain PostgreSQL schema and query patterns  
**Status:** Recommendations — Phase 5 not yet implemented

---

## Connection pool (implemented)

| Setting         | Value          | Location                             |
| --------------- | -------------- | ------------------------------------ |
| `pool_size`     | 10             | `apps/api/src/porterchain_api/db.py` |
| `max_overflow`  | 20             | `db.py`                              |
| `pool_timeout`  | 30s            | `db.py`                              |
| `pool_recycle`  | 1800s (30 min) | `db.py`                              |
| `pool_pre_ping` | true           | `db.py`                              |

**Classification:** **Healthy** for local/single-node API. Tune `pool_size` × Uvicorn workers in production load testing.

---

## Existing indexes (Alembic)

Initial schema and subsequent migrations define indexes on:

- Foreign key columns (`order_id`, `merchant_id`, `clerk_user_id`, etc.)
- Status / kind columns on sync jobs, notifications, orders
- Audit log `action` column
- Fleetbase sync `next_attempt_at`, `idempotency_key`

**Classification:** **Healthy** for MVP scale.

---

## Missing indexes (recommended)

| Table                  | Recommended index                                                          | Reason                       | Priority |
| ---------------------- | -------------------------------------------------------------------------- | ---------------------------- | -------- |
| `crm_companies`        | GIN on `address` JSONB (after JSONB migration)                             | City/province filters        | High     |
| `crm_leads`            | GIN on `address`, `custom_fields`                                          | Faceted search               | High     |
| `orders`               | Composite `(status, created_at DESC)`                                      | Admin order grid             | High     |
| `orders`               | Composite `(merchant_id, status)`                                          | Merchant portal lists        | High     |
| `domain_events`        | `(event_type, occurred_at DESC)`                                           | Event bus diagnostics        | Medium   |
| `fleetbase_sync_jobs`  | Partial `(status, next_attempt_at) WHERE status IN ('pending','retrying')` | Worker dequeue               | High     |
| `notification_records` | `(status, created_at)`                                                     | Notification admin dashboard | Medium   |
| `admin_audit_logs`     | `(resource_type, resource_id, created_at DESC)`                            | Settings audit trail         | Medium   |
| `booking_drafts`       | `(session_id)` unique                                                      | Session restore              | Medium   |

---

## JSON / JSONB queries

| Current                              | Issue                           | Recommendation                                                                |
| ------------------------------------ | ------------------------------- | ----------------------------------------------------------------------------- |
| `JSON` type + `column['key'].astext` | Works but no index support      | Migrate to `JSONB`                                                            |
| CRM address filters                  | Sequential scan on large tables | GIN `jsonb_path_ops` on `address`                                             |
| Route `stops`, `order_ids`           | Large payloads                  | Keep JSONB; avoid filtering inside JSON where possible — normalize hot fields |

---

## Slow query risks

| Query pattern                             | Service               | Risk                            |
| ----------------------------------------- | --------------------- | ------------------------------- |
| `limit: 10000` driver/merchant lists      | Admin grids           | Full table scan + large payload |
| CRM lead search with multiple `OR` + JSON | `crm_sales_service`   | CPU-heavy without GIN           |
| Diagnostics health (many HTTP probes)     | Not DB — cached 45s   | N/A                             |
| `queue_depths()`                          | Redis, not PostgreSQL | N/A                             |

**Recommendations:**

1. Paginate admin lists (default `limit=100`, max `500`).
2. Add materialized columns for `city` / `province` on CRM if JSONB migration deferred.
3. Use `EXPLAIN ANALYZE` on top 10 admin queries before production load test.

---

## Transactions and locks

| Pattern                       | Current                            | Recommendation                                                        |
| ----------------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| Service-level commits         | Per service method                 | **Healthy** — keep transactions short                                 |
| Stripe webhook + order create | Single transaction in booking flow | Verify rollback on partial failure                                    |
| Fleetbase sync job claim      | Status update + attempt increment  | Use `SELECT … FOR UPDATE SKIP LOCKED` for worker concurrency (future) |
| Long-running reports          | Stub queue                         | Route to `reports` Redis queue — avoid long PG transactions           |

---

## Partitioning (future-ready)

| Table                        | Strategy                                             | When                  |
| ---------------------------- | ---------------------------------------------------- | --------------------- |
| `domain_events`              | Range partition by `occurred_at` (monthly)           | >10M rows             |
| `admin_audit_logs`           | Range partition by `created_at`                      | >5M rows              |
| `notification_delivery_logs` | Range partition + TTL archive                        | >10M rows             |
| `driver_location_pings`      | Time-series partition or move to Timescale/Redis geo | High telemetry volume |

**Not implemented** — document for scale threshold.

---

## Performance score summary

| Area                   | Classification                  |
| ---------------------- | ------------------------------- |
| Connection pooling     | **Healthy**                     |
| Core FK indexes        | **Healthy**                     |
| JSON query performance | **Warning** — needs JSONB + GIN |
| Admin list pagination  | **Warning** — large limits      |
| Partitioning           | **N/A** — future                |
| Worker job locking     | **Warning** — optimize at scale |

See `PRODUCTION_DATABASE_SCORE.md` for overall readiness.
