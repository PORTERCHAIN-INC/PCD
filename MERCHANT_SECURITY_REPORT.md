# Merchant Portal — Security Report

**Date:** June 30, 2026  
**Reference:** [masterrule.md](./masterrule.md) security rules

---

## Summary

Merchant surfaces enforce **tenant isolation**, **module RBAC**, and **scoped API keys**. No merchant route exposes admin-only data. Support/claims use bridge services with `merchant_id` filter.

| Area                 | Rating  | Status |
| -------------------- | ------- | ------ |
| Authentication       | Strong  | ✅     |
| Authorization (RBAC) | Strong  | ✅     |
| Tenant isolation     | Strong  | ✅     |
| API key security     | Strong  | ✅     |
| Webhook security     | Strong  | ✅     |
| Secrets handling     | Good    | ⚠      |
| Input validation     | Good    | ✅     |
| Audit logging        | Partial | ⚠      |

---

## Authentication

| Surface          | Mechanism                           | Status |
| ---------------- | ----------------------------------- | ------ |
| Portal           | Clerk JWT (`Authorization: Bearer`) | ✅     |
| Org context      | `X-Merchant-Org-Id` header          | ✅     |
| Programmatic API | `X-Api-Key` + optional secret       | ✅     |
| WebSocket        | Same JWT via query/header           | ✅     |

**`MerchantContext`** resolves merchant from Clerk org; rejects cross-tenant access at dependency layer.

---

## RBAC enforcement

**Source of truth:** `merchant_engine/rbac.py`

| Module       | Permissions            | Enforced on routes |
| ------------ | ---------------------- | ------------------ |
| dashboard    | view                   | ✅                 |
| orders       | view, manage, export   | ✅                 |
| booking      | create, bulk           | ✅                 |
| tracking     | view                   | ✅                 |
| billing      | view, export           | ✅                 |
| reports      | view, export, schedule | ✅                 |
| integrations | view, manage           | ✅                 |
| team         | view, invite, manage   | ✅                 |
| settings     | view, manage           | ✅                 |
| support      | view, create           | ✅                 |
| claims       | view, create           | ✅                 |

`require_module(ctx, "module", "action")` on all sensitive endpoints in `routers/merchant.py`.

**Readonly role:** Cannot invite, manage keys, or bulk-cancel.

---

## Tenant isolation

| Check             | Implementation                                     | Status |
| ----------------- | -------------------------------------------------- | ------ |
| Order access      | `merchant_id` filter on all queries                | ✅     |
| Billing           | Scoped to `ctx.merchant_id`                        | ✅     |
| API keys/webhooks | `merchant_id` FK + service checks                  | ✅     |
| Support bridge    | `AdminSupportService.list_enriched(merchant_id=…)` | ✅     |
| Claims bridge     | `AdminClaimsService.list_enriched(merchant_id=…)`  | ✅     |
| Team              | `merchant_users.merchant_id`                       | ✅     |

**No IDOR:** Order/detail routes verify order belongs to merchant before return.

---

## API key security

| Control                                    | Status                       |
| ------------------------------------------ | ---------------------------- |
| Keys stored hashed                         | ✅                           |
| Prefix-only display in UI                  | ✅                           |
| Scope enforcement (`bookings:write`, etc.) | ✅                           |
| Rate limiting per key                      | ✅ `gateway_engine`          |
| Usage audit log                            | ✅ `merchant_api_usage_logs` |
| Sandbox vs production keys                 | ✅                           |

---

## Webhook security

| Control                                 | Status                        |
| --------------------------------------- | ----------------------------- |
| HMAC-SHA256 signing                     | ✅ `webhook_delivery_service` |
| Secret encrypted at rest                | ✅                            |
| Delivery logs (no full payload secrets) | ✅                            |
| Retry with backoff                      | ✅                            |
| Merchant-only log access                | ✅                            |

---

## Data in transit & headers

| Item                                            | Status                         |
| ----------------------------------------------- | ------------------------------ |
| HTTPS assumed in production                     | ✅ (deploy config)             |
| CORS restricted to portal origin                | ⚠ verify per env               |
| No sensitive data in client env except Maps key | ⚠ Maps key is public-by-design |

---

## Input validation

| Layer                                            | Status                       |
| ------------------------------------------------ | ---------------------------- |
| Pydantic schemas on all POST/PATCH               | ✅                           |
| Booking address validation via Fleetbase adapter | ✅                           |
| Bulk upload size/row limits                      | ✅                           |
| SQL injection                                    | Mitigated via SQLAlchemy ORM | ✅  |

---

## Partial / recommendations (⚠)

| Item                                       | Risk                     | Recommendation                                |
| ------------------------------------------ | ------------------------ | --------------------------------------------- |
| Team invite creates `pending_{email}` user | Low — no auto Clerk link | Document ops procedure; add Clerk API in v2   |
| `lib/api.ts` legacy                        | Low — unused paths       | Remove in cleanup sprint                      |
| CORS per-environment                       | Medium if misconfigured  | Validate `ALLOWED_ORIGINS` in deploy          |
| Activity log completeness                  | Low                      | Team activity from DB; not all actions logged |
| Document upload                            | Metadata only            | No arbitrary file upload surface (good)       |
| Notification WS auth                       | Medium                   | Ensure token expiry handled client-side       |

---

## Missing security controls (❌)

| Item                         | Notes                                              |
| ---------------------------- | -------------------------------------------------- |
| Merchant-facing audit export | Admin has audit; merchant team activity is partial |
| IP allowlist for API keys    | Not implemented (optional enterprise feature)      |

---

## masterrule alignment

- ✅ No secrets in frontend except public Maps key
- ✅ RBAC single source (`merchant_engine/rbac.py`)
- ✅ Merchant cannot access admin routes
- ✅ Webhook secrets not returned after creation
- ✅ API keys never returned in full after creation
