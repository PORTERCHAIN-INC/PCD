# Database Validation Report

**Last verified:** 2026-07-04  
**Database:** PostgreSQL 16 (`porterchain` database)  
**Snapshot basis:** July 2026 monorepo — re-run validation after schema changes

> **Audit:** [DATABASE_AUDIT.md](./DATABASE_AUDIT.md) · **Re-validate:** `pnpm db:migrate && cd apps/api && python scripts/validate_postgres_modules.py`

---

## Infrastructure validation

| Check | Expected | Classification |
| ----- | -------- | -------------- |
| PostgreSQL container | `porterchain-postgres` accepting connections | **Healthy** |
| Alembic at head | `n2o3p4q5r6s7` | **Healthy** |
| Table count | ~68 app tables + `alembic_version` | **Healthy** |
| `init_db()` startup ping | `SELECT 1` | **Healthy** |
| Connection pool | Pre-ping + recycle configured | **Healthy** |
| SQLite rejection | Config validator + engine guard | **Healthy** |

---

## Schema validation (core tables)

| Table | Role | Status |
| ----- | ---- | ------ |
| `orders` | Commercial mirror | ✅ |
| `customers` | Retail identity | ✅ |
| `quotes` | Pricing quotes | ✅ |
| `merchants` | B2B accounts | ✅ |
| `crm_leads` | CRM (JSONB filters) | ✅ |
| `fleetbase_sync_jobs` | Adapter retry queue | ✅ |
| `domain_events` | Event bus persistence | ✅ |
| `route_center_plans` | Route Center | ✅ |
| `porterchain_users` | Clerk identity mirror | ✅ |
| `user_invitations` | Staff invitations | ✅ |

---

## Transaction validation

| Test | Result |
| ---- | ------ |
| Explicit `BEGIN` / `ROLLBACK` | ✅ Pass |
| SQLAlchemy session commit/rollback | ✅ Pass |
| Alembic upgrade/downgrade cycle | ✅ Pass (per revision review) |

---

## Concurrency validation

| Test | Result | Notes |
| ---- | ------ | ----- |
| Connection pool (10 + overflow) | ✅ Configured | Load test pending |
| `FOR UPDATE SKIP LOCKED` on sync jobs | ⚠️ Not implemented | Recommended at worker scale |
| SQLite single-writer issue | ✅ Eliminated | PostgreSQL only |

---

## Module validation matrix

Validated by `apps/api/scripts/validate_postgres_modules.py`:

| Module | Key tables |
| ------ | ---------- |
| Website / quotes | `quotes`, `customers`, `visitor_sessions` |
| Bookings | `bookings`, `booking_drafts`, `payments` |
| Orders | `orders`, `order_events`, `order_exceptions` |
| Merchants | `merchants`, `merchant_api_keys`, `merchant_webhooks` |
| CRM | `crm_leads`, `crm_companies`, `crm_deals` |
| Finance | `invoices`, `billing_ledger_entries` |
| Drivers | `drivers`, `driver_shifts`, `driver_location_pings` |
| Fleetbase adapter | `fleetbase_sync_jobs`, `fleetbase_sync_audit` |
| Route Center | `route_center_plans`, `route_center_templates` |
| Auth | `porterchain_users`, `user_invitations`, `admin_users` |

**Runtime E2E** (portals + Fleetbase stack) remains manual QA — schema validation is automated; full flows are not CI-gated.

---

## Fleetbase synchronization validation

| Check | Status |
| ----- | ------ |
| Fleetbase MySQL untouched by Porterchain SQL | ✅ |
| Adapter state in PostgreSQL | ✅ `fleetbase_sync_*` |
| Direct MySQL from Porterchain API | ✅ None — HTTP adapter only |

---

## Redis validation

| Check | Status |
| ----- | ------ |
| Queue keys (`porterchain:queue:*`) | ✅ |
| Redis not replacing PostgreSQL as SoT | ✅ |

---

## Known gaps

| Gap | Severity | Action |
| --- | -------- | ------ |
| CI PostgreSQL + pytest suite | Warning | Add GitHub Actions service container |
| Legacy SQLite data migration | N/A | Fresh PostgreSQL default for dev |
| Remaining JSON → JSONB columns | Warning | Continue per [POSTGRESQL_PERFORMANCE.md](./POSTGRESQL_PERFORMANCE.md) |
| Full E2E in CI | Warning | QA checklist before production |

---

## Overall validation status

| Layer | Status |
| ----- | ------ |
| Schema / Alembic | **Healthy** |
| SQL compatibility | **Healthy** |
| Configuration | **Healthy** |
| Runtime E2E | **Warning** — manual QA pending |
| Production readiness | See [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) |
