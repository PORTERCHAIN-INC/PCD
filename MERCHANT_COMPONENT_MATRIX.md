# Merchant Portal — Component Matrix

**Reference:** [masterrule.md](./masterrule.md) v3.1 · [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)  
**Date:** June 30, 2026

Maps every Merchant Portal surface to its API endpoint, application service, and data layer.

**Legend:** ✅ Wired end-to-end · ⚠ Backend only or partial · ❌ Missing · 🔑 API key auth (programmatic)

---

## 1. UI → API → Service matrix

| Portal route | UI component | API endpoint | Auth | Service | Repository / model |
|--------------|--------------|--------------|------|---------|-------------------|
| `/dashboard` | `DashboardClient.tsx` | `GET /v1/merchant/dashboard` | Clerk | `MerchantDashboardService` | `Order`, `Invoice` aggregates |
| `/book` | `book/page.tsx` | `POST /v1/merchant/bookings` | Clerk | `MerchantBookingService` | `Order` |
| `/bulk` | `bulk/page.tsx` | `POST /v1/merchant/bulk/upload` | Clerk | `MerchantBulkService` | `BulkImportJob` |
| `/bulk` | `bulk/page.tsx` | `POST /v1/merchant/bulk/{id}/confirm` | Clerk | `MerchantBulkService` | `BulkImportJob`, `Order` |
| `/orders` | `orders/page.tsx` | `GET /v1/merchant/orders` | Clerk | `MerchantOrdersService` | `Order` |
| `/orders/[id]` | `orders/[order_id]/page.tsx` | `GET /v1/merchant/orders/{id}` | Clerk | `MerchantOrdersService` | `Order` |
| `/orders` | `orders/page.tsx` | `POST /v1/merchant/orders/{id}/cancel` | Clerk | `MerchantBookingService` | `Order`, `OrderEvent` |
| `/orders` | `orders/page.tsx` | `POST /v1/merchant/orders/{id}/duplicate` | Clerk | `MerchantBookingService` | `Order` |
| `/track` | `track/page.tsx` | `GET /v1/merchant/track/{number}` | Clerk | `MerchantOrdersService` | `Order`, `OrderEvent` |
| `/billing` | `billing/page.tsx` | `GET /v1/merchant/billing/statement` | Clerk | `MerchantBillingService` | `Order`, `Invoice` |
| `/billing` | `billing/page.tsx` | `GET /v1/merchant/billing/invoices` | Clerk | `MerchantBillingService` | `Invoice` |
| `/reports` | `reports/page.tsx` | `GET /v1/merchant/reports/summary` | Clerk | `MerchantReportsService` | `Order`, `Invoice` |
| `/settings` | `settings/page.tsx` | `GET /v1/merchant/profile` | Clerk | `MerchantProfileService` | `Merchant` |
| `/settings` | `settings/page.tsx` | `PATCH /v1/merchant/profile` | Clerk | `MerchantProfileService` | `Merchant` |
| — | — | `GET /v1/merchant/addresses` | Clerk | `MerchantProfileService` | `SavedAddress` |
| — | — | `POST /v1/merchant/addresses` | Clerk | `MerchantProfileService` | `SavedAddress` |
| — | — | `GET /v1/merchant/recipients` | Clerk | `MerchantProfileService` | `MerchantRecipient` |
| — | — | `POST /v1/merchant/recipients` | Clerk | `MerchantProfileService` | `MerchantRecipient` |
| `/team` | `team/page.tsx` | `GET /v1/merchant/team` | Clerk | `MerchantTeamService` | `MerchantUser` |
| `/team` | `team/page.tsx` | `POST /v1/merchant/team/invite` | Clerk | `MerchantTeamService` | `MerchantUser` |
| `/team` | `team/page.tsx` | `DELETE /v1/merchant/team/{id}` | Clerk | `MerchantTeamService` | `MerchantUser` |
| — | — | `PATCH /v1/merchant/team/{id}/role` | Clerk | `MerchantTeamService` | `MerchantUser` |
| `/api` | `api/page.tsx` | `GET /v1/merchant/api-keys` | Clerk | `MerchantApiKeyService` | `MerchantApiKey` |
| `/api` | `api/page.tsx` | `POST /v1/merchant/api-keys` | Clerk | `MerchantApiKeyService` | `MerchantApiKey`, `MerchantAuditLog` |
| `/api` | `api/page.tsx` | `DELETE /v1/merchant/api-keys/{id}` | Clerk | `MerchantApiKeyService` | `MerchantApiKey` |
| — | — | `GET /v1/merchant/webhooks` | Clerk | `MerchantApiKeyService` | `MerchantWebhook` |
| — | — | `POST /v1/merchant/webhooks` | Clerk | `MerchantApiKeyService` | `MerchantWebhook` |
| — | — | `GET /v1/merchant/orders/{id}/tracking` | Clerk | `MerchantOrdersService` | `OrderEvent` (alias) |

---

## 2. Programmatic API matrix (`/v1/merchant-api/*`)

| Endpoint | Auth | Scope | Service | Portal UI |
|----------|------|-------|---------|-----------|
| `POST /v1/merchant-api/bookings` | 🔑 `X-Api-Key` | `shipments:write` | `MerchantBookingService` | — (API consumers) |
| `GET /v1/merchant-api/orders` | 🔑 | `shipments:read` | `MerchantOrdersService` | — |
| `GET /v1/merchant-api/orders/{id}` | 🔑 | `shipments:read` | `MerchantOrdersService` | — |
| `GET /v1/merchant-api/track/{number}` | 🔑 | `shipments:read` | `MerchantOrdersService` | — |
| `POST /v1/merchant-api/orders/{id}/cancel` | 🔑 | `shipments:write` | `MerchantBookingService` | — |

Delegates to the **same** application services as `/v1/merchant/*` — no duplicate business logic.

---

## 3. Shared infrastructure components

| Component | Path | Used by |
|-----------|------|---------|
| `PortalShell` | `components/portal/PortalShell.tsx` | All portal routes |
| `StatCard` | `components/portal/StatCard.tsx` | Dashboard |
| `MerchantAuthProvider` | `components/providers/MerchantAuthProvider.tsx` | App root |
| `AppClerkProvider` | `components/providers/AppClerkProvider.tsx` | App root |
| `api.ts` | `lib/api.ts` | All data-fetching pages |
| `middleware.ts` | `middleware.ts` | Route protection |
| `AddressAutocompleteInput` | `@porterchain/maps` | Book page |

---

## 4. Backend module matrix

| Module | Router | Services | Models |
|--------|--------|----------|--------|
| Dashboard | `merchant.py` | `MerchantDashboardService` | `Order`, `Invoice` |
| Booking | `merchant.py`, `merchant_api.py` | `MerchantBookingService`, `MerchantSyncService` | `Order` |
| Bulk | `merchant.py` | `MerchantBulkService` | `BulkImportJob`, `Order` |
| Orders | `merchant.py`, `merchant_api.py` | `MerchantOrdersService`, `TrackingService` | `Order`, `OrderEvent` |
| Billing | `merchant.py` | `MerchantBillingService` | `Invoice` |
| Reports | `merchant.py` | `MerchantReportsService` | `Order` |
| Profile | `merchant.py` | `MerchantProfileService` | `Merchant`, `SavedAddress`, `MerchantRecipient` |
| Team | `merchant.py` | `MerchantTeamService` | `MerchantUser` |
| API keys | `merchant.py` | `MerchantApiKeyService` | `MerchantApiKey`, `MerchantWebhook`, `MerchantAuditLog` |
| Auth | — | — | `Merchant`, `MerchantUser` |
| RBAC | — | `rbac.py` | — |
| Fleetbase sync | — | `fleetbase_engine/*` via events | `Order.fleetbase_order_id` |
| Webhook delivery | worker queue | `WebhookDeliveryService` | `MerchantWebhook` |

---

## 5. Admin vs Merchant API separation

| Concern | Merchant self-service | Admin staff |
|---------|----------------------|-------------|
| Prefix | `/v1/merchant/*`, `/v1/merchant-api/*` | `/v1/admin/merchants/*` |
| Auth | Clerk + org headers / API key | Clerk admin JWT |
| Router | `routers/merchant.py`, `routers/merchant_api.py` | `routers/merchants.py` |
| Services | `merchant_engine/*` | `admin_engine/merchant_service.py`, `Merchant360Service` |
| Audience | Merchant users | Porterchain operations |

**Not duplicates** — different authorization boundaries and data aggregation depth.

---

## 6. Event bus matrix (merchant path)

| Event | Emitter | Handler | Downstream |
|-------|---------|---------|------------|
| `merchant.booking_created` | `MerchantBookingService` | — | Audit |
| `order.dispatch_ready` | `transition_to_dispatch_ready` | `fleetbase_sync_handler` | Fleetbase adapter |
| `order.cancelled` | `transition_order_state` | — (cancel sync direct today) | Fleetbase adapter |
| `order.*` | Various | `_handle_merchant_webhook_fanout` | Worker → `WebhookDeliveryService` |
| `merchant.api_key_generated` | `MerchantApiKeyService` | — | Audit |

---

## 7. Fleetbase integration matrix

| Trigger | Service chain | Adapter call |
|---------|---------------|--------------|
| New merchant booking | `MerchantBookingService` → `transition_to_dispatch_ready` → event | `BookingSyncService.push_order` |
| Bulk confirm | `MerchantBulkService` → same path per order | Same |
| Cancel | `MerchantBookingService.cancel_order` → direct | `BookingSyncService.sync_cancellation` |
| Inbound status | Fleetbase webhook → `WebhookProcessor` | — (updates Porterchain mirror) |
| Tracking UI | `MerchantOrdersService` → `OrderEvent` | — (reads Porterchain DB) |

**Merchant Portal never appears in this column** — correct per masterrule §7.

---

## 8. Coverage summary

| Category | Total endpoints | UI wired | Backend only | API-key |
|----------|----------------|----------|--------------|---------|
| Dashboard | 1 | 1 | 0 | 0 |
| Booking | 1 | 1 | 0 | 1 |
| Bulk | 2 | 2 | 0 | 0 |
| Orders | 5 | 4 | 1 (tracking alias) | 3 |
| Billing | 2 | 2 | 0 | 0 |
| Reports | 1 | 1 | 0 | 0 |
| Profile | 2 | 2 | 0 | 0 |
| Addresses | 2 | 0 | 2 | 0 |
| Recipients | 2 | 0 | 2 | 0 |
| Team | 4 | 3 | 1 | 0 |
| API keys | 3 | 3 | 0 | 0 |
| Webhooks | 2 | 0 | 2 | 0 |
| **Programmatic** | 5 | — | — | 5 |

**UI coverage:** 21/27 Clerk endpoints (78%)  
**Foundation coverage:** 5/5 programmatic endpoints (100% after this audit)

---

## 9. File index

### Frontend
```
apps/merchant-portal/src/app/(portal)/**/page.tsx
apps/merchant-portal/src/components/portal/
apps/merchant-portal/src/lib/api.ts
apps/merchant-portal/src/middleware.ts
```

### Backend
```
apps/api/src/porterchain_api/routers/merchant.py
apps/api/src/porterchain_api/routers/merchant_api.py
apps/api/src/porterchain_api/auth/merchant.py
apps/api/src/porterchain_api/auth/merchant_api.py
apps/api/src/porterchain_api/merchant_engine/
apps/api/src/porterchain_api/merchant_models.py
apps/api/src/porterchain_api/schemas_merchant.py
```

### Integration
```
apps/api/src/porterchain_api/fleetbase_engine/
services/fleetbase-adapter/
services/event-bus/porterchain_event_bus/handlers/__init__.py
apps/worker/processors/webhooks.py
```

---

_Matrix updated per masterrule §19 — reuse existing services; no parallel implementations._
