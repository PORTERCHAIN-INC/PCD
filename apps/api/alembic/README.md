# Porterchain API migrations

Schema changes for Porterchain-owned **PostgreSQL only** (local, staging, production).

## Commands

From repo root:

```bash
# Apply migrations
pnpm db:migrate

# Create a new revision (after model changes)
pnpm db:revision -- -m "describe change"
```

From `apps/api` with venv active:

```bash
source .venv/bin/activate
export PYTHONPATH=src
alembic upgrade head
alembic revision --autogenerate -m "your message"
```

`DATABASE_URL` is read from `apps/api/.env` via `porterchain_api.config.Settings`.
Must use `postgresql+psycopg://` — SQLite is not supported.

## Policy

| Environment | Schema management |
|-------------|-------------------|
| **All environments** | **Alembic only** — run `alembic upgrade head` before API/worker start |

`init_db()` verifies PostgreSQL connectivity only. It does **not** create tables.

New tables in `billing_engine/` and `notification_engine/` are included in metadata via `alembic/env.py`.
