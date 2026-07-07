# Security Audit — Porterchain Platform

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §15  
**Canonical:** [SECURITY.md](./SECURITY.md) · [RBAC_MATRIX.md](./RBAC_MATRIX.md)

---

## Executive verdict

| Area                           | Status                                                     |
| ------------------------------ | ---------------------------------------------------------- |
| Authentication (Clerk)         | **PASS**                                                   |
| Authorization (RBAC)           | **PASS**                                                   |
| Webhook signature verification | **PASS**                                                   |
| Secrets in repo                | **PASS**                                                   |
| Audit logs                     | **PARTIAL**                                                |
| Rate limiting                  | **PARTIAL** — implemented; local bypass + Redis dependency |
| Portal isolation               | **PASS**                                                   |

**Overall:** Strong foundation; tune rate limits for production load and extend CRM audit coverage.

---

## Authentication

| Portal                      | Mechanism           | Middleware / guard                          | Notes                                                   |
| --------------------------- | ------------------- | ------------------------------------------- | ------------------------------------------------------- |
| Admin                       | Clerk JWT           | `auth.protect()`                            | Skips if Clerk unset (dev)                              |
| Merchant                    | Clerk JWT           | `auth.protect()`                            | Same                                                    |
| Customer (`apps/customer/`) | Clerk JWT           | `middleware.ts` — all routes except sign-in | Dedicated app `:3004`                                   |
| Website                     | Clerk               | `clerkMiddleware` + i18n                    | Legacy `/portal/customer` — client gate; prefer `:3004` |
| Driver web                  | Clerk → API JWT     | Clerk login + Porterchain session cookie    | By design                                               |
| Driver mobile               | Clerk Expo          | Token → `/driver-api/v1/auth/login`         | Session JWT thereafter                                  |
| API                         | Clerk JWT per route | `auth/clerk.py`                             | `CLERK_DEV_BYPASS` local only                           |

### Portal isolation

`auth/portal_guard.py`:

- `assert_clerk_id_exclusive` — staff IDs cannot cross portals
- `require_clerk_app_for_portal` — per-app Clerk instance when configured
- Customer auto-provision blocked for admin Clerk IDs
- Admin email cannot book as customer (`identity_conflict`)

---

## RBAC

### Admin (`admin_engine/rbac.py`)

Modules enforced via `require_module()`: orders, finance, CRM, drivers, merchants, routes, claims, support, notifications, pricing, settings, diagnostics.

### Merchant (`merchant_engine/rbac.py`)

14 modules across `routers/merchant.py`.

### Enterprise bridge

`auth/enterprise_rbac.py` — shared role mapping for admin/merchant.

---

## Webhook security

| Webhook   | Path                       | Verification               | Idempotency           |
| --------- | -------------------------- | -------------------------- | --------------------- |
| Stripe    | `POST /webhooks/stripe`    | `construct_event` + secret | `stripe:{event_id}`   |
| Fleetbase | `POST /webhooks/fleetbase` | Adapter HMAC               | Event bus + processor |

**Rule (§14):** Only Stripe webhooks finalize payment — **PASS**.

---

## Secrets

| Check                               | Result                                                           |
| ----------------------------------- | ---------------------------------------------------------------- |
| `.env` gitignored                   | ✅                                                               |
| Live keys in source                 | ❌ None found                                                    |
| `jwt_secret` default in `config.py` | ⚠️ Must override in prod (`dev-sso-secret-change-in-production`) |
| Test keys in examples only          | ✅                                                               |

---

## Audit logs

| Domain          | Coverage                    | Status           |
| --------------- | --------------------------- | ---------------- |
| Booking drafts  | Every transition            | ✅               |
| Admin mutations | `admin_audit_logs`          | ⚠️ Partial       |
| CRM             | Company CRUD primarily      | ⚠️ Partial       |
| Fleetbase sync  | `fleetbase_sync_audit`      | ✅               |
| Domain events   | `domain_events`             | ✅               |
| Merchant        | `merchant_audit_logs` model | ⚠️ Underutilized |

---

## Rate limiting

| Scope                                    | Implementation                                                    | Status         |
| ---------------------------------------- | ----------------------------------------------------------------- | -------------- |
| Merchant API keys (`/v1/merchant-api/*`) | `gateway_engine/middleware.py`                                    | ✅             |
| Portal JWT routes                        | `platform/rate_limit_middleware.py` → `PortalRateLimitMiddleware` | ⚠️ **Partial** |
| Webhooks                                 | Signature-only (exempt from portal limiter)                       | ✅             |

**Portal limiter details:**

- Prefixes: `/v1/admin/`, `/v1/merchant/`, `/v1/customers/`, `/driver-api/`
- Exempt: `/health`, `/v1/webhooks/`, `/v1/quotes`, `/v1/booking-drafts`, public track
- **Disabled when `app_env=local`**
- Requires Redis in non-local; fails open if Redis unavailable
- Default: `portal_rate_limit_per_minute=120` (`PORTAL_RATE_LIMIT_PER_MINUTE`)

---

## Findings

### S-01 — Portal rate limits not enforced in local / without Redis (Medium)

| Field   | Value                                                                         |
| ------- | ----------------------------------------------------------------------------- |
| **Was** | High — no global limits                                                       |
| **Now** | Middleware exists; production must set `app_env≠local` + Redis                |
| **Fix** | Fail closed when Redis down in production; optional stricter limits per route |

### S-02 — CRM audit incomplete (Medium)

Extend audit beyond company CRUD to leads, deals, contacts.

### S-03 — Hardcoded JWT secret default (Medium)

Fail startup if default `jwt_secret` used when `app_env` is staging/production.

### S-04 — Website legacy customer portal (Low–Medium)

Embedded `/portal/customer` on website lacks server `auth.protect()` — dedicated `apps/customer/` at `:3004` is the supported surface.

### S-05 — Booking draft IDOR — **FIXED**

`assert_access` on draft endpoints.

---

## Booking security

| Control                               | Status |
| ------------------------------------- | ------ |
| Draft access control                  | ✅     |
| Staff cannot book as customer         | ✅     |
| Payment verification server-side only | ✅     |
| PCI — no card storage                 | ✅     |

---

## Related

| Document                                                           | Purpose              |
| ------------------------------------------------------------------ | -------------------- |
| [PERFORMANCE_AUDIT.md](./PERFORMANCE_AUDIT.md)                     | Performance controls |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Auth cluster         |
