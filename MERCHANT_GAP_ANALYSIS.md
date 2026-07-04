# Merchant Portal — Gap Analysis

**Reference:** [masterrule.md](./masterrule.md) v3.1 · [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)  
**Date:** June 30, 2026  
**Scope:** Merchant Portal foundation architecture and feature parity

---

## Executive summary

The Merchant Portal core B2B workflows (book, bulk, orders, track, billing, reports, API keys, team, settings) are **live and architecturally compliant**. The portal correctly routes all traffic through the Porterchain API with event-driven Fleetbase dispatch.

**Foundation gaps closed in this audit cycle:**

| ID | Gap | Fix |
|----|-----|-----|
| G-M001 | No `/v1/merchant-api` programmatic router | Added `routers/merchant_api.py` + `auth/merchant_api.py` |
| G-M002 | API key authentication not wired | `MerchantApiKeyService.authenticate_key()` + `X-Api-Key` dependency |
| G-M003 | Merchant webhook delivery stub | `merchant_engine/webhook_delivery_service.py` + worker processor |
| G-M004 | Webhook signing secret not storable for delivery | `encrypted_signing_secret` column + Fernet encryption |

**Remaining gaps** are feature/UI polish or platform-wide items — not foundation blockers.

---

## Gap inventory

### Closed (this audit)

| ID | Category | Gap | Priority | Resolution |
|----|----------|-----|----------|------------|
| G-M001 | API | `/v1/merchant-api` missing | P1 | `routers/merchant_api.py` delegates to existing `merchant_engine` services |
| G-M002 | Security | API keys created but unusable | P1 | `auth/merchant_api.py` validates `X-Api-Key` header |
| G-M003 | Event bus | `order.*` fanout queued but not delivered | P1 | `WebhookDeliveryService.deliver_fanout()` in worker |
| G-M004 | Data | Webhook secret hash-only blocks HMAC signing | P1 | Encrypted secret storage at webhook creation |

### Open — foundation (platform)

| ID | Category | Gap | Priority | Recommended fix |
|----|----------|-----|----------|-----------------|
| G-M010 | Event bus | Cancel calls `BookingSyncService` directly | P2 | Emit `order.cancelled` → handler → `sync_cancellation()` |
| G-M011 | Billing | NET batch invoice generation missing | P2 | `billing_engine` scheduled job per `billing_cycle` |
| G-M012 | Billing | `Invoice.pdf_url` never populated | P2 | PDF generation in `billing_engine` |
| G-M013 | Security | Dev bypass risk if misconfigured in prod | P1 | Hard-fail `clerk_dev_bypass` when `app_env=production` (platform) |

### Open — feature (non-foundation)

| ID | Category | Gap | Priority | Recommended fix |
|----|----------|-----|----------|-----------------|
| G-M101 | UI | Saved addresses / recipients — backend only | P2 | Settings sub-pages or book-page picker |
| G-M102 | UI | Webhook management — backend only | P2 | Extend `/api` page with webhook CRUD |
| G-M103 | UI | Team role change — backend only | P3 | Role dropdown on `/team` |
| G-M104 | UI | API key scopes not in create form | P3 | Scope checkboxes on `/api` |
| G-M105 | Bulk | XLSX upload accepted, CSV-only parser | P2 | Add openpyxl parser or restrict UI to `.csv` |
| G-M106 | Templates | `MerchantBookingTemplate` model unused | P3 | Service + API + UI |
| G-M107 | Support | RBAC `support` module, no routes | P3 | `merchant_engine/support_service.py` + routes |
| G-M108 | Tracking | No live map / WebSocket | P3 | Poll interval or shared tracking component |
| G-M109 | Reports | `average_delivery_minutes` null | P3 | Compute from `OrderEvent` timestamps |
| G-M110 | Dashboard | Notifications array empty | P3 | Wire `notification_engine` merchant feed |
| G-M111 | Team | Clerk org invitation not synced | P3 | Clerk Organizations API integration |
| G-M112 | Infra | No Docker service for merchant-portal | P3 | Add to `infrastructure/docker/` compose |
| G-M113 | Repo | `apps/merchant/` placeholder | P3 | Complete migration or remove placeholder |

---

## Architecture compliance gaps

### Fleetbase boundary — ✅ Compliant

```
Merchant Portal → Porterchain API → merchant_engine → Event Bus → fleetbase_engine → Adapter → Fleetbase
```

No direct Fleetbase communication from the portal. **No remediation required.**

### Layered architecture — ⚠ One inconsistency

| Layer | Gap | Impact |
|-------|-----|--------|
| Application Service | Direct `BookingSyncService` on cancel | Inconsistent async pattern; harder to add webhook/notification side effects |
| Worker | Webhook processor was stub | Merchant integrations could not receive order events |

### Business logic placement — ✅ Compliant

| Forbidden location | Merchant status |
|--------------------|-----------------|
| React components | ✅ No pricing/state rules |
| Routers | ✅ Delegate only |
| Fleetbase adapter | ✅ Mapping only |
| Repositories | ✅ Persistence only |

---

## Priority matrix

| Priority | Count | Focus |
|----------|-------|-------|
| **P1 — Foundation** | 4 closed, 1 open (G-M013 platform) | API key auth, webhook delivery |
| **P2 — Operations** | 6 open | Billing automation, UI parity, cancel event path |
| **P3 — Polish** | 10 open | Templates, live tracking, infra, Clerk sync |

---

## Remediation roadmap

### Phase 1 — Foundation (this audit) ✅

1. Add `/v1/merchant-api` with `X-Api-Key` authentication
2. Scope enforcement: `shipments:read`, `shipments:write`
3. Implement `WebhookDeliveryService` with HMAC-SHA256 per `SECURITY.md`
4. Store encrypted webhook signing secrets

### Phase 2 — Event consistency (recommended next)

1. Refactor cancel to event-driven Fleetbase sync
2. Wire `sync_return/damage/claim` to order exception events
3. NET batch billing job in `billing_engine`

### Phase 3 — UI parity

1. Addresses / recipients / webhooks settings UI
2. Team role management
3. API key scope selection
4. Bulk XLSX support or UI restriction

### Phase 4 — Enhancements

1. Booking templates
2. Merchant support module
3. Live tracking map
4. Docker + path migration cleanup

---

## Verification checklist

| Requirement (masterrule) | Before | After |
|--------------------------|--------|-------|
| Portal → API only | ✅ | ✅ |
| No Fleetbase from UI | ✅ | ✅ |
| Business logic in services | ✅ | ✅ |
| API key programmatic access | ❌ | ✅ |
| Webhook fanout delivery | ❌ | ✅ |
| Fleetbase via adapter on dispatch | ✅ | ✅ |
| Server-persisted orders | ✅ | ✅ |
| Clerk auth on portal | ✅ | ✅ |
| RBAC module checks | ✅ | ✅ |

---

## Dependencies

| Gap | Blocked by | Blocks |
|-----|------------|--------|
| G-M003 webhook delivery | G-M004 secret storage | Merchant ERP integrations |
| G-M001 API router | G-M002 key auth | B2B automation |
| G-M011 batch billing | `billing_engine` scheduler | `merchant.invoice_generated` events |
| G-M108 live tracking | Platform WebSocket policy (admin live-map only today) | Real-time merchant dashboard |

---

_Update this document when closing gaps. Intentional exceptions must update [masterrule.md](./masterrule.md) first (§20.10)._
