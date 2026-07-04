# Payment Flow

> **Source:** `booking_engine/payment_service.py`, `stripe_webhook_service.py`, `services/stripe_service.py`, `billing_engine/settlement_service.py`

## Retail Payment Path

| Step     | Component                                                                             |
| -------- | ------------------------------------------------------------------------------------- |
| Start    | `PaymentService.start_payment()` — creates `Payment` PROCESSING, Stripe session       |
| Redirect | Browser → Stripe hosted checkout (`checkout_url`)                                     |
| Webhook  | `POST /webhooks/stripe` — **only trusted payment completion signal**                  |
| Verify   | `stripe.Webhook.construct_event` + idempotency `stripe:{event_id}`                    |
| Complete | `mark_succeeded()` → `BookingConfirmationService.complete_payment_and_create_order()` |
| Events   | `payment.succeeded`, `receipt.generated`, `invoice.created`                           |
| Billing  | Worker `billing` queue → `SettlementService` ledger entry                             |

## Failure Paths

- `checkout.session.expired` → `mark_failed()` + `AbandonedCheckout`
- `payment_intent.payment_failed` → `mark_failed()`
- Retry: `POST /v1/payments/retry` → new checkout session

## Merchant Orders

No `Payment` row. `MerchantBookingService` creates orders directly — billing is net-terms (not Stripe).

## Mock (Dev)

`allow_stripe_mock` → `POST /v1/bookings/mock-complete` bypasses Stripe.

## Diagram

```mermaid
sequenceDiagram
  participant UI as Website
  participant API as PaymentService
  participant Stripe as Stripe Checkout
  participant WH as POST /webhooks/stripe
  participant SWS as StripeWebhookService
  participant PS as PaymentService
  participant CF as BookingConfirmationService
  participant Bus as Event Bus
  participant W as Worker billing queue
  participant BLE as SettlementService

  UI->>API: POST /v1/bookings
  API->>Stripe: create_checkout_session
  Stripe-->>UI: checkout_url redirect
  Stripe->>WH: checkout.session.completed
  WH->>SWS: verify signature + idempotency
  SWS->>PS: mark_succeeded
  SWS->>CF: complete_payment_and_create_order
  CF->>Bus: payment.succeeded (via mark_succeeded)
  Bus->>W: enqueue billing payment_settled
  W->>BLE: process_billing_job
  CF->>CF: Invoice row + receipt.generated
```

## PlantUML

See [plantuml/payment_flow.puml](./plantuml/payment_flow.puml)
