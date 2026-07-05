# Porterchain — Database Architecture


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Implemented — PostgreSQL 16 + Alembic in `apps/api/`

> **Ownership:** [DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md) · **Migrations:** [ALEMBIC_VALIDATION.md](./ALEMBIC_VALIDATION.md) · **Domain:** [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)

---

## Data store summary

| Store | Engine | Purpose | Owner | Access from Porterchain |
| ----- | ------ | ------- | ----- | ----------------------- |
| **Porterchain API DB** | PostgreSQL 16 | Commercial domain, CRM, billing, admin | Porterchain API | SQLAlchemy + Alembic |
| **Fleetbase DB** | MySQL 8 | Dispatch, GPS, routes, POD | Fleetbase (Laravel) | **HTTP adapter only** — never direct SQL |
| **Redis** | Redis 7 | Queues, cache, event streams | Shared infra | `redis` client / worker |

Auth identity: **Clerk** (external). User mirrors live in PostgreSQL (`porterchain_users`, portal-specific link tables).

---

## Porterchain PostgreSQL (canonical)

### Connection

| Setting | Local dev |
| ------- | --------- |
| URL | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` |
| Env var | `DATABASE_URL` |
| Container | `porterchain-postgres` (`postgres:16-alpine`) |
| Driver | `psycopg` ≥3.2 (`postgresql+psycopg://`) |

### ORM layout

| Module | Tables (examples) |
| ------ | ----------------- |
| `models.py` | `customers`, `quotes`, `bookings`, `orders`, `domain_events` |
| `merchant_models.py` | `merchants`, `merchant_api_keys`, `merchant_webhooks` |
| `crm_models.py` | `crm_leads`, `crm_companies`, `crm_deals` |
| `admin_models.py` | `drivers`, `pricing_tariffs`, `route_center_plans` |
| `driver_models.py` | `driver_shifts`, `driver_location_pings` |
| `booking_draft_models.py` | `booking_drafts`, `booking_draft_audits` |
| `notification_engine/models.py` | `notification_records`, `notification_devices` |
| `billing_engine/models.py` | `billing_ledger_entries` |
| `fleetbase_models.py` | `fleetbase_sync_jobs`, `fleetbase_sync_audit` |
| `user_models.py` / `invitation_models.py` | `porterchain_users`, `user_invitations` |

**~68 application tables** + `alembic_version`. Full list: [DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md).

### Schema rules

- **Alembic-only DDL** — `init_db()` runs `SELECT 1` only; no runtime `create_all`
- **SQLite blocked** — `config.py` validator + `db.py` guard reject `sqlite://`
- **Fleetbase mirror** — `orders`, `drivers`, `vehicles` in PostgreSQL; execution state synced via adapter
- **Commercial authority** — pricing, invoices, contracts, CRM stay in PostgreSQL

### Migrations

| Item | Path |
| ---- | ---- |
| Alembic config | `apps/api/alembic.ini` |
| Revisions | `apps/api/alembic/versions/` (13 revisions) |
| Head (July 2026) | `n2o3p4q5r6s7` — partial unique index on `orders.quote_id` |
| Apply | `pnpm db:migrate` |

---

## Fleetbase MySQL (execution — do not modify from Porterchain)

| Context | Host port | Container |
| ------- | --------- | --------- |
| Core compose profile | `127.0.0.1:3306` | `porterchain-mysql` |
| Fleetbase stack (`pnpm docker:fleetbase:up`) | `127.0.0.1:3307` | `porterchain-fleetbase-mysql` |

Schema owned by Fleetbase Laravel migrations. Porterchain reads/writes via `services/fleetbase-adapter/` only.

See [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) and [DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md).

---

## Redis usage

| Use case | Pattern |
| -------- | ------- |
| Worker task queues | `porterchain:queue:*` (email, sms, push, dispatch, billing, webhooks) |
| Event bus | Streams + DLQ (`porterchain:events`, `porterchain:events:dlq`) |
| Idempotency | Short-TTL keys in API handlers |
| Cache | Application-specific TTL keys |

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

## Backup (production target)

| Database | Method | Retention |
| -------- | ------ | --------- |
| PostgreSQL | `pg_dump` + WAL / managed RDS | 30 days |
| Fleetbase MySQL | `mysqldump` / managed | 30 days |
| Redis | AOF + snapshot | 7 days |

---

## Related documents

| Document | Purpose |
| -------- | ------- |
| [DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md) | Table ownership |
| [ALEMBIC_VALIDATION.md](./ALEMBIC_VALIDATION.md) | Migration validation |
| [ENTITY_RELATIONSHIP_MODEL.md](./ENTITY_RELATIONSHIP_MODEL.md) | ERM |
| [docs/architecture/DATABASE_RELATIONSHIP.md](./docs/architecture/DATABASE_RELATIONSHIP.md) | Flow diagram (Group 28) |
| [docs/archive/README.md](./docs/archive/README.md#database) | Historical database audits |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
