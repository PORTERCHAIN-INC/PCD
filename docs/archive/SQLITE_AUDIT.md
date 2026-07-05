# SQLite Audit

**Last verified:** 2026-07-04  
**Scope:** Porterchain business code in PCD monorepo  
**Objective:** PostgreSQL only for Porterchain; Fleetbase MySQL untouched

> **Migration plan:** [DATABASE_MIGRATION_PLAN.md](./DATABASE_MIGRATION_PLAN.md) · **Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

---

## Executive summary

| Category | Status |
| -------- | ------ |
| SQLite in Porterchain runtime | **Removed** — blocked at startup |
| Defensive guards | **Kept** — fail fast on `sqlite://` URLs |
| Optional ETL script | `apps/api/scripts/migrate_sqlite_to_postgres.py` (legacy import only) |
| Fleetbase MySQL | **Unchanged** — out of scope |

**Verdict:** SQLite removal from Porterchain business code is **complete**. PostgreSQL is mandatory.

---

## Refactored files (complete)

| File | Action |
| ---- | ------ |
| `apps/api/src/porterchain_api/db.py` | PostgreSQL pool only; no `create_all`, no PRAGMA |
| `apps/api/src/porterchain_api/config.py` | PostgreSQL default + Pydantic validator rejects SQLite |
| `apps/api/src/porterchain_api/admin_engine/crm_sales_service.py` | `json_extract` → `db_json.json_text()` |
| `infrastructure/scripts/provision_admin.py` | Exits on SQLite URL |
| `apps/api/.env.example` | PostgreSQL URL |

---

## Removed SQLite mechanisms

| Mechanism | Status |
| --------- | ------ |
| `create_all()` in `init_db()` | ✅ Removed — Alembic only |
| `_migrate_sqlite_schema()` / PRAGMA patches | ✅ Removed |
| `_sync_sqlite_alembic()` stamp hack | ✅ Removed |
| `check_same_thread` connect arg | ✅ Removed |
| Default `sqlite:///./porterchain.db` | ✅ Removed |

---

## Defensive guards (intentional — keep)

| File | Purpose |
| ---- | ------- |
| `db.py` | Runtime error if `sqlite://` passed |
| `config.py` | Pydantic validator at startup |
| `provision_admin.py` | Script safety exit |
| `apps/api/tests/test_postgres_smoke.py` | Skips if SQLite URL (CI guard) |

---

## Optional legacy ETL (not runtime)

| File | Purpose |
| ---- | ------- |
| `apps/api/scripts/migrate_sqlite_to_postgres.py` | One-off SQLite → PostgreSQL import (`--dry-run` default) |

Uses `sqlite3` **only in this script** — not in API/worker runtime.

---

## Not found in Porterchain runtime (clean)

| Pattern | Result |
| ------- | ------ |
| `sqlite3` in API/worker services | ❌ None |
| `aiosqlite` | ❌ Not used |
| SQLite in worker direct DB | ❌ Worker uses Redis + API |

---

## Third-party / out of scope

| Component | Database | Action |
| --------- | -------- | ------ |
| Fleetbase (`apps/fleetbase/`) | MySQL 8 | **Do not modify** |
| Fleetbase Docker stack | MySQL | Fleetbase-owned |

---

## Local artifact cleanup

| Artifact | Recommendation |
| -------- | -------------- |
| `apps/api/porterchain.db` | Safe to delete after PostgreSQL validated |
| `porterchain.db-journal` | Safe to delete |

---

## Validation gate

- [x] PostgreSQL `alembic upgrade head` (13 revisions)
- [x] `init_db()` connectivity check
- [x] CRM JSON queries use PostgreSQL helpers
- [x] JSONB + GIN for CRM (`m1n2o3p4q5r6`)
- [ ] Full runtime E2E — see [DATABASE_VALIDATION_REPORT.md](./DATABASE_VALIDATION_REPORT.md)
