# Porterchain — Event Flow Diagram

**Last verified:** 2026-07-04 · **Status:** Historical audit snapshot  
**Catalog:** `shared/python/porterchain_shared/events/catalog.py`

> Canonical event docs: [EVENT_CATALOG.md](./EVENT_CATALOG.md), [EVENT_FLOW.md](./EVENT_FLOW.md), [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md). This file captures a point-in-time emission audit.

---

## Driver lifecycle events (audit checklist)

| Event            | String                     | Emitted? | Source                                          |
| ---------------- | -------------------------- | -------- | ----------------------------------------------- |
| Driver Assigned  | `order.driver_assigned`    | ✅       | Admin ops, Fleetbase webhook                    |
| Driver Accepted  | `order.driver_accepted`    | ✅       | driver-platform availability                    |
| Driver Rejected  | `order.driver_rejected`    | ✅       | driver-platform                                 |
| Pickup Started   | `order.arrived_pickup`     | ✅       | driver stops, webhooks                          |
| Picked Up        | `order.pickup_completed`   | ✅       | driver stops, webhooks                          |
| Transit          | `order.in_transit`         | ⚠️       | Webhooks primarily                              |
| Near Delivery    | `order.near_delivery`      | ✅       | **Fixed** — driver arrive at dropoff            |
| Delivered        | `order.delivered`          | ✅       | driver stops, webhooks                          |
| Proof Completed  | `order.pod_completed`      | ✅       | POD service, webhooks                           |
| Location Updated | `order.tracking_updated`   | ✅       | Fleetbase tracking webhooks                     |
| Fleetbase Sync   | `fleetbase.status_updated` | ✅       | WebhookProcessor                                |
| Route Optimized  | `route.optimized`          | ❌       | Catalog only — Fleetbase orchestrator not wired |

---

## Booking → dispatch event chain

```mermaid
sequenceDiagram
  participant UI as Website/Merchant
  participant API as FastAPI
  participant PE as Pricing Engine
  participant EB as Event Bus
  participant FB as Fleetbase Adapter
  participant FBC as Fleetbase

  UI->>API: Create quote/booking
  API->>PE: resolve_route_distance + calculate
  API->>API: order.dispatch_requested
  API->>API: order.dispatch_ready
  API->>EB: publish
  EB->>FB: sync_order_from_event
  FB->>FBC: POST /v1/orders
  API->>API: fleetbase.order_created
```

---

## Inbound Fleetbase webhook chain

```mermaid
sequenceDiagram
  participant FBC as Fleetbase
  participant WH as /webhooks/fleetbase
  participant WP as WebhookProcessor
  participant EB as Event Bus
  participant LM as Live Map WS

  FBC->>WH: status/tracking/POD
  WH->>EB: webhook.received
  EB->>WP: apply_fleetbase_webhook
  WP->>WP: transition_order_state
  WP->>EB: fleetbase.status_updated
  WP->>EB: order.tracking_updated
  Note over LM: Next WS tick reads DB mirror
```

---

## Payment → billing

```
payment.succeeded → billing queue → SettlementService
booking.confirmed → notification handler
invoice.created + order.invoiced → audit
```

---

## Registered bus handlers

| Event                    | Handler                        |
| ------------------------ | ------------------------------ |
| `order.dispatch_ready`   | Fleetbase order sync           |
| `order.driver_assigned`  | Fleetbase dispatch assign      |
| `order.booked`           | Email notification             |
| `booking.confirmed`      | Confirmation email             |
| `payment.succeeded`      | Billing queue                  |
| `webhook.received`       | Fleetbase processor            |
| `notification.queued`    | Email / SMS (log-only) / push queues |
| `claim.opened`           | Claim notification             |
| `support.ticket_created` | Support notification           |
| `order.*`                | Merchant webhook fanout (stub) |

---

## Webhooks (ingress only)

| Provider    | Endpoint                   | Status                                          |
| ----------- | -------------------------- | ----------------------------------------------- |
| Stripe      | `POST /webhooks/stripe`    | ✅                                              |
| Fleetbase   | `POST /webhooks/fleetbase` | ✅                                              |
| Firebase    | —                          | ❌ Push outbound only (FCM), no ingress webhook |
| Google Maps | —                          | ✅ Correctly absent                             |
