# Database Configuration Report

**Last verified:** 2026-07-04  
**Standard:** PostgreSQL 16 via `postgresql+psycopg://` for all Porterchain environments

> **Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md) · **Env reference:** [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)

---

## Configuration matrix

| Component | Variable | Standard value | Status |
| --------- | -------- | -------------- | ------ |
| Porterchain API | `DATABASE_URL` | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` | ✅ |
| Shared platform settings | `database_url` | Same PostgreSQL URL | ✅ |
| Fleetbase | `DB_CONNECTION=mysql` | MySQL 8 — separate stack | ✅ |
| Redis | `REDIS_URL` | `redis://localhost:6379/0` | ✅ |

---

## File audit (July 2026)

| File | Status |
| ---- | ------ |
| `apps/api/.env.example` | ✅ PostgreSQL |
| `apps/api/src/porterchain_api/config.py` | ✅ PostgreSQL default + SQLite validator |
| `apps/api/src/porterchain_api/db.py` | ✅ Pool + PostgreSQL guard |
| `env/api.env.example` | ✅ PostgreSQL |
| `shared/python/porterchain_shared/config/settings.py` | ✅ PostgreSQL |
| `infrastructure/docker/docker-compose.yml` | ✅ `porterchain-postgres` service |
| `env/fleetbase.env.example` | ✅ MySQL for Fleetbase |

---

## Docker services

| Service | Image | Host port | Profile |
| ------- | ----- | --------- | ------- |
| `porterchain-postgres` | `postgres:16-alpine` | `127.0.0.1:5432` | `core` |
| `porterchain-mysql` | `mysql:8.0` | `127.0.0.1:3306` | `core` / `fleetbase` |
| `porterchain-redis` | `redis:7` | `6379` | `core` |
| `porterchain-fleetbase-mysql` | MySQL 8 | `127.0.0.1:3307` | Fleetbase install stack |

**Start Porterchain DB:**

```bash
pnpm docker:up    # postgres + redis (+ mysql in core profile)
pnpm db:migrate
```

Fleetbase MySQL is a **separate** compose project — see [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md).

---

## Engine configuration (`db.py`)

| Feature | Implemented |
| ------- | ----------- |
| PostgreSQL-only URL enforcement | ✅ |
| Connection pool (`pool_size=10`) | ✅ |
| Overflow (`max_overflow=20`) | ✅ |
| Pool pre-ping | ✅ |
| Pool recycle (30 min) | ✅ |
| Alembic-only schema | ✅ |
| SQLite branches removed | ✅ |

---

## Driver

| Package | Version | URL scheme |
| ------- | ------- | ---------- |
| `psycopg[binary]` | ≥3.2.0 | `postgresql+psycopg://` |

Listed in `apps/api/pyproject.toml`.

---

## Scripts and tooling

| Command / script | Purpose |
| ---------------- | ------- |
| `pnpm db:migrate` | Alembic upgrade head |
| `pnpm db:revision` | Autogenerate migration |
| `apps/api/scripts/validate_postgres_modules.py` | Module/table smoke check |
| `infrastructure/scripts/provision_admin.py` | Admin bootstrap (PostgreSQL) |

---

## Worker

`apps/worker/` consumes Redis queues. Database access goes through Porterchain API services or shared `database_url` from `PlatformSettings` (PostgreSQL).

---

## Classification

| Area | Status |
| ---- | ------ |
| Porterchain URL standardization | **Healthy** |
| Docker PostgreSQL service | **Healthy** |
| Fleetbase MySQL isolation | **Healthy** |
| Production compose | **Healthy** |
