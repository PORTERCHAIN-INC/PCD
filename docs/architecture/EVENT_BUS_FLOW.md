# Event Bus Flow

> **Source:** `shared/python/porterchain_shared/events/catalog.py`, `services/event-bus/porterchain_event_bus/handlers/__init__.py`, `booking_engine/_core.py`

## Transport

- Library: `services/event-bus/porterchain_event_bus`
- Backend: Redis (`porterchain_shared` config)
- Registration: API lifespan `platform.bus.ensure_handlers_registered()` + worker startup

## Domain Event Catalog (Implemented)

| Category      | Events                                                                                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Visitor       | `visitor.created`, `visitor.session_started`, `visitor.session_merged`                                                           |
| Quote/Booking | `quote.created`, `quote.accepted`, `booking.started`, `booking.confirmed`, `checkout.started`, `checkout.abandoned`              |
| Payment       | `payment.started`, `payment.succeeded`, `payment.failed`                                                                         |
| Orders        | `order.created`, `order.booked`, `order.dispatch_requested`, `order.dispatch_ready`, `order.driver_assigned`, … lifecycle events |
| Fleetbase     | `fleetbase.order_created`, `fleetbase.status_updated`, `fleetbase.pod_received`, `fleetbase.sync_failed`                         |
| Notifications | `notification.queued`, `notification.sent`                                                                                       |
| Webhooks      | `webhook.received`                                                                                                               |
| CRM/Support   | `claim.opened`, `support.ticket_created`, `lead.created`                                                                         |
| Merchant      | `merchant.approved`, `merchant.billed`                                                                                           |

## Registered Handlers

| Event                    | Action                                       |
| ------------------------ | -------------------------------------------- |
| `order.dispatch_ready`   | `sync_order_from_event` → Fleetbase push     |
| `order.driver_assigned`  | `sync_driver_assignment_from_event`          |
| `order.booked`           | `notify_order_booked`                        |
| `booking.confirmed`      | `notify_booking_confirmed`                   |
| `payment.succeeded`      | Enqueue `billing` queue                      |
| `webhook.received`       | Apply Fleetbase webhook + enqueue `webhooks` |
| `notification.queued`    | Route to `emails` / `sms` / `push`           |
| `claim.opened`           | `notify_claim_opened`                        |
| `support.ticket_created` | `notify_support_ticket_created`              |
| `order.*` (wildcard)     | Merchant webhook fanout                      |

## Persistence

Every `emit_event()` also writes to `domain_events` table for audit.

## Diagram

```mermaid
flowchart TB
  subgraph Producers["Event Producers (emit_event)"]
    QS[QuoteService]
    BS[BookingService]
    PS[PaymentService]
    CF[ConfirmationService]
    OT[order_transitions]
    BDS[BookingDraftService]
    CS[CustomerService]
    SWS[StripeWebhookService]
    WIS[WebhookIngressService]
    NH[notification_handler]
  end

  subgraph Bus["Redis Event Bus"]
    REG[Handler Registry<br/>register_default_handlers]
  end

  subgraph Handlers["Subscribed Handlers"]
    H1[order.dispatch_ready → sync_order_from_event]
    H2[order.driver_assigned → sync_driver_assignment]
    H3[order.booked → notify_order_booked]
    H4[booking.confirmed → notify_booking_confirmed]
    H5[payment.succeeded → billing queue]
    H6[webhook.received → Fleetbase webhook + webhooks queue]
    H7[notification.queued → emails/sms/push queues]
    H8[claim.opened → notify_claim_opened]
    H9[support.ticket_created → notify_support_ticket]
    H10[order.* → merchant webhook fanout]
  end

  subgraph Worker["apps/worker"]
    NQ[notifications processor]
    BQ[billing processor]
    WQ[webhooks processor stub]
  end

  QS & BS & PS & CF & OT & BDS & CS & SWS & WIS & NH --> Bus
  Bus --> REG
  REG --> H1 & H2 & H3 & H4 & H5 & H6 & H7 & H8 & H9 & H10
  H5 --> BQ
  H7 --> NQ
  H6 & H10 --> WQ
```

## PlantUML

See [plantuml/event_bus_flow.puml](./plantuml/event_bus_flow.puml)
