# SIG Lite questionnaire — enterprise security (§11 · ENT-G1)

**Type:** CANONICAL  
**Checklist:** ENT-G1  
**Last verified:** 2026-07-09  
**Target:** <20% answers require unreleased roadmap items

## How to use

Share this document with enterprise prospects **before** a full SIG. Each control maps to implemented evidence in-repo. Items marked **Roadmap** are Phase 2 and must stay below 20% of total answers.

| Section              | Controls | Roadmap count |
| -------------------- | -------- | ------------- |
| Access control       | 12       | 1 (SCIM)      |
| Application security | 10       | 1 (copilot)   |
| Operations           | 8        | 0             |
| Privacy              | 6        | 0             |
| **Total**            | **36**   | **2 (~6%)**   |

## Access control

| #   | Question                       | Answer                                | Evidence                                                   |
| --- | ------------------------------ | ------------------------------------- | ---------------------------------------------------------- |
| A1  | SSO supported?                 | Yes — SAML 2.0 via Clerk Enterprise   | [ADR-017](../architecture/ADR-017-enterprise-saml-scim.md) |
| A2  | MFA enforced?                  | Yes — Clerk MFA policies per portal   | [SECURITY.md](../../SECURITY.md)                           |
| A3  | RBAC model documented?         | Yes                                   | [RBAC_MATRIX.md](../../RBAC_MATRIX.md)                     |
| A4  | Admin audit export?            | Yes                                   | `GET /v1/admin/audit-logs/export`                          |
| A5  | SCIM provisioning?             | **Roadmap** Phase 2                   | ADR-017 — JIT via Clerk today                              |
| A6  | Session timeout?               | Yes — Clerk session TTL               | Clerk dashboard                                            |
| A7  | API keys scoped?               | Yes — merchant API keys + rate limits | `merchant_engine/api_key_service.py`                       |
| A8  | Secrets in vault?              | Yes — Doppler prod                    | [ADR-013](../architecture/ADR-013-secrets.md)              |
| A9  | Dev JWT blocked in prod?       | Yes                                   | `config.reject_dev_jwt_secret_in_production`               |
| A10 | Cross-tenant isolation tested? | Yes                                   | `tests/test_idor.py`                                       |
| A11 | Password policy?               | Delegated to Clerk / IdP              | —                                                          |
| A12 | Privileged access logging?     | Yes — admin audit + domain events     | `audit_export_service.py`                                  |

## Application security

| #   | Question                  | Answer                         | Evidence                                                     |
| --- | ------------------------- | ------------------------------ | ------------------------------------------------------------ |
| S1  | TLS everywhere?           | Yes — Caddy HSTS               | `infrastructure/deploy/Caddyfile`                            |
| S2  | Webhook signature verify? | Yes — Stripe + Fleetbase       | `routers/webhooks.py`                                        |
| S3  | Rate limiting?            | Yes — fail-closed middleware   | `rate_limit_middleware.py`                                   |
| S4  | SQL injection controls?   | ORM-only routers               | `validate:observability`                                     |
| S5  | Pen test cadence?         | Annual program documented      | [PEN_TEST.md](./PEN_TEST.md)                                 |
| S6  | SOC 2?                    | Type I readiness doc           | [SOC2.md](./SOC2.md)                                         |
| S7  | Privacy export/delete?    | Yes — merchant + customer APIs | `compliance_engine/privacy_service.py`                       |
| S8  | LLM on pay path?          | No — explicit ban              | [ADR-016](../architecture/ADR-016-no-llm-pricing-routing.md) |
| S9  | Admin AI copilot?         | **Roadmap** Phase 2 stub only  | `intelligence_engine/copilot_service.py`                     |
| S10 | Dependency scanning?      | Yes — CodeQL + Trivy CI        | `.github/workflows/security.yml`                             |

## Operations

| #   | Question                | Answer                         | Evidence                                                             |
| --- | ----------------------- | ------------------------------ | -------------------------------------------------------------------- |
| O1  | Status page?            | Yes                            | `/health/status`, [STATUS_PAGE.md](../STATUS_PAGE.md)                |
| O2  | Incident runbook?       | Yes                            | [RUNBOOK.md](../../RUNBOOK.md)                                       |
| O3  | Backup / restore?       | Documented                     | RUNBOOK + [DATABASE_ARCHITECTURE.md](../../DATABASE_ARCHITECTURE.md) |
| O4  | Monitoring?             | Prometheus `/metrics` + Sentry | `platform/metrics.py`                                                |
| O5  | Queue / DLQ monitoring? | Yes                            | RUNBOOK DLQ table, `porterchain_queue_depth`                         |
| O6  | DR tabletop?            | Yes — semi-annual              | RUNBOOK Incident drill (EXE-G3)                                      |
| O7  | Change management?      | GitHub PR + CI `validate:*`    | `.github/workflows/ci.yml`                                           |
| O8  | SLA documented?         | Yes                            | [SLA.md](./SLA.md)                                                   |

## Privacy (PIPEDA / GDPR-aligned)

| #   | Question                   | Answer                                | Evidence                                 |
| --- | -------------------------- | ------------------------------------- | ---------------------------------------- |
| P1  | Privacy policy published?  | Yes — website legal pages             | `website/`                               |
| P2  | Data export API?           | Yes                                   | merchant + customer privacy routes       |
| P3  | Deletion request workflow? | Yes                                   | `PRIVACY_DELETE_REQUESTED` event         |
| P4  | Canadian privacy doc?      | Yes                                   | [PIPEDA.md](./PIPEDA.md)                 |
| P5  | Subprocessor list?         | Fleetbase, Stripe, Clerk, Google Maps | [INTEGRATIONS.md](../../INTEGRATIONS.md) |
| P6  | Data residency             | Canada-primary (Toronto droplet)      | RUNBOOK                                  |

## Attestation

- **Roadmap answers:** 2 / 36 = **5.6%** (under 20% ENT-G1 target)
- **Prod gaps:** SAML live connections, pen test execution, SOC 2 auditor — tracked in checklist §11
