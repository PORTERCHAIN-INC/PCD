# Database Configuration Report

**Date:** July 1, 2026  
**Standard:** PostgreSQL 16 via `postgresql+psycopg://` for all Porterchain environments

---

## Configuration matrix

| Component                | Variable              | Standard value                                                            | Status             |
| ------------------------ | --------------------- | ------------------------------------------------------------------------- | ------------------ |
| Porterchain API          | `DATABASE_URL`        | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` | ✅ Standardized    |
| Shared platform settings | `database_url`        | Same PostgreSQL URL                                                       | ✅ Already correct |
| Fleetbase                | `DB_CONNECTION=mysql` | MySQL 8 — **unchanged**                                                   | ✅ Correct         |
| Redis                    | `REDIS_URL`           | `redis://localhost:6379/0`                                                | ✅ Unchanged       |

---

## File audit

| File                                                  | Before                         | After                      | Status             |
| ----------------------------------------------------- | ------------------------------ | -------------------------- | ------------------ |
| `apps/api/.env`                                       | `sqlite:///./porterchain.db`   | `postgresql+psycopg://...` | ✅ Updated         |
| `apps/api/.env.example`                               | SQLite                         | PostgreSQL                 | ✅ Updated         |
| `apps/api/src/porterchain_api/config.py`              | SQLite default                 | PostgreSQL + validator     | ✅ Updated         |
| `env/api.env.example`                                 | PostgreSQL                     | PostgreSQL                 | ✅ Already correct |
| `shared/python/porterchain_shared/config/settings.py` | PostgreSQL                     | PostgreSQL                 | ✅ Already correct |
| `infrastructure/deploy/docker-compose.prod.yml`       | PostgreSQL 16                  | PostgreSQL 16              | ✅ Already correct |
| `infrastructure/docker/docker-compose.yml`            | `porterchain-postgres` service | Unchanged                  | ✅ Correct         |
| `env/fleetbase.env.example`                           | `DB_CONNECTION=mysql`          | Unchanged                  | ✅ Correct         |

---

## Docker services

| Service                       | Image                | Port   | Purpose                |
| ----------------------------- | -------------------- | ------ | ---------------------- |
| `porterchain-postgres`        | `postgres:16-alpine` | `5432` | Porterchain domain DB  |
| `porterchain-fleetbase-mysql` | `mysql:8.0`          | `3307` | Fleetbase execution DB |
| `porterchain-redis`           | `redis:7`            | `6379` | Cache + queues         |

**Start:**

```bash
pnpm docker:up
```

---

## Engine configuration (`db.py`)

| Feature                          | Implemented |
| -------------------------------- | ----------- |
| PostgreSQL-only URL enforcement  | ✅          |
| Connection pool (`pool_size=10`) | ✅          |
| Overflow (`max_overflow=20`)     | ✅          |
| Pool pre-ping                    | ✅          |
| Pool recycle (30 min)            | ✅          |
| Alembic-only schema              | ✅          |
| SQLite branches removed          | ✅          |

---

## Driver

| Package           | Version | URL scheme              |
| ----------------- | ------- | ----------------------- |
| `psycopg[binary]` | ≥3.2.0  | `postgresql+psycopg://` |

Listed in `apps/api/pyproject.toml`.

---

## Scripts and tooling

| Script                                      | PostgreSQL                         |
| ------------------------------------------- | ---------------------------------- |
| `pnpm db:migrate`                           | ✅ Uses Alembic + `DATABASE_URL`   |
| `pnpm db:revision`                          | ✅ Autogenerate against PostgreSQL |
| `infrastructure/scripts/provision_admin.py` | ✅ Rejects SQLite                  |
| API seed scripts                            | ✅ Use `SessionLocal` → PostgreSQL |

---

## Worker

Worker processes consume Redis queues; database access goes through Porterchain API services or shared `database_url` from `PlatformSettings` (PostgreSQL).

---

## Remaining documentation gaps

| Document                                   | Action                                       |
| ------------------------------------------ | -------------------------------------------- |
| `FLEETBASE_DATABASE.md` line 306/314       | Update Porterchain column to PostgreSQL-only |
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | Update diagram label                         |

---

## Classification

| Area                            | Status                               |
| ------------------------------- | ------------------------------------ |
| Porterchain URL standardization | **Healthy**                          |
| Docker PostgreSQL service       | **Healthy**                          |
| Fleetbase MySQL isolation       | **Healthy**                          |
| Production compose              | **Healthy**                          |
| Doc consistency                 | **Warning** — minor stale references |
