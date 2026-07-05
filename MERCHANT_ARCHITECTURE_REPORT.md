# Merchant Portal — Architecture Report

**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [MERCHANT_FLOW.md](docs/architecture/MERCHANT_FLOW.md) (canonical doc).

**Authority:** [masterrule.md](./masterrule.md)  
**See also:** [MERCHANT_PRODUCTION_READINESS.md](./MERCHANT_PRODUCTION_READINESS.md) · [docs/architecture/MERCHANT_FLOW.md](./docs/architecture/MERCHANT_FLOW.md)

---

## Layered communication model

```
Merchant Portal (Next.js :3001)
        │  Clerk JWT + X-Merchant-Org-Id + X-Merchant-Role
        ▼
FastAPI (`/v1/merchant/*`, `/v1/merchant-api/*`)
        │  require_module() / shipments:* scopes / gateway middleware
        ▼
Application Services (`merchant_engine/*`)
        │  orchestrate, never duplicate
        ▼
Domain Engines
  ├── pricing_engine/
  ├── billing_engine/
  ├── reporting_engine/ (via MerchantReportsService)
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
              Fleetbase HTTP API (:8000)
```

**Rule:** UI never calls Fleetbase, Stripe, OSRM, Valhalla, or Google for business logic. Maps render via `@porterchain/maps`; routing/ETA server-side via `MapsService` (default `routing_engine=valhalla`).

---

## Portal structure

| Route          | Client               | Primary service                                            |
| -------------- | -------------------- | ---------------------------------------------------------- |
| `/dashboard`   | `DashboardClient`    | `MerchantDashboardService`                                 |
| `/book`        | `BookDeliveryClient` | `MerchantBookingFlowService` + `MerchantBookingService`    |
| `/bulk`        | `bulk/page`          | `MerchantBulkService`                                      |
| `/orders`      | `orders/page`        | `MerchantOrdersService`                                    |
| `/orders/[id]` | `Order360View`       | `MerchantOrdersService` + `MerchantTrackingService`        |
| `/track`       | `track/page`         | `MerchantTrackingService`                                  |
| `/billing`     | `BillingClient`      | `MerchantBillingService`                                   |
| `/reports`     | `ReportsClient`      | `MerchantReportsService`                                   |
| `/api`         | `IntegrationsClient` | `MerchantIntegrationsService` + `gateway_engine`           |
| `/team`        | `TeamClient`         | `MerchantTeamService`                                      |
| `/settings`    | `SettingsClient`     | `MerchantSettingsService` + `MerchantSupportBridgeService` |

---

## Authentication & RBAC

| Surface          | Auth                            | Authorization                                              |
| ---------------- | ------------------------------- | ---------------------------------------------------------- |
| Portal           | Clerk Bearer + org/role headers | `MerchantContext` + `require_module()`                     |
| Programmatic API | `X-Api-Key`                     | `shipments:read` / `shipments:write` + gateway rate limits |
| Notifications WS | Clerk JWT + `org_id` query      | `notification_engine/principal.py`                         |

**RBAC source:** `merchant_engine/rbac.py` → `MODULE_PERMISSIONS`

Roles: `merchant_owner`, `merchant_admin`, `merchant_ops`, `merchant_finance`, `merchant_readonly`.

Production: `PortalRateLimitMiddleware` applies to `/v1/merchant/*` (skipped when `APP_ENV=local`).

---

## Booking flow

```
BookDeliveryClient
  → POST /v1/merchant/booking/preview
  → MerchantBookingFlowService.preview()
      → pricing_engine.calculate_merchant()
      → fleetbase_engine.MerchantSyncService (address validation)
  → POST /v1/merchant/booking/confirm (or POST /bookings)
  → MerchantBookingService.create_shipment()
      → emit_event(merchant.booking_created)
      → transition_to_dispatch_ready → order.dispatch_ready
      → fleetbase_sync_handler → BookingSyncService (via event bus)
```

---

## Tracking flow

```
MerchantTrackingService
  → booking_engine.tracking_service.TrackingService
  → fleetbase_engine.integration_bridge
  → services/fleetbase_integration.py
  → MapsService (Valhalla primary, OSRM when engine=osrm)
  → Google Maps: client render only (@porterchain/maps)
```

---

## Billing / reporting / integrations

| Flow           | Path                                                                        |
| -------------- | --------------------------------------------------------------------------- |
| Billing        | `MerchantBillingService` → `billing_engine/merchant_service.py` (NET terms) |
| Reports        | `MerchantReportsService` → SQL aggregates; saved/scheduled in profile JSON  |
| Integrations   | `MerchantIntegrationsService` → keys/webhooks + `gateway_engine` usage logs |
| Webhooks       | `order.*` fanout → worker → `webhook_delivery_service` (HMAC)               |
| Support/claims | `MerchantSupportBridgeService` → admin services filtered by `merchant_id`   |

---

## Realtime

```
useMerchantRealtime
  → WS /v1/notifications/ws?token=&org_id=
  → notification_engine.realtime.realtime_hub
  → on notification → refresh(); 60s poll fallback
```

---

## masterrule compliance

| Rule                                | Status |
| ----------------------------------- | ------ |
| UI → API only                       | ✅     |
| Logic in `*_engine` services        | ✅     |
| Fleetbase via adapter only          | ✅     |
| Pricing via pricing_engine          | ✅     |
| Single RBAC source                  | ✅     |
| Event bus for dispatch side effects | ✅     |
| Cancel sync direct (G-M010)         | ⚠      |

---

## Related

| Document                                                                                     | Purpose                       |
| -------------------------------------------------------------------------------------------- | ----------------------------- |
| [MERCHANT_PRODUCTION_READINESS.md](./MERCHANT_PRODUCTION_READINESS.md)                       | Readiness and open gaps       |
| [docs/archive/MERCHANT_COMPONENT_MATRIX.md](./docs/archive/MERCHANT_COMPONENT_MATRIX.md)     | Historical UI ↔ API mapping   |
| [docs/archive/MERCHANT_INTEGRATION_MATRIX.md](./docs/archive/MERCHANT_INTEGRATION_MATRIX.md) | Historical endpoint inventory |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)                           | Platform certification        |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
