# Porterchain — Module Integration Matrix


**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [INTEGRATIONS.md](INTEGRATIONS.md) (canonical doc).

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Companion:** [MAPS_ARCHITECTURE_AUDIT.md](./MAPS_ARCHITECTURE_AUDIT.md), [GAP_ANALYSIS.md](./GAP_ANALYSIS.md)

---

## End-to-end audit (June 30, 2026)

| Flow                                                 | Status       |
| ---------------------------------------------------- | ------------ |
| Customer → Stripe → Order → Fleetbase → Driver → POD | ✅           |
| Merchant → NET terms → Order → Fleetbase → POD       | ✅           |
| Admin unified dispatch (no source split)             | ✅           |
| `order_source` / `order_type` on all new orders      | ✅           |
| API-key merchant booking                             | ✅           |
| Merchant webhook delivery                          | ✅           |
| Merchant invoice run batch                           | ❌ (roadmap) |

---

## Maps & routing integration (June 30, 2026)

| Module          | Google Maps              | OSRM/Valhalla      | Fleetbase    | FastAPI | Status |
| --------------- | ------------------------ | ------------------ | ------------ | ------- | ------ |
| Website         | ✅ Autocomplete, geocode | ✅ Quote preview   | ❌ Never     | ✅      | ✅     |
| Customer portal | ❌                       | ❌                 | ❌           | ✅      | ⚠️ (no tracking map) |
| Mobile driver   | ❌                       | via API routing    | via adapter  | ✅      | ✅                   |
| Mobile customer | ❌                       | via API            | ❌           | ✅      | ⚠️ 62% readiness     |
| Merchant portal | ✅ Book autocomplete     | via API pricing    | via events   | ✅      | ✅     |
| Admin           | ✅ Live map full         | ❌ (viz only)      | SSO + mirror | ✅      | ✅     |
| Driver portal   | ❌                       | ❌                 | via adapter  | ✅      | ⚠️     |
| Pricing engine  | ❌                       | ✅ Server distance | ❌           | ✅      | ✅     |
| Live map        | ✅ Viz                   | ❌                 | mirror only  | ✅ WS   | ✅     |
| Booking engine  | ❌                       | via pricing        | via events   | ✅      | ✅     |

---

**Legend:** ✅ Connected · ⚠️ Partially Connected · ❌ Missing Integration · ➖ Unused Integration

---

## Executive summary

| Layer                         | Status                                                       |
| ----------------------------- | ------------------------------------------------------------ |
| UI → Porterchain API          | ✅ All portals call `:8001` only                             |
| API → Application Services    | ✅ `*_engine` packages own business logic                    |
| Services → Event Bus          | ⚠️ Core lifecycle emitted; some catalog events not emitted   |
| Event Bus → Fleetbase Adapter | ✅ `order.dispatch_ready`, `order.driver_assigned`, webhooks |
| Fleetbase Adapter → Fleetbase | ✅ Orders, drivers, vehicles, dispatch, tracking, POD        |
| Direct Fleetbase from UI      | ✅ None found                                                |

---

## Module matrix

### Website (`website/`)

| Dimension          | Status | Notes                                                              |
| ------------------ | ------ | ------------------------------------------------------------------ |
| Business Logic     | ➖     | UI only; server validates via API                                  |
| API                | ✅     | `lib/api.ts` → `/v1/quotes`, `/bookings`, `/orders`, `/customers`  |
| Database           | ➖     | No direct DB                                                       |
| Permissions / RBAC | ✅     | Clerk session → API JWT                                            |
| Events             | ➖     | Emitted server-side on quote/booking                               |
| Fleetbase          | ✅     | Never called; `fleetbase_order_id` display only                    |
| Notifications      | ⚠️     | Receives email via booking confirmation event chain                |
| Maps               | ✅     | Autocomplete + geocode (Google); routing via Valhalla/OSRM preview |
| Audit Logs         | ➖     | Server-side draft transitions                                      |
| Realtime           | ❌     | No WebSocket; tracking is REST                                     |
| Search             | ➖     | N/A                                                                |
| Reports            | ➖     | N/A                                                                |

**Cross-module:** Booking ✅ · Customer portal (embedded) ✅ · Orders (track) ✅ · Pricing (estimate + server quote) ✅

---

### Booking (`booking_engine/` + website book flow)

| Dimension      | Status | Notes                                                     |
| -------------- | ------ | --------------------------------------------------------- |
| Business Logic | ✅     | `BookingService`, `QuoteService`, `PaymentService`        |
| API            | ✅     | `routers/quotes.py`, `payments.py`                        |
| Database       | ✅     | Quotes, bookings, payments                                |
| Permissions    | ✅     | Clerk + draft ownership                                   |
| Events         | ✅     | `quote.created`, `booking.confirmed`, `payment.succeeded` |
| Fleetbase      | ✅     | Via `order.dispatch_ready` → adapter                      |
| Notifications  | ✅     | `booking.confirmed`, `order.booked` handlers              |
| Maps           | ✅     | Address capture → geocoded on server                      |
| Audit          | ✅     | Draft transitions, domain events                          |
| Realtime       | ❌     | —                                                         |
| Search         | ➖     | —                                                         |
| Reports        | ⚠️     | Feeds admin booking-draft analytics                       |

**Cross-module:** Booking Draft ✅ · Customer ✅ · Pricing ✅ · Finance (Stripe) ✅ · Orders ✅ · Notifications ✅

---

### Booking Draft (`booking_draft_models.py`, `BookingDraftService`)

| Dimension      | Status | Notes                                                                               |
| -------------- | ------ | ----------------------------------------------------------------------------------- |
| Business Logic | ✅     | State machine per masterrule §10.2                                                  |
| API            | ✅     | `routers/booking_drafts.py`, admin `/booking-drafts`                                |
| Database       | ✅     | Server-persisted drafts                                                             |
| Permissions    | ✅     | `assert_access` on GET/PATCH                                                        |
| Events         | ⚠️     | Emits `booking_draft.*` dynamic events; catalog alias `BookingDraftCreated` missing |
| Fleetbase      | ➖     | Correct — drafts never reach Fleetbase                                              |
| Notifications  | ⚠️     | Checkout recovery template exists; not all draft events wired                       |
| Maps           | ✅     | Via quote addresses                                                                 |
| Audit          | ✅     | Every transition audited                                                            |
| Realtime       | ❌     | —                                                                                   |
| Search         | ⚠️     | Admin list/filter only                                                              |
| Reports        | ✅     | `AdminBookingDraftService.analytics`                                                |

---

### Customer (`CustomerService`, `apps/customer/`, website portal)

| Dimension      | Status | Notes                                                           |
| -------------- | ------ | --------------------------------------------------------------- |
| Business Logic | ✅     | `CustomerService`                                               |
| API            | ✅     | `/v1/customers/me/*`                                            |
| Database       | ✅     | `Customer` model                                                |
| Permissions    | ✅     | Clerk                                                           |
| Events         | ✅     | `customer.registered`, `lead.created`, `support.ticket_created` |
| Fleetbase      | ✅     | Never direct                                                    |
| Notifications  | ⚠️     | Support ticket creation has no notification handler             |
| Maps           | ❌     | Customer app has no map                                         |
| Audit          | ✅     | Domain events                                                   |
| Realtime       | ❌     | —                                                               |
| Search         | ➖     | —                                                               |
| Reports        | ⚠️     | Via CRM aggregates                                              |

**Cross-module:** Orders ✅ · Support ⚠️ · Booking ✅ · Finance (invoices in portal) ✅

---

### Merchant (`merchant_engine/`, `apps/merchant-portal/`)

| Dimension      | Status | Notes                                                  |
| -------------- | ------ | ------------------------------------------------------ |
| Business Logic | ✅     | Bookings, bulk, billing, API keys                      |
| API            | ✅     | `/v1/merchant/*`                                       |
| Database       | ✅     | `merchant_models`                                      |
| Permissions    | ✅     | `merchant_engine/rbac.py`                              |
| Events         | ✅     | `merchant.booking_created`, `order.dispatch_ready`     |
| Fleetbase      | ✅     | Event-driven dispatch; cancel via `fleetbase_engine` |
| Notifications  | ✅     | Webhook fanout via `WebhookDeliveryService` + worker   |
| Maps           | ✅     | `AddressAutocompleteInput` on book form                |
| Audit          | ✅     | API key generation events                              |
| Realtime       | ❌     | —                                                      |
| Search         | ⚠️     | Order list filter                                      |
| Reports        | ✅     | `MerchantReportsService`                               |

**Cross-module:** CRM ⚠️ · Orders ✅ · Invoices ✅ · Payments ✅ · Pricing (contracts) ✅ · CSV/Bulk ✅ · Support ❌ · Claims ❌ · Documents ❌ · Analytics ⚠️

---

### CRM (`admin_engine/crm_service.py`, `crm_sales_service.py`)

| Dimension      | Status | Notes                                         |
| -------------- | ------ | --------------------------------------------- |
| Business Logic | ✅     | Companies, leads, pipeline                    |
| API            | ✅     | `/v1/admin/crm/*`                             |
| Database       | ✅     | `crm_models`                                  |
| Permissions    | ✅     | Admin RBAC `crm` module                       |
| Events         | ⚠️     | `lead.created`; not all CRM mutations audited |
| Fleetbase      | ✅     | Never                                         |
| Notifications  | ❌     | —                                             |
| Maps           | ➖     | —                                             |
| Audit          | ⚠️     | Company CRUD wired; extend to all entities    |
| Realtime       | ❌     | —                                             |
| Search         | ✅     | CRM list filters                              |
| Reports        | ✅     | Via `AdminReportsService`                     |

---

### Drivers (`admin_engine/driver_service.py`, `driver_engine/`, `driver-portal/`)

| Dimension      | Status | Notes                                                              |
| -------------- | ------ | ------------------------------------------------------------------ |
| Business Logic | ✅     | Approval, 360, driver platform bridge                              |
| API            | ✅     | `/v1/admin/drivers`, `/driver-api/v1`                              |
| Database       | ✅     | `admin_models.Driver`                                              |
| Permissions    | ✅     | Admin RBAC + `DriverAuthService`                                   |
| Events         | ✅     | `driver.approved`, `driver.suspended`                              |
| Fleetbase      | ✅     | `push_driver`/`push_vehicle` on approve; driver bridge for GPS/POD |
| Notifications  | ⚠️     | Push queue from driver-platform                                    |
| Maps           | ❌     | Driver portal has no map UI                                        |
| Audit          | ✅     | Admin audit on approval                                            |
| Realtime       | ❌     | Location via API poll                                              |
| Search         | ✅     | Driver list                                                        |
| Reports        | ✅     | Driver360 analytics                                                |

**Cross-module:** Fleetbase ✅ · Vehicle ✅ · Orders ✅ · Tracking ✅ · Claims ⚠️ · Support ⚠️ · Performance ⚠️ · Documents ⚠️ (API exists, pages missing) · Incidents ⚠️

---

### Fleet (vehicles, maintenance, insurance — admin + Fleetbase mirror)

| Dimension      | Status | Notes                                                     |
| -------------- | ------ | --------------------------------------------------------- |
| Business Logic | ⚠️     | Vehicles in Porterchain DB; maintenance/insurance partial |
| API            | ⚠️     | Driver admin 360; no standalone fleet router              |
| Database       | ✅     | `Vehicle` model                                           |
| Permissions    | ✅     | Admin drivers/fleet modules                               |
| Events         | ⚠️     | Vehicle sync on driver approve                            |
| Fleetbase      | ✅     | `sync_vehicle` via adapter                                |
| Notifications  | ❌     | —                                                         |
| Maps           | ⚠️     | Live map shows vehicles from mirror                       |
| Audit          | ✅     | Fleetbase sync audit                                      |
| Realtime       | ⚠️     | Live map WebSocket                                        |
| Search         | ⚠️     | Via driver 360                                            |
| Reports        | ⚠️     | Dashboard fleet health card                               |

**Cross-module:** Drivers ✅ · Orders ✅ · Fleetbase ✅ · GPS ✅ · Dispatch ✅ · Maintenance ⚠️ · Insurance ⚠️

---

### Orders (`AdminOrdersService`, `merchant_engine/orders_service.py`)

| Dimension      | Status | Notes                                           |
| -------------- | ------ | ----------------------------------------------- |
| Business Logic | ✅     | `order_transitions.py` canonical state machine  |
| API            | ✅     | Admin, merchant, public tracking                |
| Database       | ✅     | `Order`, `OrderEvent`                           |
| Permissions    | ✅     | Admin + merchant scoped                         |
| Events         | ✅     | Full lifecycle (most states)                    |
| Fleetbase      | ✅     | Outbound sync + inbound webhooks                |
| Notifications  | ⚠️     | Booked/confirmed only; delivery updates partial |
| Maps           | ✅     | Admin Order360 embed map                        |
| Audit          | ✅     | Order events + domain events                    |
| Realtime       | ⚠️     | Live map; no per-order WS                       |
| Search         | ✅     | Filters on admin list                           |
| Reports        | ✅     | Operations + finance reports                    |

**Hub connections:** Booking ✅ · Draft ✅ · Customer ✅ · Merchant ✅ · CRM ⚠️ · Pricing ✅ · Payments ✅ · Invoices ✅ · Driver ✅ · Vehicle ⚠️ · Fleetbase ✅ · Tracking ✅ · Claims ✅ · Support ✅ · Notifications ⚠️ · Reports ✅ · Documents ✅ · Audit ✅ · Timeline ✅

---

### Pricing (`pricing_engine/`, `AdminPricingService`)

| Dimension      | Status | Notes                                        |
| -------------- | ------ | -------------------------------------------- |
| Business Logic | ✅     | `porterchain_pricing` library + repository   |
| API            | ✅     | Admin pricing + quote endpoints              |
| Database       | ✅     | Pricing config tables                        |
| Permissions    | ✅     | Admin `pricing` module                       |
| Events         | ✅     | `pricing.updated`                            |
| Fleetbase      | ✅     | Never                                        |
| Notifications  | ❌     | —                                            |
| Maps           | ⚠️     | Distance used in pricing; not Google routing |
| Audit          | ✅     | `log_admin_audit` on mutations               |
| Realtime       | ❌     | —                                            |
| Search         | ✅     | Contract/zone filters                        |
| Reports        | ✅     | Pricing reports slice                        |

**Cross-module:** Quotes ✅ · Draft ✅ · Booking ✅ · Merchant contracts ✅ · Orders ✅ · Finance ✅ · Reports ✅

---

### Finance (`AdminFinanceService`, `billing_engine/`, Stripe)

| Dimension      | Status | Notes                                                                       |
| -------------- | ------ | --------------------------------------------------------------------------- |
| Business Logic | ✅     | Invoices, settlements, merchant billing                                     |
| API            | ✅     | `/v1/admin/finance/*`, merchant billing                                     |
| Database       | ✅     | `Invoice`, `Payment`, `BillingLedgerEntry`                                  |
| Permissions    | ✅     | Admin `finance` module                                                      |
| Events         | ⚠️     | `payment.succeeded` → billing queue; `invoice.created` not `order.invoiced` |
| Fleetbase      | ✅     | Never                                                                       |
| Notifications  | ⚠️     | Invoice template exists; not event-driven                                   |
| Maps           | ➖     | —                                                                           |
| Audit          | ✅     | Finance mutations                                                           |
| Realtime       | ❌     | —                                                                           |
| Search         | ✅     | Invoice filters                                                             |
| Reports        | ✅     | Finance reports                                                             |

**Cross-module:** Orders ✅ · Stripe ✅ · Merchant ✅ · Driver payout ⚠️ (future) · Refunds ⚠️ · Credit notes ❌ (roadmap) · Claims ⚠️ · Reports ✅

---

### Claims (`AdminClaimsService`)

| Dimension      | Status | Notes                                                         |
| -------------- | ------ | ------------------------------------------------------------- |
| Business Logic | ✅     | Full claims lifecycle                                         |
| API            | ✅     | `/v1/admin/claims/*`                                          |
| Database       | ✅     | `Claim` model                                                 |
| Permissions    | ✅     | Admin `claims` module                                         |
| Events         | ✅     | `claim.opened`, `claim.resolved`                              |
| Fleetbase      | ⚠️     | Inbound webhook opens claim; outbound `sync_claim` audit-only |
| Notifications  | ❌     | No handler for `claim.opened`                                 |
| Maps           | ➖     | —                                                             |
| Audit          | ✅     | Domain events                                                 |
| Realtime       | ❌     | —                                                             |
| Search         | ✅     | Claim filters                                                 |
| Reports        | ✅     | Claims slice in reports                                       |

---

### Support (`AdminSupportService`)

| Dimension      | Status | Notes                                   |
| -------------- | ------ | --------------------------------------- |
| Business Logic | ✅     | Tickets, SLA, attachments               |
| API            | ✅     | `/v1/admin/support/*`, customer support |
| Database       | ✅     | Support ticket models                   |
| Permissions    | ✅     | Admin `support` module                  |
| Events         | ✅     | `support.ticket_created`                |
| Fleetbase      | ✅     | Never                                   |
| Notifications  | ❌     | No handler for ticket created           |
| Maps           | ➖     | —                                       |
| Audit          | ⚠️     | Partial                                 |
| Realtime       | ❌     | —                                       |
| Search         | ✅     | Ticket filters                          |
| Reports        | ✅     | Support metrics                         |

---

### Reports (`AdminReportsService`, `MerchantReportsService`)

| Dimension      | Status | Notes                                     |
| -------------- | ------ | ----------------------------------------- |
| Business Logic | ✅     | Aggregates only — no owned business rules |
| API            | ✅     | Admin + merchant reports endpoints        |
| Database       | ✅     | Read-only queries across modules          |
| Permissions    | ✅     | RBAC                                      |
| Events         | ➖     | Consumes data; does not emit lifecycle    |
| Fleetbase      | ✅     | Never                                     |
| Notifications  | ➖     | —                                         |
| Maps           | ➖     | —                                         |
| Audit          | ➖     | —                                         |
| Realtime       | ❌     | —                                         |
| Search         | ➖     | —                                         |
| Reports        | ✅     | Self — BI center                          |

**Data sources:** All modules ⚠️ (documents/analytics slices thin)

---

### Settings (`AdminSettingsService`)

| Dimension      | Status | Notes                              |
| -------------- | ------ | ---------------------------------- |
| Business Logic | ✅     | Integration health, module toggles |
| API            | ✅     | `/v1/admin/settings`               |
| Database       | ✅     | Settings store                     |
| Permissions    | ✅     | `settings` module                  |
| Events         | ➖     | —                                  |
| Fleetbase      | ✅     | Health check only                  |
| Notifications  | ➖     | —                                  |
| Maps           | ✅     | Google Maps key health             |
| Audit          | ⚠️     | Partial                            |
| Realtime       | ❌     | —                                  |
| Search         | ➖     | —                                  |
| Reports        | ➖     | —                                  |

---

### Notifications (`notification_engine/`)

| Dimension      | Status | Notes                                       |
| -------------- | ------ | ------------------------------------------- |
| Business Logic | ✅     | `NotificationOrchestrator`, templates       |
| API            | ➖     | Internal + worker delivery                  |
| Database       | ✅     | `NotificationDeliveryLog`                   |
| Permissions    | ➖     | System                                      |
| Events         | ✅     | `notification.queued`, `notification.sent`  |
| Fleetbase      | ➖     | Receives order events, not Fleetbase direct |
| Notifications  | ✅     | Email/SMS/push queues                       |
| Maps           | ➖     | —                                           |
| Audit          | ✅     | Delivery logs                               |
| Realtime       | ❌     | No push WS to portals                       |
| Search         | ➖     | —                                           |
| Reports        | ⚠️     | Delivery stats partial                      |

**Event sources:** Booking ✅ · Orders ⚠️ · Payments ✅ · Fleetbase ⚠️ (via webhooks → order events) · Claims ❌ · Support ❌ · Finance ⚠️

---

### Analytics (dashboard + draft analytics + 360 views)

| Dimension      | Status | Notes                       |
| -------------- | ------ | --------------------------- |
| Business Logic | ✅     | Read aggregates in services |
| API            | ✅     | Dashboard, 360, reports     |
| Database       | ✅     | Query-only                  |
| Permissions    | ✅     | RBAC                        |
| Events         | ➖     | —                           |
| Fleetbase      | ✅     | Never owns analytics        |
| Notifications  | ➖     | —                           |
| Maps           | ⚠️     | Dashboard embedded map      |
| Audit          | ➖     | —                           |
| Realtime       | ⚠️     | Dashboard polls 20s         |
| Search         | ➖     | —                           |
| Reports        | ✅     | Overlaps reports module     |

---

### Documents (order/driver document attachments)

| Dimension      | Status | Notes                                |
| -------------- | ------ | ------------------------------------ |
| Business Logic | ⚠️     | JSON blobs on models; driver doc API |
| API            | ⚠️     | Driver `/documents`; admin 360       |
| Database       | ✅     | `documents` JSON fields              |
| Permissions    | ✅     | Scoped                               |
| Events         | ❌     | No document events                   |
| Fleetbase      | ✅     | POD proofs via adapter               |
| Notifications  | ❌     | —                                    |
| Maps           | ➖     | —                                    |
| Audit          | ⚠️     | Partial                              |
| Realtime       | ❌     | —                                    |
| Search         | ❌     | —                                    |
| Reports        | ➖     | —                                    |

---

### Operations (`AdminOperationsService`, `ControlTowerService`)

| Dimension      | Status | Notes                                        |
| -------------- | ------ | -------------------------------------------- |
| Business Logic | ✅     | Dispatch queue, exceptions                   |
| API            | ✅     | `/v1/admin/operations`                       |
| Database       | ✅     | Order mirror                                 |
| Permissions    | ✅     | `operations` module                          |
| Events         | ✅     | `dispatch.assigned`, `order.driver_assigned` |
| Fleetbase      | ✅     | Assignment → adapter via events              |
| Notifications  | ⚠️     | Driver assigned template unused              |
| Maps           | ⚠️     | Ops page polls; SSO to Fleetbase console     |
| Audit          | ✅     | `AdminAuditLog`                              |
| Realtime       | ⚠️     | HTTP poll 15s                                |
| Search         | ✅     | Queue filters                                |
| Reports        | ✅     | Ops metrics                                  |

---

### Control Tower (`ControlTowerService`)

| Dimension      | Status | Notes                                |
| -------------- | ------ | ------------------------------------ |
| Business Logic | ✅     | KPI aggregation from DB mirror       |
| API            | ✅     | `/v1/admin/operations/control-tower` |
| Database       | ✅     | Read-only                            |
| Permissions    | ✅     | `operations` module                  |
| Events         | ➖     | Consumer                             |
| Fleetbase      | ✅     | Never direct                         |
| Notifications  | ➖     | —                                    |
| Maps           | ➖     | Separate live-map module             |
| Audit          | ➖     | —                                    |
| Realtime       | ⚠️     | Poll-based                           |
| Search         | ➖     | —                                    |
| Reports        | ✅     | Overlaps reports                     |

---

### Live Map (`LiveMapService`, admin live-map UI)

| Dimension      | Status | Notes                               |
| -------------- | ------ | ----------------------------------- |
| Business Logic | ✅     | DB mirror + `DriverLocationPing`    |
| API            | ✅     | REST snapshot + WebSocket           |
| Database       | ✅     | Mirror tables                       |
| Permissions    | ✅     | Admin `operations` + Clerk WS token |
| Events         | ⚠️     | Consumes tracking events            |
| Fleetbase      | ✅     | **Never direct** — mirror only      |
| Notifications  | ➖     | —                                   |
| Maps           | ✅     | Google Maps visualization           |
| Audit          | ➖     | —                                   |
| Realtime       | ✅     | WebSocket 5s + HTTP fallback        |
| Search         | ➖     | —                                   |
| Reports        | ➖     | —                                   |

**Inputs:** Drivers ✅ · Vehicles ✅ · Orders ✅ · Tracking ✅ · Fleetbase (mirror) ✅ · Traffic ✅ · Geofences ⚠️ · Incidents ⚠️

---

## Communication path compliance

```
UI → FastAPI Router → Application Service → Repository → DB
                              ↓
                         Event Bus → Worker
                              ↓
                    Fleetbase Adapter → Fleetbase
```

| Violation type                       | Found?                |
| ------------------------------------ | --------------------- |
| UI → Fleetbase direct                | ❌ None               |
| Router → Fleetbase HTTP              | ❌ None               |
| Service bypassing adapter            | ❌ None               |
| Fleetbase owning CRM/pricing/finance | ❌ Correct separation |

---

## Prioritized integration gaps (see MISSING_INTEGRATIONS.md)

1. **P0** — Fleetbase cancellation uses wrong API path (`OrderService.cancel`)
2. **P0** — `order.dispatch_requested` never emitted
3. **P1** — Notification handlers for `claim.opened`, `support.ticket_created`
4. **P1** — `fleetbase.status_updated` / `fleetbase.pod_received` not emitted on webhook
5. **P1** — Event catalog aliases (`BookingDraftCreated`, `SupportTicketCreated`, `FleetbaseOrderCreated`)
6. **P2** — Driver portal missing pages (performance, vehicle, documents, support)
7. **P2** — Delivery lifecycle notification handlers (`order.delivered`, `driver_assigned`)
8. **P3** — Documents module event emissions
9. **P3** — Operations/dashboard WebSocket (poll-only today)
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
