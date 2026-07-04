# SQLite Audit

**Date:** July 1, 2026  
**Scope:** Entire PCD repository (Porterchain business code)  
**Objective:** Remove SQLite from Porterchain; Fleetbase MySQL untouched

---

## Executive summary

| Category                                    | Count   |
| ------------------------------------------- | ------- |
| **Removed / refactored (Porterchain code)** | 4 files |
| **Defensive guards (reject SQLite URLs)**   | 3 files |
| **Documentation only (updated or pending)** | 6 files |
| **Third-party / Fleetbase (do not modify)** | N/A     |

SQLite has been **removed from Porterchain runtime code**. Remaining mentions are rejection guards or historical documentation references.

---

## Porterchain business code (removed or refactored)

| File                                                             | Purpose                           | Action                                                              | Status  |
| ---------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------- | ------- |
| `apps/api/src/porterchain_api/db.py`                             | Engine, `init_db`, SQLite patches | **Refactored** — PostgreSQL pool only; no `create_all`, no PRAGMA   | ✅ Done |
| `apps/api/src/porterchain_api/config.py`                         | Default `DATABASE_URL`            | **Refactored** — PostgreSQL default + validator rejects `sqlite://` | ✅ Done |
| `apps/api/src/porterchain_api/admin_engine/crm_sales_service.py` | CRM JSON filters                  | **Refactored** — `json_extract` → PostgreSQL `json_text()` helper   | ✅ Done |
| `infrastructure/scripts/provision_admin.py`                      | Admin provisioning                | **Refactored** — PostgreSQL URL default; exits on SQLite            | ✅ Done |
| `apps/api/.env`                                                  | Local dev config                  | **Updated** — `postgresql+psycopg://...`                            | ✅ Done |
| `apps/api/.env.example`                                          | Template                          | **Updated** — PostgreSQL URL                                        | ✅ Done |
| `apps/api/src/porterchain_api/admin_engine/driver360_service.py` | Timestamp comment                 | **Updated** — removed SQLite reference                              | ✅ Done |

---

## Removed SQLite mechanisms

| Mechanism                            | Former location        | Safe to remove?                      | Status      |
| ------------------------------------ | ---------------------- | ------------------------------------ | ----------- |
| `create_all()` bootstrap             | `db.py` `init_db()`    | Yes — Alembic is sole schema manager | ✅ Removed  |
| `_migrate_sqlite_schema()`           | `db.py`                | Yes — ad-hoc PRAGMA patches          | ✅ Removed  |
| `_sync_sqlite_alembic()`             | `db.py`                | Yes — SQLite stamp hack              | ✅ Removed  |
| `PRAGMA table_info`                  | `db.py`                | Yes                                  | ✅ Removed  |
| `sqlite_master` queries              | `db.py`                | Yes                                  | ✅ Removed  |
| `check_same_thread` connect arg      | `db.py`                | Yes                                  | ✅ Removed  |
| `func.json_extract()`                | `crm_sales_service.py` | No — needed PostgreSQL replacement   | ✅ Replaced |
| Default `sqlite:///./porterchain.db` | `config.py`, `.env*`   | Yes                                  | ✅ Removed  |

---

## Defensive SQLite guards (intentional — keep)

| File                                        | Purpose                             | Classification             |
| ------------------------------------------- | ----------------------------------- | -------------------------- |
| `apps/api/src/porterchain_api/db.py`        | Runtime error if `sqlite://` passed | **Keep** — fail fast       |
| `apps/api/src/porterchain_api/config.py`    | Pydantic validator rejects SQLite   | **Keep** — fail at startup |
| `infrastructure/scripts/provision_admin.py` | Exit if SQLite URL                  | **Keep** — script safety   |

---

## Documentation references (updated or note)

| File                                                  | Mention                       | Action                                                                        |
| ----------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------- |
| `apps/api/alembic/README.md`                          | SQLite local policy           | ✅ Updated — PostgreSQL only                                                  |
| `apps/api/README.md`                                  | `porterchain.db`              | ✅ Updated                                                                    |
| `README.md`                                           | SQLite init_db                | ✅ Updated                                                                    |
| `TECH_STACK.md`                                       | SQLite local                  | ✅ Updated                                                                    |
| `FLEETBASE_DATABASE.md`                               | Porterchain PostgreSQL/SQLite | ⚠️ Update Porterchain column to PostgreSQL only (Fleetbase section unchanged) |
| `FLEETBASE_ANALYSIS.md`                               | Dual store wording            | ⚠️ Historical — Porterchain side is PostgreSQL                                |
| `docs/architecture/SYSTEM_ARCHITECTURE.md`            | Diagram label                 | ⚠️ Update diagram text                                                        |
| `docs/architecture/ARCHITECTURE_VALIDATION_REPORT.md` | SQLite dev default            | ⚠️ Superseded by this migration                                               |

---

## Not found in Porterchain code (clean)

| Pattern               | Result                                    |
| --------------------- | ----------------------------------------- |
| `sqlite3`             | Not used in Porterchain Python            |
| `aiosqlite`           | Not used                                  |
| `database.db`         | Not used                                  |
| SQLite-specific tests | No `apps/api/tests/` directory            |
| SQLite in worker      | Worker uses Redis + API; no direct DB URL |

---

## Third-party / out of scope

| Component                     | Database    | Action                           |
| ----------------------------- | ----------- | -------------------------------- |
| Fleetbase (`apps/fleetbase/`) | MySQL 8     | **Do not modify** per masterrule |
| Fleetbase Docker              | `mysql:8.0` | **Keep** — execution engine      |
| Laravel migrations            | MySQL       | Fleetbase-owned                  |

---

## Local artifact cleanup

| Artifact                  | Recommendation                                      |
| ------------------------- | --------------------------------------------------- |
| `apps/api/porterchain.db` | Safe to delete after PostgreSQL migration validated |
| `porterchain.db-journal`  | Safe to delete                                      |

---

## Validation gate (per implementation rules)

- [x] PostgreSQL `alembic upgrade head` succeeds on fresh database
- [x] Alembic downgrade/upgrade cycle tested
- [x] `init_db()` connectivity check passes
- [x] CRM JSON queries refactored
- [ ] Full Phase 9 module CRUD validation (see `DATABASE_VALIDATION_REPORT.md`)

**SQLite removal from Porterchain business code: APPROVED** after PostgreSQL validation passes.
