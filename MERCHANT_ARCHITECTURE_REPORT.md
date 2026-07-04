# Merchant Portal — Architecture Report

**Date:** June 30, 2026  
**Authority:** [masterrule.md](./masterrule.md)

---

## Layered communication model

```
Merchant Portal (Next.js 3001)
        │  Clerk JWT + X-Merchant-Org-Id
        ▼
FastAPI (`/v1/merchant/*`, `/v1/merchant-api/*`)
        │  require_module() / API-key scopes
        ▼
Application Services (`merchant_engine/*`)
        │  orchestrate, never duplicate
        ▼
Domain Engines
  ├── pricing_engine/
  ├── billing_engine/
  ├── reporting_engine/
  ├── booking_engine/
  ├── fleetbase_engine/  (adapter only)
  └── notification_engine/
        │
        ▼
Event Bus (`platform/bus.py` → `porterchain_event_bus`)
        │
        ├──► Worker queues (webhooks, notifications)
        └──► Fleetbase Adapter (`services/fleetbase_integration.py`)
                    │
                    ▼
              Fleetbase HTTP API
```

**Rule:** UI never calls Fleetbase, Stripe, OSRM, Valhalla, or Google directly for business logic. Maps render client-side; routing/ETA server-side via `MapsService`.

---

## Portal structure

| Route | Client | Primary service |
|-------|--------|-----------------|
| `/dashboard` | `DashboardClient` | `MerchantDashboardService` |
| `/book` | `BookDeliveryClient` | `MerchantBookingFlowService` |
| `/bulk` | `bulk/page` | `MerchantBulkService` |
| `/orders` | `orders/page` | `MerchantOrdersService` |
| `/orders/[id]` | `Order360View` | `MerchantOrdersService` + `MerchantTrackingService` |
| `/track` | `track/page` | `MerchantTrackingService` |
| `/billing` | `BillingClient` | `MerchantBillingService` |
| `/reports` | `ReportsClient` | `MerchantReportsService` |
| `/api` | `IntegrationsClient` | `MerchantIntegrationsService` + `gateway_engine` |
| `/team` | `TeamClient` | `MerchantTeamService` |
| `/settings` | `SettingsClient` | `MerchantSettingsService` + `MerchantSupportBridgeService` |

---

## Authentication & RBAC

| Surface | Auth | Authorization |
|---------|------|---------------|
| Portal | Clerk Bearer + org header | `MerchantContext` + `require_module()` |
| Programmatic API | `X-Api-Key` | Scopes + `MerchantApiGatewayMiddleware` rate limits |

**Single RBAC source:** `merchant_engine/rbac.py` → `MODULE_PERMISSIONS`, `permissions_catalog()`.

Roles: `merchant_owner`, `merchant_admin`, `merchant_ops`, `merchant_finance`, `merchant_readonly`.

---

## Booking flow

```
BookDeliveryClient
  → POST /booking/preview
  → MerchantBookingFlowService.preview()
      → pricing_engine.calculate_merchant()
      → fleetbase_engine.MerchantSyncService (address validation)
  → POST /booking/confirm
  → MerchantBookingService.create_shipment()
      → emit_event(MERCHANT_BOOKING_CREATED)
      → transition_to_dispatch_ready → event bus
      → fleetbase_engine.BookingSyncService (via handler, not direct)
```

---

## Tracking flow

```
MerchantTrackingService
  → booking_engine.tracking_service.TrackingService
  → fleetbase_engine.integration_bridge.FleetbaseIntegrationBridge
  → services/fleetbase_integration.py (adapter factory)
  → MapsService: OSRM (ETA), Valhalla (route polyline)
  → Google Maps: client render only (@vis.gl/react-google-maps)
```

---

## Billing flow

```
BillingClient → MerchantBillingService
  → billing_engine/merchant_service.py (serialize, NET terms, outstanding)
  → Invoice / Payment / Order models
```

No Stripe for contract merchants unless `merchant_uses_stripe()`.

---

## Reporting flow

```
ReportsClient → MerchantReportsService
  → reporting_engine/merchant_service.py (SQL aggregates)
  → MerchantOrdersService, MerchantBillingService (orchestration)
  → Saved/scheduled → merchant.profile JSON
```

---

## Integrations flow

```
IntegrationsClient → MerchantIntegrationsService
  → MerchantApiKeyService (keys/webhooks)
  → gateway_engine (rate limits, usage logs, docs)
  → webhook_delivery_service → worker fanout on domain events
```

---

## Support & claims (bridge pattern)

```
SettingsClient / Order360View
  → MerchantSupportBridgeService
  → AdminSupportService.list_enriched(merchant_id=…)
  → AdminClaimsService.list_enriched(merchant_id=…)
  → Ticket/claim create with merchant actor + emit_event
```

No duplicate support/claims business logic in merchant_engine.

---

## Realtime

```
useMerchantRealtime
  → WebSocket /v1/notifications/ws
  → notification_engine.realtime.realtime_hub
  → on message: refresh dashboard/orders/tracking (poll 60s fallback)
```

---

## Data ownership

| Entity | Model | Merchant scope |
|--------|-------|----------------|
| Merchant | `merchants` | `clerk_org_id` |
| Orders | `orders` | `merchant_id` |
| API keys | `merchant_api_keys` | per merchant |
| Webhooks | `merchant_webhooks` | per merchant |
| Usage logs | `merchant_api_usage_logs` | per merchant |
| Team | `merchant_users` | per merchant |
| Settings extensions | `merchants.profile` JSON | per merchant |

---

## masterrule compliance

| Rule | Status |
|------|--------|
| UI → API only | ✅ |
| Logic in `*_engine` services | ✅ |
| Fleetbase via adapter only | ✅ Verified (grep: no direct HTTP in merchant_engine) |
| Pricing via pricing_engine | ✅ |
| No duplicate RBAC | ✅ |
| Event bus for side effects | ✅ |
