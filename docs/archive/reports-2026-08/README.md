# Archived reports — August 2026

Point-in-time readiness reports, module matrices, regenerable E2E reports, and retired RBAC docs removed from the repo root during documentation cleanup.

**Do not edit.** Prefer living SSOTs in [docs/README.md](../../README.md).

| Former root file                                                    | Prefer instead                                                                            |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `CTO_AUDIT_REPORT.md`                                               | [docs/SILICON_VALLEY_READINESS_CHECKLIST.md](../../SILICON_VALLEY_READINESS_CHECKLIST.md) |
| `PRODUCTION_READINESS_REPORT.md` / `GAP_ANALYSIS.md` / `ROADMAP.md` | [PRIORITY_TODOS.md](../../PRIORITY_TODOS.md)                                              |
| `MODULE_*` scorecards                                               | [ops/ORDERS_MODULE.md](../../ops/ORDERS_MODULE.md) + checklist                            |
| `RBAC_MATRIX.md` / `ROLE_PERMISSIONS.md`                            | [architecture/auth-clerk-spicedb.md](../../architecture/auth-clerk-spicedb.md)            |
| `*_LOGISTICS_REPORT.md` / consistency / failure reports             | Regenerate via `pnpm validate:e2e:reports` when needed                                    |
| Website authority / gap / ICP logs                                  | [WEBSITE_GTM_EXECUTION_PLAN.md](../../WEBSITE_GTM_EXECUTION_PLAN.md)                      |
