# Database Audit — Porterchain Platform

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §9 (Database ownership)  
**Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

---

## Executive verdict

| Area                         | Status                                       |
| ---------------------------- | -------------------------------------------- |
| PostgreSQL (production path) | **PASS**                                     |
| SQLite business logic        | **PASS** (blocked at startup)                |
| Alembic migrations           | **PASS** (13 revisions, head `n2o3p4q5r6s7`) |
| Foreign keys (core)          | **PASS**                                     |
| Indexes / performance        | **PARTIAL** — JSONB rollout ongoing          |
| Redis                        | **PASS**                                     |
| Fleetbase MySQL              | **Separate** — HTTP adapter only             |

---

## PostgreSQL enforcement

| Check                       | Implementation                         | Status |
| --------------------------- | -------------------------------------- | ------ |
| Startup rejection of SQLite | `db.py`, `config.py` validator         | ✅     |
| No runtime DDL              | `init_db()` = `SELECT 1` only          | ✅     |
| Connection pool             | `pool_pre_ping`, size 10 + overflow 20 | ✅     |
| Alembic owns schema         | 13 migrations through `n2o3p4q5r6s7`   | ✅     |

**Latest migration:** `n2o3p4q5r6s7` — partial unique index on `orders.quote_id` (retail idempotency).

**Performance migration:** `m1n2o3p4q5r6` — CRM JSONB + GIN indexes.

---

## Data ownership (§9)

| Porterchain PostgreSQL                                 | Fleetbase MySQL                 |
| ------------------------------------------------------ | ------------------------------- |
| Customers, merchants, quotes, drafts, bookings, orders | Drivers (operational), vehicles |
| Invoices, payments, CRM, support, notifications        | Dispatch, routes, GPS, POD      |
| Domain events, audit logs, pricing config              | Fleet operations                |

Commercial data stays in Porterchain unless Fleetbase requires a field for execution.

---

## Findings

### DB-M01 — Newer tables missing FKs (Medium)

| Field      | Value                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------- |
| **Tables** | `route_center_plans`, `route_center_templates`, `user_invitations`                                |
| **Issue**  | Indexed columns without FK constraints to `drivers`, `vehicles`, `merchants`, `porterchain_users` |
| **Fix**    | Alembic revision adding FKs                                                                       |

### DB-M02 — Legacy timestamp defaults (Medium)

Initial migration used SQLite-autogen `(CURRENT_TIMESTAMP)`. Normalize to `now()` in future migrations.

### DB-M03 — JSONB rollout partial (Medium)

CRM `address` / `custom_fields` migrated in `m1n2o3p4q5r6`. Other JSON columns may remain `sa.JSON()`.

### DB-L01 — String UUID PKs (Low)

Historical `String(36)` vs native PostgreSQL `UUID` — acceptable; migrate only if needed.

---

## Indexes (highlights)

| Index                            | Table               | Purpose               |
| -------------------------------- | ------------------- | --------------------- |
| `ix_orders_state_created_at`     | orders              | Control tower         |
| `ix_orders_merchant_state`       | orders              | Merchant portal       |
| `ix_domain_events_type_occurred` | domain_events       | Event audit           |
| `ix_fleetbase_sync_jobs_pending` | fleetbase_sync_jobs | Retry drain (partial) |
| GIN on CRM JSONB                 | crm_*               | Search                |
| `uq_orders_quote_id`             | orders              | One order per quote   |

---

## Transactions

| Pattern                           | Status             |
| --------------------------------- | ------------------ |
| Service-level `db.commit()`       | ✅ Standard        |
| Booking confirmation multi-entity | ⚠️ Review per flow |
| Alembic transactional DDL         | ✅                 |

---

## Redis

| Use                                     | Status                           |
| --------------------------------------- | -------------------------------- |
| Event streams (`porterchain:events`)    | ✅                               |
| DLQ (`porterchain:events:dlq`)          | ✅                               |
| Idempotency keys                        | ✅                               |
| Task queues (email, SMS, push, billing) | ✅                               |
| Production requirement                  | `require_redis_for_production()` |

---

## SQLite audit

| Item                            | Status                                   |
| ------------------------------- | ---------------------------------------- |
| Runtime SQLite                  | ❌ Blocked                               |
| `migrate_sqlite_to_postgres.py` | One-off ETL only (if legacy data exists) |
| Test skip-if-sqlite             | Acceptable                               |

**Verdict:** No SQLite business logic in production path.

---

## Validation tooling

```bash
pnpm db:migrate
cd apps/api && python scripts/validate_postgres_modules.py
```

---

## Related

| Document                                                         | Purpose                   |
| ---------------------------------------------------------------- | ------------------------- |
| [DATABASE_VALIDATION_REPORT.md](./DATABASE_VALIDATION_REPORT.md) | Phase validation snapshot |
| [FLEETBASE_DATABASE.md](./FLEETBASE_DATABASE.md)                 | Fleetbase MySQL reference |
