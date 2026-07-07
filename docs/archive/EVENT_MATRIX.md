# Porterchain — Event Matrix

**Reference:** [masterrule.md](./masterrule.md) §12  
**Last verified:** 2026-07-04 · **Status:** Historical audit snapshot  
**Catalog:** `shared/python/porterchain_shared/events/catalog.py`  
**Bus bridge:** `apps/api/src/porterchain_api/platform/bus.py`  
**Handlers:** `services/event-bus/porterchain_event_bus/handlers/__init__.py`

> Canonical event reference is [EVENT_CATALOG.md](./EVENT_CATALOG.md); handler wiring is [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md). This matrix is a point-in-time emitted/handler audit and may lag the catalog.

---

## Requested events (audit checklist)

| PascalCase            | Canonical string              | Emitted?     | Handler?        | Emitter                                     | Consumer                   |
| --------------------- | ----------------------------- | ------------ | --------------- | ------------------------------------------- | -------------------------- |
| QuoteCreated          | `quote.created`               | ✅           | ❌ (audit only) | `quote_service.py`                          | —                          |
| BookingDraftCreated   | `booking_draft.draft_created` | ✅           | ❌              | `booking_draft_service.py`                  | —                          |
| BookingConfirmed      | `booking.confirmed`           | ✅           | ✅              | `confirmation_service.py`                   | `notify_booking_confirmed` |
| PaymentSucceeded      | `payment.succeeded`           | ✅           | ✅              | `payment_service.py`                        | Billing queue → worker     |
| OrderCreated          | `order.created`               | ✅           | ⚠️              | `confirmation_service.py`                   | `order.*` webhook fanout   |
| FleetbaseOrderCreated | `fleetbase.order_created`     | ✅           | ⚠️              | `integration_bridge.py`                     | `order.*` fanout           |
| DispatchRequested     | `order.dispatch_requested`    | ❌ → **fix** | ❌              | —                                           | —                          |
| DriverAssigned        | `order.driver_assigned`       | ✅           | ✅              | `operations_service.py`, webhooks           | Fleetbase driver sync      |
| PickupStarted         | `order.arrived_pickup`        | ✅           | ⚠️              | `driver-platform/stops.py`                  | `order.*` fanout           |
| ParcelPickedUp        | `order.pickup_completed`      | ✅           | ⚠️              | `stops.py`, webhooks                        | `order.*` fanout           |
| ParcelDelivered       | `order.delivered`             | ✅           | ⚠️              | `stops.py`, webhooks                        | `order.*` fanout           |
| PODCompleted          | `order.pod_completed`         | ✅           | ⚠️              | `pod.py`, `webhook_processor.py`            | `order.*` fanout           |
| InvoiceGenerated      | `order.invoiced`              | ⚠️           | ❌              | Code emits `invoice.created`                | —                          |
| ClaimOpened           | `claim.opened`                | ✅           | ❌ → **fix**    | `claims_service.py`, webhooks               | —                          |
| SupportTicketCreated  | `support.ticket_created`      | ✅           | ❌ → **fix**    | `support_service.py`, `customer_service.py` | —                          |
| NotificationSent      | `notification.sent`           | ✅           | ❌              | `orchestrator.py`                           | —                          |

---

## Registered bus handlers

| Subscription             | Handler                              | Downstream                                |
| ------------------------ | ------------------------------------ | ----------------------------------------- |
| `order.dispatch_ready`   | `sync_order_from_event`              | `BookingSyncService.push_order` → adapter |
| `order.driver_assigned`  | `sync_driver_assignment_from_event`  | `push_driver_assignment` → adapter        |
| `order.booked`           | `notify_order_booked`                | `notification.queued` → email             |
| `booking.confirmed`      | `notify_booking_confirmed`           | `NotificationService` direct              |
| `payment.succeeded`      | `_handle_payment_succeeded`          | `QueueName.BILLING`                       |
| `webhook.received`       | `apply_fleetbase_webhook_from_event` | `WebhookProcessor` + webhooks queue       |
| `notification.queued`    | `_handle_notification_queued`        | email/SMS/push queues                     |
| `order.*`                | `_handle_merchant_webhook_fanout`    | webhooks queue (stub)                     |
| `claim.opened`           | **added**                            | `notify_claim_opened`                     |
| `support.ticket_created` | **added**                            | `notify_support_ticket_created`           |

---

## Full event catalog by domain

### Visitor

| Event                     | Emitted         | Handler |
| ------------------------- | --------------- | ------- |
| `visitor.created`         | ❌ catalog only | —       |
| `visitor.session_started` | ✅              | —       |
| `visitor.session_merged`  | ✅              | —       |

### Quote & booking

| Event                      | Emitted                    | Handler       |
| -------------------------- | -------------------------- | ------------- |
| `quote.created`            | ✅                         | —             |
| `quote.accepted`           | ✅                         | —             |
| `quote.expired`            | ⚠️ DB only in `pricing.py` | —             |
| `booking.started`          | ✅                         | —             |
| `booking.confirmed`        | ✅                         | notifications |
| `booking.created`          | ✅                         | —             |
| `checkout.started`         | ✅                         | —             |
| `checkout.abandoned`       | ✅                         | —             |
| `booking.draft_restored`   | ✅                         | —             |
| `booking.consent_recorded` | ✅                         | —             |

### Booking draft (dynamic `booking_draft.*`)

| Event                                  | Emitted | Handler |
| -------------------------------------- | ------- | ------- |
| `booking_draft.draft_created`          | ✅      | —       |
| `booking_draft.draft_updated`          | ✅      | —       |
| `booking_draft.quote_generated`        | ✅      | —       |
| `booking_draft.customer_identified`    | ✅      | —       |
| `booking_draft.customer_authenticated` | ✅      | —       |
| `booking_draft.payment_started`        | ✅      | —       |
| `booking_draft.payment_completed`      | ✅      | —       |
| `booking_draft.booking_confirmed`      | ✅      | —       |
| `booking_draft.draft_cancelled`        | ✅      | —       |
| `booking_draft.draft_expired`          | ✅      | —       |

### Customer & merchant

| Event                           | Emitted | Handler |
| ------------------------------- | ------- | ------- |
| `customer.registered`           | ✅      | —       |
| `customer.authenticated`        | ✅      | —       |
| `lead.created`                  | ✅      | —       |
| `merchant.approved`             | ✅      | —       |
| `merchant.suspended`            | ✅      | —       |
| `merchant.booking_created`      | ✅      | —       |
| `merchant.bulk_booking_created` | ✅      | —       |
| `merchant.api_key_generated`    | ✅      | —       |
| `merchant.lead_created`         | ❌      | —       |
| `merchant.activated`            | ❌      | —       |
| `merchant.billed`               | ❌      | —       |

### Payment & financial

| Event                   | Emitted              | Handler       |
| ----------------------- | -------------------- | ------------- |
| `payment.started`       | ✅                   | —             |
| `payment.succeeded`     | ✅                   | billing queue |
| `payment.failed`        | ✅                   | —             |
| `invoice.created`       | ✅                   | —             |
| `receipt.generated`     | ✅                   | —             |
| `order.invoiced`        | ⚠️ **fix** dual emit | —             |
| `refund.requested`      | ❌                   | —             |
| `refund.issued`         | ❌                   | —             |
| `refund.approved`       | ❌                   | —             |
| `driver.payout_created` | ❌                   | —             |

### Order lifecycle

| Event                      | Emitted         | Handler            |
| -------------------------- | --------------- | ------------------ |
| `order.created`            | ✅              | fanout             |
| `order.booked`             | ✅              | notifications      |
| `order.dispatch_requested` | ❌ → **fix**    | —                  |
| `order.dispatch_ready`     | ✅              | Fleetbase sync     |
| `order.driver_assigned`    | ✅              | Fleetbase + fanout |
| `order.driver_accepted`    | ✅              | —                  |
| `order.driver_rejected`    | ✅              | —                  |
| `order.arrived_pickup`     | ✅              | fanout             |
| `order.pickup_completed`   | ✅              | fanout             |
| `order.in_transit`         | ⚠️ webhook only | fanout             |
| `order.delivered`          | ✅              | fanout             |
| `order.pod_completed`      | ✅              | fanout             |
| `order.cancelled`          | ✅              | fanout             |
| `order.closed`             | ❌              | —                  |
| `order.tracking_updated`   | ✅              | —                  |
| `order.admin_override`     | ✅              | —                  |
| `dispatch.assigned`        | ✅              | —                  |
| `dispatch.queued`          | ❌ defined only | —                  |

### Claims & support

| Event                     | Emitted | Handler                  |
| ------------------------- | ------- | ------------------------ |
| `claim.opened`            | ✅      | **notification handler** |
| `claim.resolved`          | ✅      | —                        |
| `support.ticket_created`  | ✅      | **notification handler** |
| `support.ticket_resolved` | ✅      | —                        |

### Notifications & webhooks

| Event                 | Emitted | Handler             |
| --------------------- | ------- | ------------------- |
| `notification.queued` | ✅      | worker queues       |
| `notification.sent`   | ✅      | —                   |
| `webhook.received`    | ✅      | Fleetbase processor |

### Fleetbase bridge

| Event                           | Emitted      | Handler |
| ------------------------------- | ------------ | ------- |
| `fleetbase.order_created`       | ✅           | fanout  |
| `fleetbase.status_updated`      | ❌ → **fix** | —       |
| `fleetbase.pod_received`        | ❌ → **fix** | —       |
| `fleetbase.sync_failed`         | ❌           | —       |
| `fleetbase.cancellation_synced` | ✅           | —       |

### Admin

| Event              | Emitted | Handler |
| ------------------ | ------- | ------- |
| `driver.approved`  | ✅      | —       |
| `driver.suspended` | ✅      | —       |
| `pricing.updated`  | ✅      | —       |

---

## Event flow diagrams

### Retail booking → dispatch

```
quote.created
  → booking.started → checkout.started
  → payment.succeeded → [billing queue]
  → booking.confirmed → [email confirmation]
  → order.created → order.booked → [email booked]
  → order.dispatch_requested  [NEW]
  → order.dispatch_ready → [Fleetbase push_order]
  → fleetbase.order_created
```

### Fleetbase inbound

```
POST /webhooks/fleetbase
  → webhook.received
  → WebhookProcessor
  → order.{state} via transition_order_state
  → fleetbase.status_updated [NEW]
  → order.pod_completed → fleetbase.pod_received [NEW]
```

---

## Gaps closed in this audit (implementation)

1. Emit `order.dispatch_requested` before `order.dispatch_ready`
2. Notification handlers for `claim.opened`, `support.ticket_created`
3. Emit `fleetbase.status_updated`, `fleetbase.pod_received` on webhook processing
4. Dual emit `order.invoiced` with `invoice.created`
5. Catalog aliases: `BookingDraftCreated`, `SupportTicketCreated`, `FleetbaseOrderCreated`, `PickupStarted`

---

## Intentionally unimplemented (roadmap)

- `refund.*`, `driver.payout_created`, `merchant.billed`
- `order.closed` terminal event
- `fleetbase.sync_failed` on retry exhaustion
- Full merchant webhook fanout delivery (worker stub)
