# SOC 2 Type I readiness (§11.1.1)

**Type:** CANONICAL  
**Checklist:** §11.1.1 · ENT-G4  
**Last verified:** 2026-07-09  
**Status:** Dev controls documented — external audit not started

## Scope

Porterchain API + portals (merchant, admin, driver, customer) + website. Fleetbase adapter is a subprocess boundary (vendor).

## Trust service criteria (in scope)

| TSC | Control           | Evidence in repo                                                                            |
| --- | ----------------- | ------------------------------------------------------------------------------------------- |
| CC6 | Logical access    | [auth-clerk-spicedb.md](../architecture/auth-clerk-spicedb.md), SpiceDB `schema.zed`, Clerk |
| CC7 | System operations | [RUNBOOK.md](../../RUNBOOK.md), `/health/ready`, Sentry                                     |
| CC8 | Change management | GitHub PR + CI `validate:*` guards                                                          |
| CC9 | Risk mitigation   | [SECURITY.md](../../SECURITY.md), rate limits fail-closed                                   |

## Implemented technical controls

- RBAC enforced server-side (`require_module`)
- Admin + merchant audit logs + `GET /v1/admin/audit-logs/export`
- GDPR/CCPA export: `GET /v1/merchant/privacy/export`, `GET /v1/customers/me/privacy/export`
- JWT secret boot assertion in prod (`config.py`)
- Webhook signature verification (Stripe + Fleetbase)
- Secrets file-mount in deploy workflow (§11.1.5)

## Gap (external)

- SOC 2 Type I auditor engagement
- Annual penetration test (§11.1.3)
- Production secret manager attestation (Doppler — §11.1.14)

## Next step

Engage auditor after FND-G5 prod bridge + ENT-G2 SAML pilot are scheduled.
