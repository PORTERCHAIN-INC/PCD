# Notification Template Catalog

> Templates live in `notification_engine/templates.py`. Admin UI reads this catalog; DB overrides are future scope.

## Categories

| Category | Templates |
|----------|-----------|
| **Booking** | `booking_draft_created`, `booking_confirmed`, `checkout_recovery` |
| **Orders** | `order_created`, `order_booked`, `driver_assigned`, `driver_accepted`, `driver_rejected` |
| **Tracking** | `pickup_started`, `parcel_picked_up`, `in_transit`, `near_delivery`, `delivered`, `tracking_update`, `pod_uploaded` |
| **Finance** | `payment_started`, `payment_receipt`, `payment_failed`, `invoice_ready`, `merchant_invoice_ready`, `refund_processed` |
| **Claims** | `claim_opened`, `claim_updated` |
| **Support** | `support_ticket_created`, `support_reply` |
| **CRM** | `quote_created`, `merchant_welcome` |
| **Security** | `system_alert`, `password_reset`, `otp` |
| **Marketing** | `marketing_campaign` (future) |

## Template Schema

Each template defines:

| Field | Description |
|-------|-------------|
| `subject` | Email subject / push title |
| `body` | Plain text body |
| `html` | Optional HTML email |
| `push_title` | Override push title |
| `push_body` | Override push body |
| `category` | Preference category |
| `variables` | Required context keys |

## Variable Reference

| Variable | Used in |
|----------|---------|
| `{tracking_number}` | Booking, tracking |
| `{order_number}` | Orders |
| `{booking_number}` | Booking |
| `{invoice_number}` | Finance |
| `{amount_display}` | Payments |
| `{driver_name}` | Driver assigned |
| `{claim_number}` | Claims |
| `{ticket_number}` | Support |
| `{recovery_url}` | Checkout recovery |
| `{deep_link}` | In-app navigation |

## Localization

Templates support `{locale}` suffix keys (e.g. `booking_confirmed_fr`). Default locale: `en-CA`.

Fallback order: `{template}_{locale}` → `{template}` → generic `delivery_update`.

## Admin Management

Route: `/admin/notifications` → Templates tab

- View catalog (read-only in v1)
- Preview rendered output with sample context
- DB-backed overrides: future (`notification_template_overrides` table)
