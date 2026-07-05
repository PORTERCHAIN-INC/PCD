# Merchant Portal — Gap Analysis

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) v3.1 · [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)  
**Scope:** Merchant Portal foundation architecture and feature parity

---

## Executive summary

Merchant core B2B workflows (book, bulk, orders, track, billing, reports, API keys, webhooks, team, settings) are **live and architecturally compliant**. All traffic routes through the Porterchain API with event-driven Fleetbase dispatch.

**Foundation gaps closed (2026-06/07 audit cycle):**

| ID     | Gap                          | Fix                                                |
| ------ | ---------------------------- | -------------------------------------------------- |
| G-M001 | No `/v1/merchant-api` router | `routers/merchant_api.py` + `auth/merchant_api.py` |
| G-M002 | API key auth not wired       | `X-Api-Key` + `gateway_engine/middleware.py`       |
| G-M003 | Webhook fanout not delivered | `webhook_delivery_service.py` + worker processor   |
| G-M004 | Signing secret not storable  | `encrypted_signing_secret` + Fernet                |

**UI gaps partially closed (2026-07):**

| ID     | Was                           | Now                                                  |
| ------ | ----------------------------- | ---------------------------------------------------- |
| G-M101 | Recipients UI missing         | ✅ Settings + book picker                            |
| G-M102 | Webhook UI missing            | ✅ `/api` Integrations page                          |
| G-M110 | Dashboard notifications empty | ⚠ `NotificationCenter` wired; feed depends on events |

---

## Gap inventory

### Closed (foundation)

| ID     | Category  | Resolution                                          |
| ------ | --------- | --------------------------------------------------- |
| G-M001 | API       | `/v1/merchant-api/*` delegates to `merchant_engine` |
| G-M002 | Security  | `MerchantApiKeyService.authenticate_key()` + scopes |
| G-M003 | Event bus | HMAC webhook delivery in worker                     |
| G-M004 | Data      | Encrypted webhook signing secrets                   |

### Open — foundation (platform)

| ID     | Category  | Gap                                        | Priority      |
| ------ | --------- | ------------------------------------------ | ------------- |
| G-M010 | Event bus | Cancel calls `BookingSyncService` directly | P2            |
| G-M011 | Billing   | NET batch invoice generation missing       | P2            |
| G-M012 | Billing   | `Invoice.pdf_url` never populated          | P2            |
| G-M013 | Security  | Dev bypass if misconfigured in prod        | P1 (platform) |

### Open — feature (non-foundation)

| ID     | Category  | Gap                                               | Priority |
| ------ | --------- | ------------------------------------------------- | -------- |
| G-M103 | UI        | Team role change UI limited                       | P3       |
| G-M104 | UI        | API key scopes not in create form                 | P3       |
| G-M105 | Bulk      | XLSX label but CSV-only parser                    | P2       |
| G-M106 | Templates | `MerchantBookingTemplate` model unused            | P3       |
| G-M107 | Support   | Merchant-scoped support routes minimal            | P3       |
| G-M108 | Tracking  | No dedicated live map WebSocket (platform policy) | P3       |
| G-M109 | Reports   | `average_delivery_minutes` may be null            | P3       |
| G-M111 | Team      | Clerk org invitation not synced                   | P3       |
| G-M112 | Infra     | No dedicated Docker service for merchant-portal   | P3       |
| G-M113 | Repo      | `apps/merchant/` placeholder                      | P3       |

---

## Architecture compliance

### Fleetbase boundary — ✅ Compliant

```
Merchant Portal :3001 → /v1/merchant/* → merchant_engine → Event Bus → fleetbase_engine → Adapter → Fleetbase :8000
```

### Layered architecture — ⚠ One inconsistency

Direct `BookingSyncService.sync_cancellation()` on merchant cancel (G-M010) — should emit `order.cancelled` first.

---

## Priority matrix

| Priority | Open count   | Focus                                            |
| -------- | ------------ | ------------------------------------------------ |
| P1       | 1 (platform) | Dev bypass hardening                             |
| P2       | 5            | Billing automation, cancel event path, bulk XLSX |
| P3       | 9            | Templates, Clerk sync, infra polish              |

---

## Verification checklist

| Requirement                       | Status |
| --------------------------------- | ------ |
| Portal → API only                 | ✅     |
| No Fleetbase from UI              | ✅     |
| Business logic in services        | ✅     |
| API key programmatic access       | ✅     |
| Webhook fanout delivery           | ✅     |
| Fleetbase via adapter on dispatch | ✅     |
| Clerk auth + RBAC                 | ✅     |

---

## Related

| Document                                                               | Purpose                |
| ---------------------------------------------------------------------- | ---------------------- |
| [MERCHANT_PRODUCTION_READINESS.md](./MERCHANT_PRODUCTION_READINESS.md) | Readiness matrix       |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)     | Platform certification |

_Update when closing gaps. Intentional exceptions must update [masterrule.md](./masterrule.md) first (§20.10)._
