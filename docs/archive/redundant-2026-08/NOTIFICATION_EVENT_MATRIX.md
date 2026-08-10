# Notification Event Matrix

**Type:** REPORT
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [EVENT_CATALOG.md](../../EVENT_CATALOG.md) (canonical doc).

**Source of truth:** `notification_engine/event_router.py` → `_specs_for_event()`  
**See also:** [EVENT_CATALOG.md](../../EVENT_CATALOG.md) · [NOTIFICATION_FLOW.md](../architecture/NOTIFICATION_FLOW.md)

Domain events → notification routing. Recipients are resolved in the EventRouter — **no module hardcodes recipients**.

---

## Legend

| Channel | Code                         |
| ------- | ---------------------------- |
| Push    | `push`                       |
| Email   | `email`                      |
| In-App  | `in_app`                     |
| SMS     | `sms` (log-only when routed) |

| Recipient   | Code       |
| ----------- | ---------- |
| Customer    | `customer` |
| Merchant    | `merchant` |
| Driver      | `driver`   |
| Admin / Ops | `admin`    |
| Finance     | `finance`  |
| Support     | `support`  |

---

## Matrix (implemented handlers)

| Domain Event                           | Template                                   | Customer | Merchant | Driver | Admin | Finance | Support | Channels              |
| -------------------------------------- | ------------------------------------------ | -------- | -------- | ------ | ----- | ------- | ------- | --------------------- |
| `booking_draft.draft_created`          | `booking_draft_created`                    | ●        | —        | —      | —     | —       | —       | email†, in_app        |
| `booking.confirmed`                    | `booking_confirmed`                        | ●        | ●        | —      | ●     | —       | —       | email†, push, in_app  |
| `checkout.started` / `payment.started` | `payment_started`                          | ●        | —        | —      | —     | —       | —       | in_app                |
| `payment.succeeded`                    | `payment_receipt`                          | ●        | ●        | —      | ●     | ●       | —       | email†, in_app        |
| `payment.failed`                       | `payment_failed`                           | ●        | —        | —      | —     | —       | —       | email†, in_app        |
| `order.created`                        | `order_created`                            | ●        | ●        | —      | ●     | —       | —       | email†, in_app        |
| `order.booked`                         | `order_booked`                             | ●        | ●        | —      | ●     | —       | —       | email†, in_app        |
| `order.driver_assigned`                | `driver_assigned`                          | ●        | ●        | ●      | ●     | —       | —       | push, in_app          |
| `order.driver_accepted`                | `driver_accepted`                          | —        | —        | ●      | ●     | —       | —       | in_app                |
| `order.driver_rejected`                | `driver_rejected`                          | —        | —        | —      | ●     | —       | —       | in_app                |
| `order.arrived_pickup`                 | `pickup_started`                           | ●        | —        | —      | ●     | —       | —       | push, in_app          |
| `order.pickup_completed`               | `parcel_picked_up`                         | ●        | —        | —      | ●     | —       | —       | push, in_app          |
| `order.in_transit`                     | `in_transit`                               | ●        | —        | —      | —     | —       | —       | push                  |
| `order.near_delivery`                  | `near_delivery`                            | ●        | —        | —      | —     | —       | —       | push                  |
| `order.delivered`                      | `delivered`                                | ●        | —        | ●      | ●     | —       | —       | push, in_app          |
| `order.pod_completed`                  | `pod_uploaded`                             | —        | —        | ●      | ●     | —       | —       | in_app                |
| `order.invoiced`                       | `invoice_ready` / `merchant_invoice_ready` | ●‡       | ●        | —      | —     | ●       | —       | email‡, in_app        |
| `merchant.billed`                      | `merchant_invoice_ready`                   | —        | ●        | —      | —     | ●       | —       | in_app                |
| `refund.issued`                        | `refund_processed`                         | ●        | —        | —      | —     | —       | —       | email†, in_app        |
| `claim.opened`                         | `claim_opened`                             | ●        | —        | ●§     | —     | —       | ●       | email†, push§, in_app |
| `claim.resolved`                       | `claim_updated`                            | ●        | —        | ●      | —     | —       | ●       | push, in_app          |
| `support.ticket_created`               | `support_ticket_created`                   | ●        | —        | ●¶     | —     | —       | ●       | email†, push¶, in_app |
| `fleetbase.status_updated`             | `tracking_update`                          | ●        | —        | —      | —     | —       | —       | push, in_app          |
| `driver.emergency`                     | `driver_alert`                             | —        | —        | —      | ●     | —       | —       | in_app (critical)     |
| `driver.route_changed`                 | `driver_route_changed`                     | —        | —        | ●      | —     | —       | —       | push, in_app          |
| `incident.reported`                    | `driver_alert`                             | —        | —        | ●      | ●     | —       | —       | in_app                |
| `driver.shift_*` / `driver.break_*`    | `driver_alert`                             | —        | —        | ●      | —     | —       | —       | in_app                |

† Email only when `email` / `contact_email` present in event payload  
‡ Customer gets `invoice_ready` email; merchant gets `merchant_invoice_ready` in_app  
§ Driver push/in_app when reporter is driver  
¶ Driver when `driver_id` on ticket payload

---

## Not wired to EventRouter

| Event                  | Notes                                                      |
| ---------------------- | ---------------------------------------------------------- |
| `quote.created`        | Emitted by pricing; **no notification handler** registered |
| `support.ticket_reply` | Template exists; handler not subscribed                    |
| `system.alert`         | Template exists; use admin broadcast or future wiring      |

---

## Handler Registration

`register_notification_handlers()` in `event_router.py`, called from `platform/bus.ensure_handlers_registered()`.

## Preference Gates

Before dispatch, `PreferenceService.is_enabled()` checks category × channel (`email`, `push`, `sms`, `in_app`). SMS defaults off in preferences.

## Priority

| Event class                                    | Priority                  |
| ---------------------------------------------- | ------------------------- |
| `driver.emergency`                             | `critical`                |
| `payment.failed`                               | `critical` (PRIORITY_MAP) |
| `order.driver_assigned`, `order.near_delivery` | `high`                    |
| Default                                        | `normal`                  |

---

## Governance

| Document                                                              | Role              |
| --------------------------------------------------------------------- | ----------------- |
| [masterrule.md](../../masterrule.md)                                  | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../archive/reports-2026-08/CTO_AUDIT_REPORT.md) | Doc vs code audit |
