# Security Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` §15

---

## Executive Verdict

| Area                           | Status                      |
| ------------------------------ | --------------------------- |
| Authentication (Clerk)         | **PASS**                    |
| Authorization (RBAC)           | **PASS**                    |
| Webhook signature verification | **PASS**                    |
| Secrets in repo                | **PASS**                    |
| Audit logs                     | **PARTIAL**                 |
| Rate limiting                  | **PARTIAL**                 |
| Portal isolation               | **PASS** (recent hardening) |

**Overall:** Strong foundation; gaps in global rate limits and CRM audit coverage.

---

## Authentication

| Portal   | Mechanism              | Middleware              | Gap                                  |
| -------- | ---------------------- | ----------------------- | ------------------------------------ |
| Admin    | Clerk JWT              | `auth.protect()`        | Skips if Clerk unset (dev)           |
| Merchant | Clerk JWT              | `auth.protect()`        | Same                                 |
| Customer | Clerk JWT              | `auth.protect()`        | Same                                 |
| Website  | Clerk (login)          | i18n only; client gates | Medium — embedded portal client-side |
| Driver   | Porterchain JWT cookie | Cookie guard            | By design (not Clerk on routes)      |
| API      | Clerk JWT per route    | `auth/clerk.py`         | Dev bypass gated                     |

### Portal Isolation (Recent)

- `portal_guard.py` — `assert_clerk_id_exclusive`, staff portal blocks
- Customer auto-provision blocked for admin Clerk IDs
- Admin email cannot book as customer (identity_conflict)

---

## RBAC

### Admin (`admin_engine/rbac.py`)

| Module                                   | Enforced |
| ---------------------------------------- | -------- |
| orders, finance, crm, drivers, merchants | ✅       |
| routes, claims, support, notifications   | ✅       |
| pricing, settings, diagnostics           | ✅       |

**Usage:** `require_module()` ~100× in admin routers.

### Merchant (`merchant_engine/rbac.py`)

14 modules enforced across `routers/merchant.py`.

### Enterprise RBAC

`auth/enterprise_rbac.py` bridges admin/merchant to shared roles.

---

## Webhook Security

| Webhook   | Verification               | Idempotency         |
| --------- | -------------------------- | ------------------- |
| Stripe    | `construct_event` + secret | `stripe:{event_id}` |
| Fleetbase | Adapter signature          | Event bus store     |

**Rule compliance (§14):** Only Stripe webhooks finalize payment — **PASS**.

---

## Secrets

| Check                           | Result                                 |
| ------------------------------- | -------------------------------------- |
| `.env` gitignored               | ✅                                     |
| Live keys in source             | ❌ None found                          |
| Hardcoded `jwt_secret` default  | ⚠️ `config.py` — must override in prod |
| Test keys in docs/examples only | ✅                                     |

---

## Audit Logs

| Domain          | Coverage               | Status           |
| --------------- | ---------------------- | ---------------- |
| Booking drafts  | Every transition       | ✅ Complete      |
| Admin mutations | `admin_audit_logs`     | ⚠️ Partial       |
| CRM             | Company CRUD only      | ⚠️ Partial       |
| Fleetbase sync  | `fleetbase_sync_audit` | ✅ Complete      |
| Domain events   | `domain_events` table  | ✅ Complete      |
| Merchant        | Model exists           | ⚠️ Underutilized |

---

## Rate Limiting

| Scope                                    | Implementation                 | Status                     |
| ---------------------------------------- | ------------------------------ | -------------------------- |
| Merchant API keys (`/v1/merchant-api/*`) | `gateway_engine/middleware.py` | ✅                         |
| Portal JWT routes                        | None                           | ❌ **HIGH gap**            |
| Webhooks                                 | Signature-only                 | ✅ Acceptable              |
| Settings metadata                        | `rate_limit_per_minute: 120`   | Not enforced on portal API |

---

## Findings

### S-01 — No global portal API rate limits (High)

| Field               | Value                                                           |
| ------------------- | --------------------------------------------------------------- |
| **Severity**        | High                                                            |
| **Root Cause**      | Rate limit middleware only on merchant API gateway              |
| **Affected Layer**  | API / Gateway                                                   |
| **Recommended Fix** | SlowAPI or Redis sliding window on `/v1/*` authenticated routes |
| **Effort**          | 1–2 days                                                        |

### S-02 — CRM audit incomplete (Medium)

| Field               | Value                                                      |
| ------------------- | ---------------------------------------------------------- |
| **Severity**        | Medium                                                     |
| **Root Cause**      | Audit wired for company CRUD only                          |
| **Recommended Fix** | Extend `crm_sales_service` audit to leads, deals, contacts |
| **Effort**          | 1 day                                                      |

### S-03 — Hardcoded JWT secret default (Medium)

| Field               | Value                                                                    |
| ------------------- | ------------------------------------------------------------------------ |
| **Severity**        | Medium                                                                   |
| **Root Cause**      | `jwt_secret = "dev-sso-secret-change-in-production"` in committed config |
| **Recommended Fix** | Fail startup if default used in non-local env                            |
| **Effort**          | 2 hours                                                                  |

### S-04 — Website customer portal client-side gate (Medium)

| Field               | Value                                                           |
| ------------------- | --------------------------------------------------------------- |
| **Severity**        | Medium                                                          |
| **Root Cause**      | No server-side Clerk protect on website embedded portal         |
| **Recommended Fix** | Middleware protect on `/portal/customer` or redirect to `:3004` |
| **Effort**          | 4 hours                                                         |

### S-05 — Booking draft IDOR (Low) — FIXED

`assert_access` on draft endpoints — previously flagged, now implemented.

---

## Booking Security

| Control                                | Status |
| -------------------------------------- | ------ |
| Draft access control (`assert_access`) | ✅     |
| Staff cannot book as customer          | ✅     |
| Payment verification server-side only  | ✅     |
| PCI — no card storage                  | ✅     |

---

_Performance controls: `PERFORMANCE_AUDIT.md` · Auth docs: `AUTHENTICATION.md`_
