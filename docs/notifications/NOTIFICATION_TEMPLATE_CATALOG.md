# Notification Template Catalog


**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Source of truth:** `notification_engine/templates.py` (`TEMPLATES` + `TEMPLATE_META`)  
**See also:** [NOTIFICATION_EVENT_MATRIX.md](./NOTIFICATION_EVENT_MATRIX.md) · [NOTIFICATION_REPORT.md](../../NOTIFICATION_REPORT.md)

Templates are rendered by `render_template(template_key, context)` → `(subject, body)`.

---

## Categories

| Category | Templates |
| -------- | --------- |
| **Booking** | `booking_draft_created`, `booking_confirmed`, `checkout_recovery`, `quote_created` |
| **Orders** | `order_created`, `order_booked`, `driver_assigned`, `driver_accepted`, `driver_rejected`, `driver_alert` |
| **Tracking** | `pickup_started`, `parcel_picked_up`, `in_transit`, `near_delivery`, `delivered`, `tracking_update`, `pod_uploaded`, `driver_route_changed`, `delivery_update` |
| **Finance** | `payment_started`, `payment_receipt`, `payment_failed`, `invoice_ready`, `merchant_invoice_ready`, `refund_processed` |
| **Claims** | `claim_opened`, `claim_updated` |
| **Support** | `support_ticket_created`, `support_reply` |
| **Marketing** | `merchant_welcome` |
| **Security** | `system_alert`, `password_reset`, `otp` |

## Template Schema

Each entry in `TEMPLATES` defines:

| Field | Description |
| ----- | ----------- |
| `subject` | Email subject / default push title |
| `body` | Plain text with `{variable}` placeholders |

`TEMPLATE_META` adds `category` for preference routing. HTML overrides and push-specific fields are optional future extensions.

## Variable Reference

| Variable | Used in |
| -------- | ------- |
| `{tracking_number}` | Booking, tracking |
| `{order_number}` | Orders |
| `{booking_number}` | Booking |
| `{quote_id}` | Quotes, checkout recovery |
| `{invoice_number}` | Finance |
| `{amount_display}` | Payments |
| `{merchant_name}` | Merchant invoice |
| `{claim_number}`, `{claim_type}` | Claims |
| `{ticket_number}`, `{subject}` | Support |
| `{recovery_url}` | Checkout recovery |
| `{message}`, `{title}`, `{body}` | Generic / alerts |
| `{route_id}`, `{stops_count}` | Driver route changed |

Unknown variables fall back to unformatted template strings (`KeyError` handler in `render_template`).

## Localization

Not implemented in code — single `en-CA` strings. Future: `{template}_{locale}` keys or DB overrides.

## Orchestrator-Only Templates

`NotificationOrchestrator` may dispatch outside the event matrix:

- `checkout_recovery` — abandoned checkout email

## Admin Management

Route: `/admin/notifications` → Templates tab via `GET /v1/admin/notifications/templates`

- View catalog (read-only)
- Preview with sample context (admin API)
- DB-backed overrides: **not implemented** (`notification_template_overrides` future)

## E2E Coverage

Regenerate template audit snapshot:

```bash
pnpm validate:e2e:reports
```

Writes [NOTIFICATION_REPORT.md](../../NOTIFICATION_REPORT.md).
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](../../masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
