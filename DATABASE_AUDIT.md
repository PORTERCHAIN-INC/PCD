# Database Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` §9 (Database ownership)

---

## Executive Verdict

| Area | Status |
|------|--------|
| PostgreSQL (production) | **PASS** |
| SQLite business logic | **PASS** (removed) |
| Alembic migrations | **PASS** (13 revisions) |
| Foreign keys (core) | **PASS** |
| Indexes / performance | **PARTIAL** |
| Redis | **PASS** |
| Fleetbase MySQL | **Separate** (execution engine) |

---

## PostgreSQL Enforcement

| Check | Implementation | Status |
|-------|----------------|--------|
| Startup rejection of SQLite | `db.py`, `config.py` validator | ✅ |
| No runtime DDL | `init_db()` = `SELECT 1` only | ✅ |
| Connection pool | `pool_pre_ping`, configurable size | ✅ |
| Alembic owns schema | 13 migrations through `n2o3p4q5r6s7` | ✅ |

**Latest migration:** `n2o3p4q5r6s7` — unique partial index on `orders.quote_id` (retail idempotency).

---

## Data Ownership (§9)

| Porterchain PostgreSQL | Fleetbase MySQL |
|------------------------|-----------------|
| Customers, merchants, quotes, drafts, bookings, orders | Drivers (operational), vehicles |
| Invoices, payments, CRM, support, notifications | Dispatch, routes, GPS, POD |
| Domain events, audit logs, pricing config | Fleet operations |

Commercial data stays in Porterchain unless Fleetbase requires a field for execution.

---

## Findings

### DB-M01 — Newer tables missing FKs (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | Route center and user_invitations migrations indexed but did not add FK constraints |
| **Affected Layer** | Repository |
| **Tables** | `route_center_plans`, `route_center_templates`, `user_invitations` |
| **Recommended Fix** | Alembic revision adding FKs to `drivers`, `vehicles`, `merchants`, `porterchain_users` |
| **Effort** | 4 hours |

### DB-M02 — Legacy timestamp defaults (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | Initial migration used SQLite-autogen `(CURRENT_TIMESTAMP)` |
| **Affected Layer** | Schema |
| **Recommended Fix** | Normalize to `now()` in future migrations |
| **Effort** | 2 hours |

### DB-M03 — JSONB rollout partial (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | CRM address/custom_fields migrated; other JSON columns remain `sa.JSON()` |
| **Affected Layer** | Performance |
| **Recommended Fix** | Continue per `POSTGRESQL_PERFORMANCE.md` |
| **Effort** | 1–2 days |

### DB-L01 — String UUID PKs (Low)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Root Cause** | Historical choice `String(36)` vs native `UUID` |
| **Recommended Fix** | Future migration if needed |
| **Effort** | 3+ days |

---

## Indexes (Highlights)

| Index | Table | Purpose |
|-------|-------|---------|
| `ix_orders_state_created_at` | orders | Control tower queries |
| `ix_orders_merchant_state` | orders | Merchant portal |
| `ix_domain_events_type_occurred` | domain_events | Event audit |
| `ix_fleetbase_sync_jobs_pending` | fleetbase_sync_jobs | Retry drain (partial) |
| GIN on CRM JSONB | crm_* | Search |
| `uq_orders_quote_id` | orders | **NEW** — one order per quote |

---

## Transactions

| Pattern | Status |
|---------|--------|
| Service-level `db.commit()` | ✅ Standard |
| Booking confirmation multi-entity | ⚠️ Partial commits before draft update (mitigated by BW-C01 fix) |
| Alembic transactional DDL | ✅ |

---

## Redis

| Use | Status |
|-----|--------|
| Event streams (`porterchain:events`) | ✅ |
| DLQ (`porterchain:events:dlq`) | ✅ |
| Idempotency keys | ✅ |
| Task queues (email, SMS, push, billing) | ✅ |
| Production requirement | `require_redis_for_production()` |

---

## SQLite Audit

| Item | Status |
|------|--------|
| Runtime SQLite | ❌ Blocked |
| `migrate_sqlite_to_postgres.py` | One-off ETL only |
| Test skip-if-sqlite | Acceptable |

**Verdict:** No SQLite business logic.

---

*Fleetbase MySQL audited separately in `FLEETBASE_AUDIT.md`.*
