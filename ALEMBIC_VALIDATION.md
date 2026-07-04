# Alembic Validation Report

**Date:** July 1, 2026  
**Database:** `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain`  
**Container:** `porterchain-postgres` (PostgreSQL 16)

---

## Policy (post-standardization)

| Rule                                             | Status                          |
| ------------------------------------------------ | ------------------------------- |
| Alembic is the **only** schema management system | ✅ Enforced                     |
| `create_all()` removed from `init_db()`          | ✅ Removed                      |
| SQLite bootstrap removed                         | ✅ Removed                      |
| `DATABASE_URL` must be PostgreSQL                | ✅ Validated at config + engine |

---

## Migration chain

| Revision       | Description                       |
| -------------- | --------------------------------- |
| `bd830e39ef4e` | initial_schema                    |
| `c4e8f1a2b3d0` | Support ticket enterprise         |
| `d5f6a7b8c9d0` | Order source/type, billing cycle  |
| `e6f7a8b9c0d1` | Enterprise notifications          |
| `f7a8b9c0d1e2` | Merchant webhook signing secret   |
| `g8h9i0j1k2l3` | Merchant integrations gateway     |
| `h9i0j1k2l3m4` | Driver shifts                     |
| `i0j1k2l3m4n5` | Route Center tables               |
| `j1k2l3m4n5o6` | porterchain_users                 |
| `k2l3m4n5o6p7` | user_invitations                  |
| `l3m4n5o6p7q8` | CRM task Zoho calendar (**head**) |

**Total revisions:** 11

---

## Validation tests

| Test                   | Command                              | Result                                     |
| ---------------------- | ------------------------------------ | ------------------------------------------ |
| Fresh database upgrade | `alembic upgrade head`               | ✅ Pass — all 11 revisions applied (~4.8s) |
| Current revision       | `alembic current`                    | ✅ `l3m4n5o6p7q8 (head)`                   |
| Downgrade one step     | `alembic downgrade -1`               | ✅ Pass — CRM Zoho columns removed         |
| Forward re-upgrade     | `alembic upgrade head`               | ✅ Pass                                    |
| Dialect                | Alembic log                          | ✅ `Context impl PostgresqlImpl`           |
| Startup connectivity   | `init_db()`                          | ✅ Pass — `SELECT 1`                       |
| ORM smoke query        | `SELECT COUNT(*) FROM crm_companies` | ✅ Pass                                    |

---

## Dependencies removed

| Former dependency                       | Replacement                                                  |
| --------------------------------------- | ------------------------------------------------------------ |
| `Base.metadata.create_all()` on startup | `alembic upgrade head` in deploy / `pnpm db:migrate` locally |
| SQLite PRAGMA column patches            | Proper Alembic revisions for all schema changes              |
| SQLite Alembic stamp hack               | Standard migration history from empty DB                     |

---

## Deploy checklist

```bash
# 1. Ensure PostgreSQL is running
docker start porterchain-postgres   # or pnpm docker:up

# 2. Set DATABASE_URL in apps/api/.env
DATABASE_URL=postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain

# 3. Apply migrations
pnpm db:migrate

# 4. Start API
pnpm dev:api
```

Production (`infrastructure/deploy/docker-compose.prod.yml`) already sets PostgreSQL URL and depends on `postgres` service.

---

## Data migration (SQLite → PostgreSQL)

**Not automated** — manual migration required if existing `porterchain.db` data must be preserved.

| Approach                             | Risk   | Recommendation                     |
| ------------------------------------ | ------ | ---------------------------------- |
| Fresh PostgreSQL + seed scripts      | Low    | ✅ Dev/staging                     |
| `pgloader sqlite:// → postgresql://` | Medium | Staging validation required        |
| Custom ETL per table                 | High   | Production only with rollback plan |

**Rule:** If migration introduces data-loss risk, stop and document — do not proceed automatically. See `DATABASE_MIGRATION_PLAN.md`.

---

## Status

| Check                    | Classification                            |
| ------------------------ | ----------------------------------------- |
| Fresh DB migration       | **Healthy**                               |
| Rollback / forward       | **Healthy**                               |
| SQLite dependency        | **Healthy** — removed                     |
| Automated data migration | **Warning** — not implemented (by design) |
