# Alembic Validation Report

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Database:** `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain`  
**Container:** `porterchain-postgres` (PostgreSQL 18)

> **Commands:** [apps/api/alembic/README.md](./apps/api/alembic/README.md) · **Migration plan:** [DATABASE_MIGRATION_PLAN.md](./DATABASE_MIGRATION_PLAN.md)

---

## Policy

| Rule                                             | Status                    |
| ------------------------------------------------ | ------------------------- |
| Alembic is the **only** schema management system | ✅ Enforced               |
| `create_all()` removed from `init_db()`          | ✅                        |
| SQLite bootstrap removed                         | ✅                        |
| `DATABASE_URL` must be PostgreSQL                | ✅ Config + engine guards |

---

## Migration chain (13 revisions)

| Revision       | Description                                       |
| -------------- | ------------------------------------------------- |
| `bd830e39ef4e` | initial_schema                                    |
| `c4e8f1a2b3d0` | Support ticket enterprise                         |
| `d5f6a7b8c9d0` | Order source/type, billing cycle                  |
| `e6f7a8b9c0d1` | Enterprise notifications                          |
| `f7a8b9c0d1e2` | Merchant webhook signing secret                   |
| `g8h9i0j1k2l3` | Merchant integrations gateway                     |
| `h9i0j1k2l3m4` | Driver shifts                                     |
| `i0j1k2l3m4n5` | Route Center tables                               |
| `j1k2l3m4n5o6` | porterchain_users                                 |
| `k2l3m4n5o6p7` | user_invitations                                  |
| `l3m4n5o6p7q8` | CRM task Zoho calendar                            |
| `m1n2o3p4q5r6` | CRM JSONB + performance indexes                   |
| `n2o3p4q5r6s7` | Partial unique index `orders.quote_id` (**head**) |

Path: `apps/api/alembic/versions/`

---

## Validation tests

| Test                   | Command                                       | Expected                  |
| ---------------------- | --------------------------------------------- | ------------------------- |
| Fresh database upgrade | `pnpm db:migrate`                             | All 13 revisions apply    |
| Current revision       | `cd apps/api && alembic current`              | `n2o3p4q5r6s7 (head)`     |
| Downgrade one step     | `alembic downgrade -1`                        | Reversible                |
| Forward re-upgrade     | `alembic upgrade head`                        | Pass                      |
| Dialect                | Alembic log                                   | `PostgresqlImpl`          |
| Startup connectivity   | `init_db()`                                   | `SELECT 1`                |
| Module smoke           | `python scripts/validate_postgres_modules.py` | All module tables present |

---

## Dependencies removed

| Former dependency                       | Replacement                    |
| --------------------------------------- | ------------------------------ |
| `Base.metadata.create_all()` on startup | `pnpm db:migrate` / deploy job |
| SQLite PRAGMA column patches            | Alembic revisions              |
| SQLite Alembic stamp hack               | Standard chain from empty DB   |

---

## Deploy checklist

```bash
pnpm docker:up
# DATABASE_URL in apps/api/.env → postgresql+psycopg://...
pnpm db:migrate
pnpm dev:api
```

Production: `infrastructure/deploy/docker-compose.prod.yml` — PostgreSQL service + migration before API start.

---

## Data migration (SQLite → PostgreSQL)

**Not automated in Alembic** — optional ETL:

```bash
cd apps/api
python scripts/migrate_sqlite_to_postgres.py --sqlite ./porterchain.db --dry-run
```

| Approach                        | Risk   | Recommendation              |
| ------------------------------- | ------ | --------------------------- |
| Fresh PostgreSQL + seeds        | Low    | ✅ Dev/staging default      |
| `migrate_sqlite_to_postgres.py` | Medium | Legacy data only            |
| `pgloader`                      | Medium | Staging validation required |

---

## Status

| Check                        | Classification                     |
| ---------------------------- | ---------------------------------- |
| Fresh DB migration (13 revs) | **Healthy**                        |
| Rollback / forward           | **Healthy**                        |
| SQLite dependency            | **Healthy** — removed from runtime |
| Automated data migration     | **N/A** — optional script only     |

---

## Governance

| Document                                                                | Role              |
| ----------------------------------------------------------------------- | ----------------- |
| [masterrule.md](masterrule.md)                                          | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](docs/archive/reports-2026-08/CTO_AUDIT_REPORT.md) | Doc vs code audit |
