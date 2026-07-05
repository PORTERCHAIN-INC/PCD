# Porterchain Event Catalog


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Source of truth:** `shared/python/porterchain_shared/events/catalog.py` (+ mirror `packages/events/src/catalog.ts`)

Event names use `{aggregate}.{action}` dot notation. PascalCase aliases (e.g. `QuoteCreated`) map to the same string via `EVENT_ALIASES`.

---

## Visitor

| Event                     | Alias          | Aggregate | Description                          |
| ------------------------- | -------------- | --------- | ------------------------------------ |
| `visitor.created`         | VisitorCreated | visitor   | Anonymous visitor record created     |
| `visitor.session_started` | —              | visitor   | Session cookie issued                |
| `visitor.session_merged`  | —              | visitor   | Anonymous session linked to customer |

---

## Quote & booking

| Event                | Alias            | Aggregate | Description                                     |
| -------------------- | ---------------- | --------- | ----------------------------------------------- |
| `quote.created`      | QuoteCreated     | quote     | Price quote generated                           |
| `quote.accepted`     | QuoteAccepted    | quote     | Customer accepted quote / proceeded to checkout |
| `quote.expired`      | —                | quote     | Quote TTL elapsed                               |
| `booking.started`    | —                | booking   | Customer clicked continue booking               |
| `booking.confirmed`  | BookingConfirmed | booking   | Payment captured; booking + order created       |
| `checkout.started`   | —                | checkout  | Stripe session created                          |
| `checkout.abandoned` | —                | checkout  | Session expired or payment failed               |
| `booking_draft.draft_created` | BookingDraftCreated | booking_draft | Server-persisted retail draft created |

---

## Customer

| Event                    | Alias              | Aggregate | Description          |
| ------------------------ | ------------------ | --------- | -------------------- |
| `customer.registered`    | CustomerRegistered | customer  | New customer account |
| `customer.authenticated` | —                  | customer  | Clerk session linked |

---

## Merchant

| Event                   | Alias            | Aggregate | Description                        |
| ----------------------- | ---------------- | --------- | ---------------------------------- |
| `merchant.lead_created` | —                | merchant  | Lead form submitted                |
| `merchant.approved`     | MerchantApproved | merchant  | Sales/compliance approved merchant |
| `merchant.activated`    | —                | merchant  | Merchant portal access enabled     |
| `merchant.billed`       | MerchantBilled   | merchant  | Net-terms invoice issued           |

---

## Payment

| Event               | Alias            | Aggregate | Description             |
| ------------------- | ---------------- | --------- | ----------------------- |
| `payment.succeeded` | PaymentSucceeded | payment   | Stripe payment captured |
| `payment.failed`    | —                | payment   | Payment attempt failed  |
| `payment.started`   | PaymentStarted   | payment   | Checkout session initiated |

---

## Order lifecycle

| Event                      | Alias               | Aggregate | Schema ver. | Description                         |
| -------------------------- | ------------------- | --------- | ----------- | ----------------------------------- |
| `order.created`            | OrderCreated        | order     | 1           | Order record persisted              |
| `order.booked`             | —                   | order     | 2           | Order confirmed (paid or net terms) |
| `order.dispatch_ready`     | —                   | order     | 1           | Ready for Fleetbase dispatch        |
| `order.dispatch_requested` | DispatchRequested   | order     | 1           | Manual dispatch requested           |
| `order.driver_assigned`    | DriverAssigned      | order     | 1           | Driver assigned by ops              |
| `order.driver_accepted`    | DriverAccepted      | order     | 1           | Driver accepted job                 |
| `order.driver_rejected`    | —                   | order     | 1           | Driver rejected job                 |
| `order.arrived_pickup`     | DriverArrivedPickup | order     | 1           | Driver at pickup location           |
| `order.pickup_completed`   | ParcelPickedUp      | order     | 1           | Parcel collected                    |
| `order.in_transit`         | DeliveryStarted     | order     | 1           | En route to destination             |
| `order.delivered`          | ParcelDelivered     | order     | 1           | Delivered to recipient              |
| `order.pod_completed`      | ProofCompleted      | order     | 1           | Proof of delivery validated         |
| `order.invoiced`           | InvoiceGenerated    | order     | 1           | Invoice generated                   |
| `order.closed`             | —                   | order     | 1           | Order settled and archived          |
| `order.cancelled`          | —                   | order     | 1           | Order cancelled                     |
| `order.near_delivery`      | NearDelivery        | order     | 1           | Driver approaching destination      |
| `order.tracking_updated`   | LocationUpdated     | order     | 1           | GPS / tracking ping                 |
| `route.optimized`          | RouteOptimized      | route     | 1           | Route plan updated                  |

---

## Financial

| Event                   | Alias               | Aggregate | Description                      |
| ----------------------- | ------------------- | --------- | -------------------------------- |
| `refund.requested`      | RefundRequested     | refund    | Customer/ops requested refund    |
| `refund.issued`         | —                   | refund    | Refund processed via Stripe      |
| `driver.payout_created` | DriverPayoutCreated | driver    | Driver payout batch item created |

---

## Claims

| Event            | Alias         | Aggregate | Description                  |
| ---------------- | ------------- | --------- | ---------------------------- |
| `claim.opened`   | ClaimOpened   | claim     | Damage/loss claim filed      |
| `claim.resolved` | ClaimResolved | claim     | Claim closed with resolution |

---

## Support

| Event                    | Alias               | Aggregate | Description              |
| ------------------------ | ------------------- | --------- | ------------------------ |
| `support.ticket_created` | SupportTicketCreated | support  | Customer support ticket  |

---

## Notifications & webhooks

| Event                 | Alias              | Aggregate    | Description                               |
| --------------------- | ------------------ | ------------ | ----------------------------------------- |
| `notification.queued` | NotificationQueued | notification | Outbound message queued                   |
| `notification.sent`   | NotificationSent   | notification | Message delivered to provider             |
| `webhook.received`    | WebhookReceived    | webhook      | Inbound Stripe/Fleetbase webhook accepted |

---

## Fleetbase bridge

| Event                      | Aggregate | Description                            |
| -------------------------- | --------- | -------------------------------------- |
| `fleetbase.order_created`  | order     | Porterchain order synced to Fleetbase  |
| `fleetbase.status_updated` | order     | Fleetbase status pushed to Porterchain |
| `fleetbase.pod_received`   | order     | Proof documents received               |
| `fleetbase.sync_failed`    | order     | Sync error (retry/DLQ)                 |

---

## Phase 2 stubs (no consumers yet — ADR-010)

| Event                      | Aggregate | Description                              |
| -------------------------- | --------- | ---------------------------------------- |
| `dispatch.recommendation`  | dispatch  | AI/optimizer suggestion (not implemented)|
| `eta.predicted`            | order     | Predictive ETA (not implemented)         |

---

## CRM

| Event          | Aggregate | Description             |
| -------------- | --------- | ----------------------- |
| `lead.created` | lead      | Marketing lead captured |

---

## Default consumers

| Event pattern                  | Handler                                                     | Side effect                   |
| ------------------------------ | ----------------------------------------------------------- | ----------------------------- |
| `order.dispatch_ready`         | `fleetbase_sync_handler.sync_order_from_event`              | Create/update Fleetbase order |
| `order.driver_assigned`        | `fleetbase_sync_handler.sync_driver_assignment_from_event`  | Sync driver + dispatch        |
| `order.booked`                 | `notification_handler.notify_order_booked`                  | Queue order booked email      |
| `booking.confirmed`            | `notification_handler.notify_booking_confirmed`             | Send booking confirmation     |
| `payment.succeeded`            | billing queue enqueue                                       | Settlement workflow           |
| `webhook.received` (fleetbase) | `fleetbase_sync_handler.apply_fleetbase_webhook_from_event` | Apply status update           |
| `webhook.received`             | webhook queue enqueue                                       | Merchant fan-out              |
| `notification.queued`          | email/SMS/push queue                                        | Deliver notification          |
| `order.*`                      | webhook queue                                               | Merchant webhook fan-out      |

---

## Payload conventions

- Include only IDs and display fields needed by consumers — not full ORM graphs.
- Use `correlation_id` to chain quote → order → payment → invoice.
- `actor.type`: `customer`, `merchant`, `admin`, `fleetbase`, `system`, `webhook`.

Example `booking.confirmed` payload:

```json
{
  "order_id": "ord_abc",
  "email": "customer@example.com",
  "phone": "+15551234567",
  "tracking_number": "PC-2026-00001",
  "order_number": "ORD-00001",
  "invoice_number": "INV-00001",
  "booking_number": "BKG-00001"
}
```

---

## TypeScript mirror

```typescript
import { DomainEvents } from "@porterchain/events";

DomainEvents.BOOKING_CONFIRMED; // "booking.confirmed"
```

---

## Related documents

| Document | Purpose |
| -------- | ------- |
| [EVENT_BUS.md](./EVENT_BUS.md) | Infrastructure and operations |
| [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md) | End-to-end flows |
| [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md) | Handler wiring diagram |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
