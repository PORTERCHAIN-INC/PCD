# Notification Event Matrix

> Domain events → Notification Engine routing. Recipients are resolved by the engine — **no module hardcodes recipients**.

## Legend

| Channel | Code           |
| ------- | -------------- |
| Push    | `push`         |
| Email   | `email`        |
| In-App  | `in_app`       |
| SMS     | `sms` (future) |

| Recipient   | Code       |
| ----------- | ---------- |
| Customer    | `customer` |
| Merchant    | `merchant` |
| Driver      | `driver`   |
| Admin / Ops | `admin`    |
| Finance     | `finance`  |
| Support     | `support`  |

## Matrix

| Domain Event                  | Template                 | Customer | Merchant | Driver | Admin | Finance | Support | Channels                 |
| ----------------------------- | ------------------------ | -------- | -------- | ------ | ----- | ------- | ------- | ------------------------ |
| `quote.created`               | `quote_created`          | —        | ●        | —      | ●     | —       | —       | in_app                   |
| `booking_draft.draft_created` | `booking_draft_created`  | ●        | ●        | —      | —     | —       | —       | email, in_app            |
| `booking.confirmed`           | `booking_confirmed`      | ●        | ●        | —      | ●     | —       | —       | email, sms, push, in_app |
| `checkout.started`            | `payment_started`        | ●        | —        | —      | —     | —       | —       | in_app                   |
| `payment.started`             | `payment_started`        | ●        | —        | —      | —     | —       | —       | in_app                   |
| `payment.succeeded`           | `payment_receipt`        | ●        | ●        | —      | ●     | ●       | —       | email, in_app            |
| `payment.failed`              | `payment_failed`         | ●        | —        | —      | ●     | —       | —       | email, in_app            |
| `order.created`               | `order_created`          | ●        | ●        | —      | ●     | —       | —       | in_app, push             |
| `order.booked`                | `order_booked`           | ●        | ●        | —      | ●     | —       | —       | email, in_app            |
| `order.driver_assigned`       | `driver_assigned`        | ●        | ●        | ●      | ●     | —       | —       | push, email, in_app      |
| `order.driver_accepted`       | `driver_accepted`        | ●        | ●        | —      | ●     | —       | —       | in_app, push             |
| `order.driver_rejected`       | `driver_rejected`        | —        | —        | —      | ●     | —       | —       | in_app, push             |
| `order.arrived_pickup`        | `pickup_started`         | ●        | ●        | —      | ●     | —       | —       | push, in_app             |
| `order.pickup_completed`      | `parcel_picked_up`       | ●        | ●        | —      | ●     | —       | —       | push, in_app             |
| `order.in_transit`            | `in_transit`             | ●        | ●        | —      | —     | —       | —       | push, in_app             |
| `order.near_delivery`         | `near_delivery`          | ●        | ●        | —      | —     | —       | —       | push, in_app             |
| `order.delivered`             | `delivered`              | ●        | ●        | ●      | ●     | —       | —       | push, email, in_app      |
| `order.pod_completed`         | `pod_uploaded`           | ●        | ●        | ●      | ●     | —       | —       | in_app                   |
| `order.invoiced`              | `invoice_ready`          | ●        | ●        | —      | ●     | ●       | —       | email, in_app            |
| `merchant.billed`             | `merchant_invoice_ready` | —        | ●        | —      | ●     | ●       | —       | email, in_app            |
| `refund.issued`               | `refund_processed`       | ●        | ●        | —      | ●     | ●       | —       | email, in_app            |
| `claim.opened`                | `claim_opened`           | ●        | ●        | —      | ●     | —       | ●       | email, in_app            |
| `claim.resolved`              | `claim_updated`          | ●        | ●        | —      | ●     | —       | ●       | email, in_app            |
| `support.ticket_created`      | `support_ticket_created` | ●        | ●        | —      | ●     | —       | ●       | email, in_app            |
| `support.ticket_reply`        | `support_reply`          | ●        | ●        | —      | ●     | —       | ●       | email, in_app, push      |
| `fleetbase.status_updated`    | `tracking_update`        | ●        | ●        | ●      | ●     | —       | —       | push, in_app             |
| `system.alert`                | `system_alert`           | —        | —        | —      | ●     | —       | —       | push, in_app, email      |

## Handler Registration

All rows are handled by `notification_engine/event_router.py`, subscribed via `register_notification_handlers()` called from `platform/bus.py`.

## Preference Gates

Before dispatch, `PreferenceService` checks category (booking, tracking, orders, payments, invoices, claims, support, marketing, security) × channel (email, push, sms).

## Priority

| Event class                 | Priority   |
| --------------------------- | ---------- |
| Security / payment failed   | `critical` |
| Driver assigned / emergency | `high`     |
| Tracking updates            | `normal`   |
| Marketing                   | `low`      |
