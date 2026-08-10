# Porterchain — Database Architecture

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-08

**Status:** Implemented — PostgreSQL 18 + Alembic in `apps/api/`

> **Ownership:** [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) · **Migrations:** [README.md](apps/api/alembic/README.md) · **Domain:** [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)

---

## Data store summary

| Store                  | Engine        | Purpose                                | Owner               | Access from Porterchain                  |
| ---------------------- | ------------- | -------------------------------------- | ------------------- | ---------------------------------------- |
| **Porterchain API DB** | PostgreSQL 18 | Commercial domain, CRM, billing, admin | Porterchain API     | SQLAlchemy + Alembic                     |
| **Fleetbase DB**       | MySQL 8       | Dispatch, GPS, routes, POD             | Fleetbase (Laravel) | **HTTP adapter only** — never direct SQL |
| **Redis**              | Redis 7       | Queues, cache, event streams           | Shared infra        | `redis` client / worker                  |

Auth identity: **Clerk** (external). User mirrors live in PostgreSQL (`porterchain_users`, portal-specific link tables).

---

## Porterchain PostgreSQL (canonical)

### Connection

| Setting   | Local dev                                                                 |
| --------- | ------------------------------------------------------------------------- |
| URL       | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` |
| Env var   | `DATABASE_URL`                                                            |
| Container | `porterchain-postgres` (`postgres:16-alpine`)                             |
| Driver    | `psycopg` ≥3.2 (`postgresql+psycopg://`)                                  |

### ORM layout

| Module                                    | Tables (examples)                                            |
| ----------------------------------------- | ------------------------------------------------------------ |
| `models.py`                               | `customers`, `quotes`, `bookings`, `orders`, `domain_events` |
| `merchant_models.py`                      | `merchants`, `merchant_api_keys`, `merchant_webhooks`        |
| `crm_models.py`                           | `crm_leads`, `crm_companies`, `crm_deals`                    |
| `admin_models.py`                         | `drivers`, `pricing_tariffs`, `route_center_plans`           |
| `driver_models.py`                        | `driver_shifts`, `driver_location_pings`                     |
| `booking_draft_models.py`                 | `booking_drafts`, `booking_draft_audits`                     |
| `notification_engine/models.py`           | `notification_records`, `notification_devices`               |
| `billing_engine/models.py`                | `billing_ledger_entries`                                     |
| `fleetbase_models.py`                     | `fleetbase_sync_jobs`, `fleetbase_sync_audit`                |
| `user_models.py` / `invitation_models.py` | `porterchain_users`, `user_invitations`                      |

**~68 application tables** + `alembic_version`. Full list: [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md).

### Schema rules

- **Alembic-only DDL** — `init_db()` runs `SELECT 1` only; no runtime `create_all`
- **SQLite blocked** — `config.py` validator + `db.py` guard reject `sqlite://`
- **Fleetbase mirror** — `orders`, `drivers`, `vehicles` in PostgreSQL; execution state synced via adapter
- **Commercial authority** — pricing, invoices, contracts, CRM stay in PostgreSQL

### Migrations

| Item             | Path                                                       |
| ---------------- | ---------------------------------------------------------- |
| Alembic config   | `apps/api/alembic.ini`                                     |
| Revisions        | `apps/api/alembic/versions/` (13 revisions)                |
| Head (July 2026) | `n2o3p4q5r6s7` — partial unique index on `orders.quote_id` |
| Apply            | `pnpm db:migrate`                                          |

---

## Fleetbase MySQL (execution — do not modify from Porterchain)

| Context                                      | Host port        | Container                     |
| -------------------------------------------- | ---------------- | ----------------------------- |
| Core compose profile                         | `127.0.0.1:3306` | `porterchain-mysql`           |
| Fleetbase stack (`pnpm docker:fleetbase:up`) | `127.0.0.1:3307` | `porterchain-fleetbase-mysql` |

Schema owned by Fleetbase Laravel migrations. Porterchain reads/writes via `services/fleetbase-adapter/` only.

See [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) and [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md).

---

## Redis usage

| Use case           | Pattern                                                               |
| ------------------ | --------------------------------------------------------------------- |
| Worker task queues | `porterchain:queue:*` (email, sms, push, dispatch, billing, webhooks) |
| Event bus          | Streams + DLQ (`porterchain:events`, `porterchain:events:dlq`)        |
| Idempotency        | Short-TTL keys in API handlers                                        |
| Cache              | Application-specific TTL keys                                         |

Fleetbase uses its own Redis instance inside the Fleetbase Docker stack.

---

## Data flow

```
Website / portals / mobile
        │
        ▼
Porterchain API (:8001)
        │
        ├── PostgreSQL — quotes, bookings, orders, merchants, CRM, billing
        ├── Redis — queues, events, cache
        └── Fleetbase adapter (HTTP)
                    │
                    ▼
            Fleetbase MySQL — dispatch execution, GPS, POD
```

Merchant onboarding, contracts, and billing terms are **PostgreSQL + Clerk** — not a separate Laravel DB in this monorepo.

---

## Read replica (analytics — §3.4.4, DD-19)

**Phase A (now):** All API and worker traffic uses the **primary** Postgres connection (`DATABASE_URL`). OLTP queries, Fleetbase sync jobs, and portal dashboards hit the primary.

**Phase B/C (growth):** When analytics/reporting load competes with dispatch OLTP:

| Role             | Connection                                   | Workloads                                                                                  |
| ---------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Primary**      | `DATABASE_URL`                               | Writes, booking, dispatch, billing, webhooks, Fleetbase sync                               |
| **Read replica** | `DATABASE_URL_REPLICA` (read-only, optional) | Heavy aggregates, CRM reports, merchant `reporting_metrics`, future `analytics_engine` ETL |

### Configuration (when replica provisioned)

```bash
# Primary — required (read/write)
DATABASE_URL=postgresql+psycopg://user:pass@primary-host:5432/porterchain?sslmode=require

# Replica — optional; analytics code paths only
DATABASE_URL_REPLICA=postgresql+psycopg://user:pass@replica-host:5432/porterchain?sslmode=require
```

**Rules:**

- Never run Alembic migrations against the replica.
- Replica lag >30s → fall back to primary for time-sensitive admin dashboards.
- Managed Postgres (DigitalOcean, RDS) — enable replica in console; see [ADR-012 Phase C](./docs/architecture/ADR-012-scaling.md).

Until `DATABASE_URL_REPLICA` is set, `merchant_engine/reporting_metrics.py` and admin report endpoints continue using the primary pool (acceptable at Phase A scale).

---

## Managed Postgres (production — §3.4.7, DD-19)

**Phase A (current prod):** Single Postgres container in `docker-compose.prod.yml` (`pcd-postgres`, Postgres 18).

**Phase B (managed primary):** Move OLTP to DigitalOcean Managed PostgreSQL 18+ before scaling past 2 API replicas.

| Step | Action                                                                                                |
| ---- | ----------------------------------------------------------------------------------------------------- |
| 1    | Provision **Managed PostgreSQL** (primary + optional standby) in DO console                           |
| 2    | `pg_dump` from droplet `pcd-postgres` → restore to managed cluster (`?sslmode=require`)               |
| 3    | Set Doppler / droplet `DATABASE_URL` on **api** + **worker** to managed primary URI                   |
| 4    | Run migrations once: `docker compose exec api python scripts/repair_and_migrate.py`                   |
| 5    | Maintenance window cutover — stop compose `postgres` service after smoke (`pnpm validate:p0:prod` G1) |
| 6    | Enable **read replica** in managed console; set `DATABASE_URL_REPLICA` (read-only URI)                |

**Code paths:**

| Variable               | Consumer                | Purpose                              |
| ---------------------- | ----------------------- | ------------------------------------ |
| `DATABASE_URL`         | `db.engine`, `get_db()` | All writes + OLTP reads              |
| `DATABASE_URL_REPLICA` | `db.get_read_db()`      | Analytics/reporting reads (optional) |

Replica pool defaults: `pool_size=5`, `max_overflow=10` — smaller than primary to cap analytics load.

**Analytics off primary:** CRM reports, merchant `reporting_metrics`, and future `analytics_engine` ETL should use `Depends(get_read_db)` once replica is provisioned. Until then, `get_read_db()` falls back to primary.

See [infrastructure/deploy/README.md](./infrastructure/deploy/README.md) and [ADR-012 Phase B](./docs/architecture/ADR-012-scaling.md).

---

## Backup (production target)

| Database        | Method                        | Retention |
| --------------- | ----------------------------- | --------- |
| PostgreSQL      | `pg_dump` + WAL / managed RDS | 30 days   |
| Fleetbase MySQL | `mysqldump` / managed         | 30 days   |
| Redis           | AOF + snapshot                | 7 days    |

---

## Related documents

| Document                                                                                   | Purpose                    |
| ------------------------------------------------------------------------------------------ | -------------------------- |
| [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md)                                       | Table ownership            |
| [README.md](apps/api/alembic/README.md)                                                    | Migration validation       |
| [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)                                                       | ERM                        |
| [docs/architecture/DATABASE_RELATIONSHIP.md](./docs/architecture/DATABASE_RELATIONSHIP.md) | Flow diagram (Group 28)    |
| [docs/archive/README.md](./docs/archive/README.md#database)                                | Historical database audits |

---
