# Merchant Portal — Security Report

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) · [SECURITY.md](./SECURITY.md) · [RBAC.md](./RBAC.md)

---

## Summary

Merchant surfaces enforce **tenant isolation**, **module RBAC**, and **scoped API keys**. No merchant route exposes admin-only data. Support/claims use bridge services with `merchant_id` filter.

| Area                   | Rating  | Status          |
| ---------------------- | ------- | --------------- |
| Authentication         | Strong  | ✅              |
| Authorization (RBAC)   | Strong  | ✅              |
| Tenant isolation       | Strong  | ✅              |
| API key security       | Strong  | ✅              |
| Webhook security       | Strong  | ✅              |
| Rate limiting (portal) | Good    | ✅ (production) |
| Secrets handling       | Good    | ⚠               |
| Audit logging          | Partial | ⚠               |

> **Platform:** Overall certification — [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)

---

## Authentication

| Surface          | Mechanism                                      | Status |
| ---------------- | ---------------------------------------------- | ------ |
| Portal           | Clerk JWT (`Authorization: Bearer`)            | ✅     |
| Org context      | `X-Merchant-Org-Id`, `X-Merchant-Role`         | ✅     |
| Programmatic API | `X-Api-Key` via `gateway_engine/middleware.py` | ✅     |
| Notifications WS | JWT query param + optional `org_id`            | ✅     |

`MerchantContext` resolves merchant from Clerk org; rejects cross-tenant access at dependency layer.

---

## RBAC enforcement

**Source of truth:** `merchant_engine/rbac.py` → `MODULE_PERMISSIONS`

| Module key                                   | Typical actions        | Enforced |
| -------------------------------------------- | ---------------------- | -------- |
| `dashboard`, `orders`, `tracking`, `reports` | view                   | ✅       |
| `book`, `bulk`, `orders_write`               | create/manage          | ✅       |
| `billing`, `invoices`, `statements`          | view/export            | ✅       |
| `api_keys`                                   | manage keys/webhooks   | ✅       |
| `users`                                      | team invite/manage     | ✅       |
| `settings`                                   | profile/locations      | ✅       |
| `support`, `claims`                          | view/create via bridge | ✅       |

`require_module(ctx, "module")` on sensitive routes in `routers/merchant.py`.

**Readonly role:** Cannot manage keys, bulk write ops, or team invites.

---

## Tenant isolation

| Check                 | Implementation                            | Status |
| --------------------- | ----------------------------------------- | ------ |
| Order access          | `merchant_id` filter on all queries       | ✅     |
| Billing               | Scoped to `ctx.merchant.id`               | ✅     |
| API keys/webhooks     | `merchant_id` FK + service checks         | ✅     |
| Support/claims bridge | Admin services with `merchant_id=` filter | ✅     |
| Team                  | `merchant_users.merchant_id`              | ✅     |

Order/detail routes verify order belongs to merchant before return (no IDOR).

---

## API key security

| Control                                                 | Status                       |
| ------------------------------------------------------- | ---------------------------- |
| Keys stored hashed (SHA-256)                            | ✅                           |
| Prefix-only display in UI                               | ✅                           |
| Scope enforcement (`shipments:read`, `shipments:write`) | ✅                           |
| Per-key rate limits                                     | ✅ `gateway_engine`          |
| Usage audit log                                         | ✅ `merchant_api_usage_logs` |
| Sandbox vs production keys                              | ✅                           |
| Full key shown once at creation                         | ✅                           |

---

## Webhook security

| Control                                       | Status                        |
| --------------------------------------------- | ----------------------------- |
| HMAC-SHA256 signing on delivery               | ✅ `webhook_delivery_service` |
| Secret encrypted at rest (Fernet)             | ✅                            |
| Delivery logs (`merchant_webhook_deliveries`) | ✅                            |
| Retry with backoff (3 attempts)               | ✅                            |
| Merchant-scoped log access                    | ✅                            |

---

## Rate limiting

| Path                 | Middleware                     | Notes                           |
| -------------------- | ------------------------------ | ------------------------------- |
| `/v1/merchant/*`     | `PortalRateLimitMiddleware`    | Production; skipped in `local`  |
| `/v1/merchant-api/*` | `MerchantApiGatewayMiddleware` | Per-key limits + usage metering |

---

## Recommendations (⚠)

| Item                          | Recommendation                                     |
| ----------------------------- | -------------------------------------------------- |
| Team invite `pending_{email}` | Document ops procedure; Clerk Organizations API v2 |
| CORS per environment          | Validate `cors_origins` in deploy                  |
| Notification WS token expiry  | Client reconnect on 4401                           |
| IP allowlist for API keys     | Not implemented (enterprise future)                |

---

## masterrule alignment

- ✅ No secrets in frontend except public Maps key
- ✅ RBAC single source (`merchant_engine/rbac.py`)
- ✅ Merchant cannot access admin routes
- ✅ Webhook/API secrets not returned after creation
- ✅ Dev bypass gated (`CLERK_DEV_BYPASS` + `APP_ENV=local`)

---

## Related

| Document                                               | Purpose                    |
| ------------------------------------------------------ | -------------------------- |
| [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)               | Architecture audit         |
| [MERCHANT_GAP_ANALYSIS.md](./MERCHANT_GAP_ANALYSIS.md) | Open gaps (G-M010, G-M013) |
