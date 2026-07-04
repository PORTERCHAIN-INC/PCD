# Database Migration Plan

**Date:** July 1, 2026  
**Objective:** Porterchain on PostgreSQL only; Fleetbase remains MySQL  
**Authority:** [masterrule.md](./masterrule.md) §9

---

## Target architecture

```
Porterchain API / Worker  →  PostgreSQL 16 (postgresql+psycopg://)
Fleetbase Core            →  MySQL 8       (unchanged)
Redis                     →  Cache + queues (unchanged)
Fleetbase Adapter         →  Syncs PG ↔ Fleetbase HTTP ↔ MySQL
```

---

## Phase A — Preparation (completed)

- [x] Audit SQLite usage (`SQLITE_AUDIT.md`)
- [x] Classify table ownership (`DATABASE_OWNERSHIP_MATRIX.md`)
- [x] Fix PostgreSQL-incompatible SQL (`POSTGRESQL_COMPATIBILITY_REPORT.md`)
- [x] Standardize `DATABASE_URL` to `postgresql+psycopg://`
- [x] Remove SQLite from `db.py`, `config.py`
- [x] Implement connection pool

---

## Phase B — Schema migration (completed)

- [x] Validate Alembic on fresh PostgreSQL (`ALEMBIC_VALIDATION.md`)
- [x] Confirm 11 revisions apply cleanly
- [x] Test downgrade / upgrade cycle

**Command:**

```bash
pnpm docker:up          # starts porterchain-postgres
pnpm db:migrate         # alembic upgrade head
```

---

## Phase C — Data migration (optional — manual)

**Only required if existing `porterchain.db` SQLite data must be preserved.**

| Step | Action | Owner | Risk |
|------|--------|-------|------|
| C1 | Export SQLite to SQL/CSV | DBA | Low |
| C2 | Map types (JSON, timestamps) | Engineering | Medium |
| C3 | Import via `pgloader` or custom script | DBA | **High** — validate row counts |
| C4 | Reconcile sequences / UUIDs | Engineering | Medium |
| C5 | Run module validation (Phase 9) | QA | — |

**Stop rule:** If row count mismatch >0.1% or FK violations, **rollback** and do not cut over.

**Dev recommendation:** Use fresh PostgreSQL + seed scripts (`seed_crm.py`, `seed_dev_portal_users.py`) instead of SQLite import.

---

## Phase D — Environment cutover

| Environment | `DATABASE_URL` | Migration |
|-------------|----------------|-----------|
| Local | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` | `pnpm db:migrate` |
| CI | PostgreSQL service container | `alembic upgrade head` in pipeline |
| Production | Set in `docker-compose.prod.yml` | Pre-deploy migration job |

**Files updated:**

- `apps/api/.env` / `.env.example`
- `env/api.env.example` (already PostgreSQL)
- `shared/python/porterchain_shared/config/settings.py` (already PostgreSQL)
- `infrastructure/deploy/docker-compose.prod.yml` (already PostgreSQL)

---

## Phase E — Application validation (Phase 9)

Run after cutover:

1. Website quote → booking flow
2. Merchant portal CRUD
3. Admin modules (CRM, orders, finance, claims, support)
4. Driver API reads/writes
5. Fleetbase adapter sync (order create + status inbound)
6. Notification queue processing
7. Stripe webhook idempotency

Document results in `DATABASE_VALIDATION_REPORT.md`.

---

## Phase F — Cleanup

| Item | When |
|------|------|
| Delete `apps/api/porterchain.db` | After Phase E pass |
| Remove SQLite mentions from remaining docs | After Phase E pass |
| Add CI PostgreSQL job | Before production deploy |

---

## Rollback plan

| Scenario | Action |
|----------|--------|
| Alembic migration fails | `alembic downgrade -1`; fix revision; retry |
| App fails on PostgreSQL | Revert code deploy; PostgreSQL data retained |
| Data migration corrupt | Restore PostgreSQL from pre-migration snapshot; do not use SQLite in production |

**SQLite rollback is NOT supported** after this standardization — PostgreSQL is the only Porterchain store going forward.

---

## Timeline estimate

| Phase | Duration |
|-------|----------|
| A–B (code + schema) | ✅ Complete |
| C (data migration) | 1–3 days if needed |
| D (env cutover) | 1 hour per environment |
| E (validation) | 1–2 days |
| F (cleanup) | 2 hours |

---

## Fleetbase — no changes

- MySQL container: `porterchain-fleetbase-mysql` / `porterchain-mysql`
- Laravel migrations: unchanged
- Adapter sync: unchanged

Do **not** attempt to consolidate Fleetbase MySQL into Porterchain PostgreSQL.
