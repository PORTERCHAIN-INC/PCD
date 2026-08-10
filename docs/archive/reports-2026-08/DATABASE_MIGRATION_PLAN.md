# Database Migration Plan

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Objective:** Porterchain on PostgreSQL only; Fleetbase remains MySQL  
**Authority:** [masterrule.md](./masterrule.md) §9

> **Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md) · **Alembic:** [ALEMBIC_VALIDATION.md](./ALEMBIC_VALIDATION.md) · **Archive:** [docs/archive/README.md#database](./docs/archive/README.md#database)

---

## Target architecture

```
Porterchain API / Worker  →  PostgreSQL 16 (postgresql+psycopg://)
Fleetbase Core            →  MySQL 8       (unchanged)
Redis                     →  Cache + queues (unchanged)
Fleetbase Adapter         →  HTTP sync (no direct MySQL from Porterchain API)
```

---

## Phase A — Preparation ✅ complete

- [x] Audit SQLite usage ([docs/archive/SQLITE_AUDIT.md](./docs/archive/SQLITE_AUDIT.md))
- [x] Classify table ownership ([DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md))
- [x] Fix PostgreSQL-incompatible SQL ([docs/archive/POSTGRESQL_COMPATIBILITY_REPORT.md](./docs/archive/POSTGRESQL_COMPATIBILITY_REPORT.md))
- [x] Standardize `DATABASE_URL` to `postgresql+psycopg://`
- [x] Remove SQLite from `db.py`, `config.py`
- [x] Implement connection pool

---

## Phase B — Schema migration ✅ complete

- [x] Validate Alembic on fresh PostgreSQL ([ALEMBIC_VALIDATION.md](./ALEMBIC_VALIDATION.md))
- [x] **13 revisions** apply cleanly (head `n2o3p4q5r6s7`)
- [x] Performance/JSONB revision `m1n2o3p4q5r6` applied
- [x] Retail idempotency index `n2o3p4q5r6s7` applied

```bash
pnpm docker:up          # porterchain-postgres
pnpm db:migrate         # alembic upgrade head
```

---

## Phase C — Data migration (optional — manual)

**Only if legacy `porterchain.db` SQLite data must be preserved.**

| Step | Action             | Tool                                                       |
| ---- | ------------------ | ---------------------------------------------------------- |
| C1   | Dry-run row counts | `apps/api/scripts/migrate_sqlite_to_postgres.py --dry-run` |
| C2   | Execute import     | Same script with `--execute`                               |
| C3   | Validate           | `python scripts/validate_postgres_modules.py`              |

**Dev recommendation:** Fresh PostgreSQL + seed scripts:

- `scripts/seed_crm.py`
- `scripts/seed_dev_portal_users.py`
- `scripts/seed_local_dev.py`

**Stop rule:** Row count mismatch >0.1% or FK violations → rollback, do not cut over.

---

## Phase D — Environment cutover ✅ complete (local/dev)

| Environment | `DATABASE_URL`                                                            | Migration                                                       |
| ----------- | ------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Local       | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` | `pnpm db:migrate`                                               |
| CI          | PostgreSQL service container                                              | `alembic upgrade head` (recommended — not yet in all workflows) |
| Production  | `infrastructure/deploy/docker-compose.prod.yml`                           | Pre-deploy migration job                                        |

---

## Phase E — Application validation ⚠️ partial

Schema validation: ✅ ([docs/archive/DATABASE_VALIDATION_REPORT.md](./docs/archive/DATABASE_VALIDATION_REPORT.md))

Runtime E2E (manual QA pending):

1. Website quote → booking flow
2. Merchant portal CRUD
3. Admin modules (CRM, orders, finance, claims, support)
4. Driver API reads/writes
5. Fleetbase adapter sync
6. Notification queue processing
7. Stripe webhook idempotency

---

## Phase F — Cleanup ⚠️ partial

| Item                                        | Status                                      |
| ------------------------------------------- | ------------------------------------------- |
| Delete `apps/api/porterchain.db` if present | Manual — safe after PG validated            |
| Remove SQLite mentions from docs            | Ongoing (Groups 20–21, final grep Group 43) |
| CI PostgreSQL + pytest                      | Pending                                     |

---

## Rollback plan

| Scenario                | Action                                                      |
| ----------------------- | ----------------------------------------------------------- |
| Alembic migration fails | `alembic downgrade -1`; fix revision; retry                 |
| App fails on PostgreSQL | Revert code deploy; PostgreSQL data retained                |
| Data migration corrupt  | Restore PG snapshot; **do not** revert to SQLite production |

**SQLite rollback is NOT supported** — PostgreSQL is the only Porterchain store.

---

## Fleetbase — no changes

- MySQL: core compose `:3306` or Fleetbase stack `:3307`
- Laravel migrations: Fleetbase-owned
- Do **not** consolidate Fleetbase MySQL into Porterchain PostgreSQL

---

## Timeline

| Phase               | Status                                      |
| ------------------- | ------------------------------------------- |
| A–B (code + schema) | ✅ Complete                                 |
| C (data migration)  | Optional — 1–3 days if legacy SQLite exists |
| D (local env)       | ✅ Complete                                 |
| E (validation)      | ⚠️ Schema done; E2E manual                  |
| F (cleanup)         | ⚠️ Partial                                  |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
