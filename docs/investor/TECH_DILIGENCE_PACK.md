# Tech diligence pack (§10.2.6)

**Type:** CANONICAL  
**Checklist:** §10.2.6 · INV-G3 · Appendix H  
**Last verified:** 2026-07-09

## Executive summary

Porterchain is a multi-tenant logistics orchestration platform: **Next.js portals + FastAPI API + Postgres + Redis worker + Fleetbase adapter**. Merchants integrate via API keys, webhooks, and ERP connectors (NetSuite MVP). Vertical workflows (medical, food, construction, wholesale) are implemented in the API layer with CI guards (`pnpm validate:moat`).

## Architecture

- Context map: [ADR-011](../architecture/ADR-011-context-map.md)
- SAP deferred: [ADR-015](../architecture/ADR-015-sap-connector-deferred.md)
- Integrations registry: [INTEGRATIONS.md](../../INTEGRATIONS.md) + `integrations.yaml`

## Security & tenancy

- RBAC enforced in API (`authz/schema.zed`, `require_module` → SpiceDB Check)
- Authz ADR: [auth-clerk-spicedb.md](../architecture/auth-clerk-spicedb.md) (RBAC_MATRIX.md retired)
- Tenant isolation: merchant-scoped repositories (DD-07 closed)
- Rate limits fail-closed (DD-06)
- Audit export: `GET /v1/admin/audit-logs/export`

## Observability

- Sentry + OpenTelemetry (`platform/observability.py`) — DD-02 closed
- Business metrics: `admin_engine/business_metrics.py`

## Test & CI

- API tests: `apps/api/tests/` (27+ files)
- CI: `.github/workflows/ci.yml` — `validate:*` guards

## Open prod items (disclosed)

| ID     | Item                           | Status                                |
| ------ | ------------------------------ | ------------------------------------- |
| DD-05  | Fleetbase prod dispatch bridge | [~] dev processor; prod flag deferred |
| 0.1.13 | Alembic head in prod           | dev at `q0r1s2t3u4v5`                 |

## Validation commands

```bash
pnpm validate:architecture
pnpm validate:moat
pnpm validate:integration-marketplace
pnpm validate:investor-monopoly
```
