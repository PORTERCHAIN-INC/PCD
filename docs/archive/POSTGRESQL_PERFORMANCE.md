# PostgreSQL Performance Report

**Last verified:** 2026-07-04  
**Scope:** Porterchain PostgreSQL schema and query patterns  
**Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

> **Compatibility:** [POSTGRESQL_COMPATIBILITY_REPORT.md](./POSTGRESQL_COMPATIBILITY_REPORT.md) · **Scorecard:** [PRODUCTION_DATABASE_SCORE.md](./PRODUCTION_DATABASE_SCORE.md)

---

## Connection pool (implemented)

| Setting | Value | Location |
| ------- | ----- | -------- |
| `pool_size` | 10 | `apps/api/src/porterchain_api/db.py` |
| `max_overflow` | 20 | `db.py` |
| `pool_timeout` | 30s | `config.py` / `db.py` |
| `pool_recycle` | 1800s | `db.py` |
| `pool_pre_ping` | true | `db.py` |

**Classification:** **Healthy** for local/single-node API. Tune `pool_size` × Uvicorn workers under load test.

---

## Implemented indexes (Alembic)

### Initial schema + module migrations

FK columns, status fields, sync job keys, audit indexes from `bd830e39ef4e` through `l3m4n5o6p7q8`.

### Revision `m1n2o3p4q5r6` ✅

| Index | Table | Purpose |
| ----- | ----- | ------- |
| `ix_crm_companies_address_gin` | crm_companies | JSONB city/province search |
| `ix_crm_leads_address_gin` | crm_leads | Faceted address search |
| `ix_crm_leads_custom_fields_gin` | crm_leads | Custom field search |
| `ix_orders_state_created_at` | orders | Admin / control tower |
| `ix_orders_merchant_state` | orders | Merchant portal lists |
| `ix_domain_events_type_occurred` | domain_events | Event diagnostics |
| `ix_fleetbase_sync_jobs_pending` | fleetbase_sync_jobs | Partial — pending/retrying dequeue |

### Revision `n2o3p4q5r6s7` ✅

| Index | Table | Purpose |
| ----- | ----- | ------- |
| `uq_orders_quote_id` | orders | Partial unique — retail checkout idempotency |

---

## Still recommended (not implemented)

| Table | Index | Priority |
| ----- | ----- | -------- |
| `notification_records` | `(status, created_at)` | Medium |
| `admin_audit_logs` | `(resource_type, resource_id, created_at DESC)` | Medium |
| `booking_drafts` | unique `(session_id)` | Medium |
| Remaining JSON columns | JSONB + GIN where filtered | Medium |

---

## JSON / JSONB queries

| Area | Status |
| ---- | ------ |
| CRM `address` / `custom_fields` | ✅ JSONB + GIN (`m1n2o3p4q5r6`) |
| Route `stops`, plan JSON | ⚠️ JSON — avoid heavy in-JSON filters |
| Helpers | `db_json.json_text()` for PostgreSQL-safe extraction |

---

## Slow query risks

| Pattern | Service | Mitigation |
| ------- | ------- | ---------- |
| Large admin list limits | Admin grids | Paginate default 100, max 500 |
| CRM multi-OR + JSON search | `crm_sales_service` | GIN indexes applied; monitor `EXPLAIN` |
| Long report generation | Reports | Redis `reports` queue — avoid long PG transactions |

---

## Transactions and locks

| Pattern | Status | Future |
| ------- | ------ | ------ |
| Service-level commits | ✅ Healthy — keep short | — |
| Stripe webhook + booking | ⚠️ Verify rollback paths | — |
| Fleetbase sync job claim | ⚠️ | `FOR UPDATE SKIP LOCKED` at worker scale |

---

## Partitioning (future)

| Table | When |
| ----- | ---- |
| `domain_events` | >10M rows — monthly range |
| `admin_audit_logs` | >5M rows |
| `notification_delivery_logs` | >10M rows + archive |
| `driver_location_pings` | High telemetry — partition or Redis geo |

Not implemented — document for scale threshold.

---

## Performance score summary

| Area | Classification |
| ---- | -------------- |
| Connection pooling | **Healthy** |
| Core + CRM indexes | **Healthy** — `m1` + `n2` applied |
| Remaining JSON columns | **Warning** — partial JSONB rollout |
| Admin list pagination | **Warning** — review large limits |
| Worker job locking | **Warning** — optimize at scale |
| Partitioning | **N/A** — future |
