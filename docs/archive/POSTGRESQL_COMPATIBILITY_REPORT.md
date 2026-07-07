# PostgreSQL Compatibility Report

**Last verified:** 2026-07-04  
**Scope:** Porterchain API SQL / SQLAlchemy usage  
**Target:** PostgreSQL 16 via `postgresql+psycopg://`

> **Performance follow-up:** [POSTGRESQL_PERFORMANCE.md](./POSTGRESQL_PERFORMANCE.md) · **Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

---

## Summary

| Status                            | Count                                  |
| --------------------------------- | -------------------------------------- |
| **Fixed** (SQLite-only SQL)       | CRM `json_extract` → `db_json` helpers |
| **Implemented** (Phase 5 partial) | CRM JSONB + GIN via `m1n2o3p4q5r6`     |
| **Compatible** (no change)        | Majority of ORM usage                  |
| **Recommended** (future)          | Native UUID, remaining JSON → JSONB    |

---

## Fixed — SQLite-only SQL

### `json_extract` (CRM address filters)

| File                                | Fix                                                   |
| ----------------------------------- | ----------------------------------------------------- |
| `admin_engine/crm_sales_service.py` | `json_text()` / `json_text_lower()` from `db_json.py` |

Helper: `apps/api/src/porterchain_api/db_json.py` — uses `column[key].astext` (PostgreSQL JSON/JSONB).

---

## Implemented — Phase 5 partial (`m1n2o3p4q5r6`)

| Change           | Tables                                                                                       | Status |
| ---------------- | -------------------------------------------------------------------------------------------- | ------ |
| `JSON` → `JSONB` | `crm_companies.address`, `custom_fields`; `crm_leads.address`, `custom_fields`               | ✅     |
| GIN indexes      | `ix_crm_companies_address_gin`, `ix_crm_leads_address_gin`, `ix_crm_leads_custom_fields_gin` | ✅     |

Other JSON columns (`route_center_plans.stops`, notification payloads, etc.) remain generic `JSON` — migrate incrementally.

---

## Compatible — no change required

| Pattern                       | PostgreSQL support |
| ----------------------------- | ------------------ |
| `Column.ilike()`              | Native `ILIKE` ✅  |
| `func.count()`, `func.now()`  | Native ✅          |
| `DateTime(timezone=True)`     | `TIMESTAMPTZ` ✅   |
| `JSON` / `JSONB` column types | Native ✅          |
| `text("SELECT 1")`            | Native ✅          |
| Alembic FK definitions        | PostgreSQL ✅      |

---

## Alembic notes

| Item                                 | Current         | Recommendation                           |
| ------------------------------------ | --------------- | ---------------------------------------- |
| `server_default=(CURRENT_TIMESTAMP)` | Early revisions | Normalize to `now()` in future revisions |
| String UUIDs `String(36)`            | All PKs         | Optional future `UUID` type migration    |
| Remaining `sa.JSON()`                | Various tables  | JSONB where filtered/indexed             |

---

## Not found (clean)

| SQLite pattern                | Status    |
| ----------------------------- | --------- |
| `date('now')`, `GROUP_CONCAT` | Not used  |
| `PRAGMA` in runtime code      | Removed   |
| Raw SQLite SQL in routers     | Not found |

---

## Future recommendations (not yet applied)

1. **JSONB rollout** — `payload`, route `stops`, notification metadata where queried
2. **Native UUID** — `gen_random_uuid()` defaults
3. **Check constraints** — enum-like status at DB level
4. **`updated_at` triggers** — audit consistency under raw SQL

---

## Compatibility score

| Area                   | Score       | Notes                              |
| ---------------------- | ----------- | ---------------------------------- |
| Query compatibility    | **Healthy** | SQLite-only queries fixed          |
| Schema compatibility   | **Healthy** | 13 Alembic revisions on PostgreSQL |
| Type system            | **Warning** | Partial JSONB; string UUIDs        |
| CRM search performance | **Healthy** | JSONB + GIN applied                |
