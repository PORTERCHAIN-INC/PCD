# Identity migration CLI (Phase 7) — RETIRED

**Status:** DELETED (2026-08-06)  
**Reason:** Cutover complete to `CLERK_MODE=platform_driver`. The 4→1 Clerk migration CLI is no longer shipped.

Removed:

- `apps/api/src/porterchain_api/auth/identity_migration/**`
- `apps/api/scripts/identity_migrate.py`
- `pnpm identity:migrate`

Postgres bookkeeping tables `identity_migration_runs` / `identity_migration_records` may still exist from Alembic Phase 2 — leave them; do not reintroduce the CLI.

**Current SoT:** [SECRETS_MAP.md](../SECRETS_MAP.md) · [clerk-consolidation.md](../runbooks/clerk-consolidation.md)
