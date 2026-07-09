# Porterchain API — CHANGELOG

**Type:** CANONICAL  
**Policy:** §0.3.7 · DD-15 — backward-compatible changes only on `/v1/*` unless documented here.

## Versioning

- **URL prefix:** `/v1/*` (stable partner + portal contract)
- **Breaking changes:** require ADR + entry below + partner notice ≥30 days
- **OpenAPI truth:** `https://api.porterchain.com/docs` (or `http://localhost:8001/docs` local)

## Unreleased

### Added

- Executive Command Center `/v1/admin/dashboard/center` returns chart-ready `trends: { labels, orders, revenue_cents }`
- Redis pub/sub WebSocket fanout for notifications (DD-11)
- Rate limit fail-closed on Redis errors (DD-06)
- Partner Postman collection (`docs/api/porterchain.postman.json`) + committed OpenAPI snapshot (`docs/api/openapi.json`, `pnpm docs:openapi`) (§7.1.2, §2.4.3)

### Fixed

- `POST /v1/admin/operations/queue/assign-batch` now defines its request body (`AssignBatchBody`) and a real `AdminOperationsService.assign_batch`; previously an undefined forward-ref model made `GET /openapi.json` (and `/docs`) raise. Guarded by `tests/test_openapi_schema.py`.

### Changed

- `route.optimized` catalog entry moved to Phase 2 stub (ADR-010) — not emitted in Phase 1 loop

### Security

- Per-portal Clerk JWKS (`CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_JWKS_URL`)
- `jwt_secret` boot guard rejects dev default in production (DD-12)

## 2026-07 — Foundation wave (DD-01–DD-08)

- Test pyramid: ≥27 API test files; CI blocks on failure
- Tenant isolation + IDOR tests (DD-07)
- Order/payment row locks + Stripe idempotency (DD-08)
- Worker in prod compose + dispatch processor (DD-04, DD-05a)
- Sentry + OpenTelemetry hooks (DD-02; DSN optional)

## Deprecation policy

1. Mark endpoint `@deprecated` in OpenAPI description
2. Log `Deprecation` header for one release cycle
3. Remove only after ADR + CHANGELOG + `validate:d2` green
