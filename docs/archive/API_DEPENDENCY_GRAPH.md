# Porterchain — API Dependency Graph

**Last verified:** 2026-07-04  
**Orchestrator:** `apps/api/` — Porterchain API `:8001`

All paths flow **UI → Router → Application Service**. No router calls Fleetbase HTTP directly.

---

## Router → Service map

```
/v1/quotes, /v1/bookings          → booking_engine (Quote, Booking, Confirmation, Draft)
/v1/booking-drafts                → BookingDraftService
/v1/payments                      → PaymentService
/v1/orders/{tracking}             → TrackingService
/v1/customers/*                   → CustomerService
/v1/merchant/*                    → merchant_engine/* (portal services)
/v1/merchant-api/*                → merchant_engine (API-key: bookings, orders, track, cancel)
/v1/admin/dashboard               → AdminDashboardService
/v1/admin/orders                  → AdminOrdersService
/v1/admin/booking-drafts          → AdminBookingDraftService
/v1/admin/claims                  → AdminClaimsService
/v1/admin/finance                 → AdminFinanceService
/v1/admin/pricing                 → AdminPricingService
/v1/admin/support                 → AdminSupportService
/v1/admin/reports                 → AdminReportsService
/v1/admin/settings                → AdminSettingsService
/v1/admin/operations              → ControlTowerService, LiveMapService
/v1/admin/operations/live-map/ws  → LiveMapService (WebSocket)
/v1/admin/drivers                 → AdminDriverService, Driver360Service
/v1/admin/merchants               → AdminMerchantService, Merchant360Service
/v1/admin/crm                     → CrmSalesService
/v1/auth/sso/fleetbase            → SsoService → FleetbaseSsoClient (adapter)
/webhooks/stripe                  → StripeWebhookService → PaymentService, ConfirmationService
/webhooks/fleetbase               → WebhookIngressService → WebhookProcessor
/driver-api/v1/*                  → DriverAuthService, DriverFleetbaseBridge
/internal/*                       → platform registry (gateway)
```

---

## Service → Service dependencies

### booking_engine

```
QuoteService ──────────► pricing_engine.get_pricing_service()
BookingService ────────► QuoteService, PaymentService, BookingDraftService
PaymentService ────────► Stripe adapter (stripe_service)
ConfirmationService ───► PaymentService, BookingDraftService, order_transitions
TrackingService ───────► FleetbaseIntegrationBridge.fetch_tracking
BookingDraftService ───► QuoteRepository, BookingDraftRepository
fleetbase_sync_handler ► BookingSyncService (via event bus)
notification_handler ──► NotificationService / notification.queued
```

### fleetbase_engine

```
FleetbaseIntegrationBridge ──► get_fleetbase_integration() → FleetbaseAdapter
BookingSyncService ──────────► IntegrationBridge, RetryQueue, AuditLogger
WebhookIngressService ───────► adapter.process_webhook → emit_event
WebhookProcessor ────────────► IntegrationBridge, StatusTranslator, order_transitions
MerchantSyncService ─────────► validation only (no Fleetbase HTTP)
```

### merchant_engine

```
MerchantBookingService ──► MerchantSyncService (validate), order_transitions, BookingSyncService (cancel)
MerchantBillingService ──► Invoice/Payment queries
MerchantReportsService ──► read aggregates
MerchantDashboardService ► Order/Invoice counts
```

### admin_engine

```
AdminOrdersService ──────► Order, Invoice, Claim, Support cross-joins
AdminFinanceService ─────► Invoice, Payment, SettlementService
AdminClaimsService ──────► Order, Merchant, Customer, Driver
AdminSupportService ─────► Order, Customer, Merchant, Driver, Finance refs
AdminReportsService ─────► all admin services (read-only aggregates)
LiveMapService ──────────► Driver, Vehicle, Order, DriverLocationPing (no Fleetbase HTTP)
ControlTowerService ─────► Order state aggregates
AdminDriverService ──────► BookingSyncService.push_driver/vehicle
AdminOperationsService ──► order_transitions, LiveMapService
```

### billing_engine

```
SettlementService ───────► BillingLedgerEntry, Stripe refs
process_billing_job ─────► triggered by payment.succeeded event
```

### notification_engine

```
NotificationOrchestrator ──► DeliveryService, templates, emit_event(notification.sent)
DeliveryService ───────────► worker queues (email, SMS log-only, push)
WebhookDeliveryService ────► merchant outbound POST (HMAC, retries)
```

### driver_engine

```
DriverAuthService ───────► Clerk, driver JWT
DriverFleetbaseBridge ───► FleetbaseAdapter (GPS, POD, route, online toggle)
```

---

## Service → External adapter dependencies

| Service                      | Adapter               | External system              |
| ---------------------------- | --------------------- | ---------------------------- |
| `FleetbaseIntegrationBridge` | `FleetbaseAdapter`    | Fleetbase `:8000`            |
| `PaymentService`             | `stripe_service`      | Stripe Checkout              |
| `QuoteService`               | `porterchain_pricing` | Pricing library (local)      |
| `SsoService`                 | `FleetbaseSsoClient`  | Fleetbase SSO                |
| `NotificationOrchestrator`   | worker queues         | SMTP, FCM push; SMS log-only |
| `WebhookDeliveryService`     | HTTP client           | Merchant webhook endpoints   |
| `TrackingService`            | Fleetbase adapter     | Fleetbase tracker API        |

---

## Frontend → API dependency graph

```
website (:3000)
  ├── POST /v1/quotes
  ├── POST /v1/bookings
  ├── GET/PATCH /v1/booking-drafts/*
  ├── POST /v1/payments/*
  ├── GET /v1/orders/{tracking}
  └── GET /v1/customers/me/*

merchant-portal (:3001)
  └── GET/POST /v1/merchant/{dashboard,orders,bookings,bulk,billing,reports,api-keys,team,profile}

admin (:3002)
  └── GET/PATCH /v1/admin/{dashboard,orders,merchants,drivers,crm,operations,claims,finance,pricing,support,reports,settings,booking-drafts}
  └── WS /v1/admin/operations/live-map/ws
  └── POST /v1/auth/sso/fleetbase

driver-portal (:3003)
  └── BFF /api/driver → /driver-api/v1/{dashboard,stops,routes,earnings,wallet,emergency,documents,...}

customer (:3004)
  └── GET /v1/customers/me/{dashboard,support,rebook}

mobile-driver (Expo)
  └── /driver-api/v1/{auth,routes,stops,location,pod,...}

mobile-customer (Expo)
  └── /v1/customers/me/* (Clerk bearer)

merchant-api (machine)
  └── /v1/merchant-api/{bookings,orders,track/*}
```

**No frontend → Fleetbase edge exists.**

---

## Event bus API (internal)

```
emit_event() [booking_engine/_core.py]
  → DomainEvent (PostgreSQL)
  → publish_domain_event() [platform/bus.py]
  → porterchain_event_bus.publish()
  → handlers/__init__.py subscribers
  → fleetbase_sync_handler | notification_handler | queue publisher
```

---

## Worker queue API (internal)

| Queue      | Producer                      | Consumer                                                   |
| ---------- | ----------------------------- | ---------------------------------------------------------- |
| `BILLING`  | `payment.succeeded`           | `worker/processors/billing.py`                             |
| `EMAILS`   | `notification.queued`         | `worker/processors/notifications.py`                       |
| `SMS`      | `notification.queued`         | notifications processor                                    |
| `PUSH`     | `notification.queued`         | notifications processor                                    |
| `WEBHOOKS` | `webhook.received`, `order.*` | `worker/processors/webhooks.py` + `WebhookDeliveryService` |
| `DISPATCH` | —                             | `worker/processors/dispatch.py` (stub)                     |

---

## Health & observability endpoints

| Endpoint            | Depends on                        |
| ------------------- | --------------------------------- |
| `GET /health`       | DB, Redis, Fleetbase adapter ping |
| `GET /health/live`  | process                           |
| `GET /health/ready` | DB + Redis                        |
| `GET /metrics`      | queue depths, request metrics     |

---

## Anti-patterns checked

| Pattern                             | Status                                                |
| ----------------------------------- | ----------------------------------------------------- |
| Duplicate order APIs                | ❌ None — single `AdminOrdersService` + merchant read |
| Parallel Fleetbase clients          | ❌ None — single `get_fleetbase_integration()`        |
| Router business logic               | ⚠️ Minimal — mostly thin                              |
| Service → Fleetbase without adapter | ❌ None found                                         |

---

## Related documents

| Document                                                                     | Purpose                 |
| ---------------------------------------------------------------------------- | ----------------------- |
| [API_FLOW_DIAGRAM.md](./API_FLOW_DIAGRAM.md)                                 | Request flow diagrams   |
| [docs/architecture/API_DEPENDENCY.md](./docs/architecture/API_DEPENDENCY.md) | Client matrix + mermaid |
| [INTEGRATIONS.md](./INTEGRATIONS.md)                                         | External integrations   |
| [EVENT_BUS.md](./EVENT_BUS.md)                                               | Internal event bus      |
