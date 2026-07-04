# PostgreSQL Compatibility Report

**Date:** July 1, 2026  
**Scope:** Porterchain API SQL / SQLAlchemy usage  
**Target:** PostgreSQL 16 via `postgresql+psycopg://`

---

## Summary

| Status                                          | Count                           |
| ----------------------------------------------- | ------------------------------- |
| **Fixed**                                       | 11 occurrences                  |
| **Compatible (no change)**                      | Majority of ORM usage           |
| **Recommended (Phase 5 — not yet implemented)** | JSONB, native UUID, GIN indexes |

---

## Fixed — SQLite-only SQL

### `json_extract` (CRM address filters)

| File                                | Lines   | Issue                                             | Fix                                                                 |
| ----------------------------------- | ------- | ------------------------------------------------- | ------------------------------------------------------------------- |
| `admin_engine/crm_sales_service.py` | 201–952 | `func.json_extract(col, "$.city")` is SQLite-only | Replaced with `json_text()` / `json_text_lower()` from `db_json.py` |

**New helper:** `apps/api/src/porterchain_api/db_json.py`

```python
column[key].astext  # PostgreSQL JSON/JSONB text extraction
```

---

## Compatible — no change required

| Pattern                      | Files                                                                          | PostgreSQL support   |
| ---------------------------- | ------------------------------------------------------------------------------ | -------------------- |
| `Column.ilike()`             | `orders_service`, `claims_service`, `finance_service`, `support_service`, etc. | Native `ILIKE` ✅    |
| `Column.like()`              | `settings_service`, `pricing_service`, `booking_draft_service`                 | Native ✅            |
| `func.count()`, `func.now()` | Widespread                                                                     | Native ✅            |
| `DateTime(timezone=True)`    | All models                                                                     | `TIMESTAMPTZ` ✅     |
| `JSON` column type           | `models.py`, CRM, routes, notifications                                        | PostgreSQL `JSON` ✅ |
| `text("SELECT 1")`           | Diagnostics, health                                                            | Native ✅            |
| `db.execute(text(...))`      | Diagnostics chaos tests                                                        | Native ✅            |
| Foreign keys in Alembic      | All migrations                                                                 | PostgreSQL ✅        |

---

## Alembic migration notes

| Item                                            | Current       | PostgreSQL impact   | Recommendation                                                |
| ----------------------------------------------- | ------------- | ------------------- | ------------------------------------------------------------- |
| `server_default=sa.text('(CURRENT_TIMESTAMP)')` | All revisions | Works on PostgreSQL | Migrate to `sa.text('now()')` in future revisions for clarity |
| String UUIDs `String(36)`                       | All PKs       | Works               | Phase 5: native `UUID` type                                   |
| Generic `sa.JSON()`                             | Widespread    | Stored as JSON      | Phase 5: `JSONB` + GIN indexes for CRM/search                 |

---

## Not found (clean)

| SQLite pattern                                | Status               |
| --------------------------------------------- | -------------------- |
| SQLite date functions (`date('now')`)         | Not used             |
| SQLite string functions (`GROUP_CONCAT`)      | Not used             |
| SQLite casting (`CAST(x AS TEXT)`) in queries | Not used             |
| `PRAGMA`                                      | Removed from `db.py` |
| Raw SQLite SQL in routers                     | Not found            |

---

## Phase 5 recommendations (before implementation)

These are **recommended** improvements — not applied in this migration to avoid data-loss risk:

1. **JSONB migration** — Convert `address`, `custom_fields`, `payload`, route `stops` columns to `JSONB` with GIN indexes for CRM city/province filters.
2. **Native UUID** — Migrate `String(36)` PKs to PostgreSQL `UUID` with `gen_random_uuid()` defaults.
3. **Composite indexes** — e.g. `(merchant_id, status)` on orders, `(status, next_attempt_at)` on `fleetbase_sync_jobs`.
4. **Partial indexes** — e.g. active orders only: `WHERE status NOT IN ('delivered','cancelled')`.
5. **Check constraints** — Enforce enum-like status values at DB level.
6. **`updated_at` triggers** — Replace SQLAlchemy `onupdate=func.now()` with PostgreSQL trigger for audit consistency under raw SQL.

---

## Compatibility score

| Area                 | Score       | Notes                                                           |
| -------------------- | ----------- | --------------------------------------------------------------- |
| Query compatibility  | **Healthy** | All known SQLite-only queries fixed                             |
| Schema compatibility | **Healthy** | Alembic runs on PostgreSQL                                      |
| Type system          | **Warning** | JSON not JSONB; string UUIDs                                    |
| Performance          | **Warning** | Missing GIN/composite indexes (see `POSTGRESQL_PERFORMANCE.md`) |
