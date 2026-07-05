# Porterchain API Migrations


**Type:** README
**masterrule:** [§21](../../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Schema changes for Porterchain-owned **PostgreSQL 16 only** (local, staging, production). SQLite is not supported.

---

## Current State

| Item | Value |
| ---- | ----- |
| Revisions | **13** |
| Head | `n2o3p4q5r6s7` (`orders_quote_id_unique`) |
| Driver | `postgresql+psycopg://` via `DATABASE_URL` in `apps/api/.env` |

---

## Commands

From repo root:

```bash
# Apply all pending migrations
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
alembic current   # show current revision
alembic history   # list revisions
```

`DATABASE_URL` is read from `apps/api/.env` via `porterchain_api.config.Settings`.

---

## Metadata Coverage

`alembic/env.py` imports all SQLAlchemy models so autogenerate sees the full schema:

- Core models (`models`, `identity_models`, `user_models`, …)
- Domain models (`merchant_models`, `driver_models`, `crm_models`, …)
- `billing_engine/models`
- `notification_engine/models`

New tables in billing or notification engines are included automatically when models are imported in `env.py`.

---

## Policy

| Rule | Detail |
| ---- | ------ |
| **Alembic only** | Run `alembic upgrade head` before API/worker start in every environment |
| **No `create_all`** | `init_db()` verifies PostgreSQL connectivity only — it does **not** create tables |
| **No SQLite** | `DATABASE_URL` must use `postgresql+psycopg://` |
| **One head** | Keep linear revision chain; resolve branches before deploy |

---

## Revision History (summary)

| Revision | Description |
| -------- | ----------- |
| `bd830e39ef4e` | Initial schema |
| `c4e8f1a2b3d0` | Support ticket enterprise |
| `d5f6a7b8c9d0` | Order source type, billing cycle |
| `e6f7a8b9c0d1` | Enterprise notifications |
| `f7a8b9c0d1e2` | Merchant webhook signing secret |
| `g8h9i0j1k2l3` | Merchant integrations gateway |
| `h9i0j1k2l3m4` | Driver shifts |
| `i0j1k2l3m4n5` | Route Center tables |
| `j1k2l3m4n5o6` | Porterchain users |
| `k2l3m4n5o6p7` | User invitations |
| `l3m4n5o6p7q8` | CRM task / Zoho calendar |
| `m1n2o3p4q5r6` | PostgreSQL performance indexes |
| `n2o3p4q5r6s7` | Orders quote_id unique (head) |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [../README.md](../README.md) | API setup |
| [../../../DATABASE_MIGRATION_PLAN.md](../../../DATABASE_MIGRATION_PLAN.md) | Migration strategy |
| [../../../ALEMBIC_VALIDATION.md](../../../ALEMBIC_VALIDATION.md) | Validation report |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../../masterrule.md](../../../masterrule.md) | Architecture SSOT |
| [../../../REPOSITORY_STRUCTURE.md](../../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

