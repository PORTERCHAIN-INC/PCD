# Booking Flow (Retail)

> **Source:** `booking_engine/quote_service.py`, `booking_draft_service.py`, `booking_service.py`, `payment_service.py`, `confirmation_service.py`, `stripe_webhook_service.py`

## Lifecycle (Actual Implementation)

| Step         | Component                                                        | State / Event                                      |
| ------------ | ---------------------------------------------------------------- | -------------------------------------------------- |
| 1. Quote     | `QuoteService.create_quote()`                                    | `quote.created`                                    |
| 2. Draft     | `BookingDraftService.create_or_update()`                         | `DRAFT` → `QUOTE_GENERATED`                        |
| 3. Auth      | Clerk JWT on `POST /v1/bookings`                                 | `AUTHENTICATED`                                    |
| 4. Checkout  | `PaymentService.start_payment()`                                 | `PAYMENT_PENDING`, `payment.started`               |
| 5. Stripe    | Redirect to `checkout_url`                                       | External Stripe hosted page                        |
| 6. Webhook   | `StripeWebhookService`                                           | `checkout.session.completed` only trusted signal   |
| 7. Confirm   | `BookingConfirmationService.complete_payment_and_create_order()` | `Order` BOOKED, `booking.confirmed`                |
| 8. Dispatch  | `transition_to_dispatch_ready()`                                 | `order.dispatch_requested`, `order.dispatch_ready` |
| 9. Fleetbase | Event handler → `BookingSyncService.push_order()`                | `fleetbase.order_created`                          |
| 10. Delivery | Fleetbase webhooks → `WebhookProcessor`                          | State machine transitions                          |
| 11. Invoice  | On `POD_COMPLETED` path                                          | `order.invoiced`, `invoice.created`                |

## Dev Bypass

When `settings.allow_stripe_mock` is true: `POST /v1/bookings/mock-complete` skips Stripe.

## Diagram

```mermaid
flowchart TD
  V[Visitor] --> Q[POST /v1/quotes<br/>QuoteService]
  Q --> BD[POST /v1/booking-drafts<br/>BookingDraftService DRAFT]
  BD --> QG[QUOTE_GENERATED]
  V --> AUTH[Clerk Sign-In<br/>website middleware]
  AUTH --> CID[CUSTOMER_IDENTIFIED / AUTHENTICATED]
  CID --> BK[POST /v1/bookings<br/>BookingService.start_booking]
  BK --> PS[PaymentService.start_payment]
  PS --> PP[PAYMENT_PENDING draft]
  PS --> SC[Stripe Checkout URL<br/>or mock if allow_stripe_mock]
  SC --> SW[Stripe Webhook<br/>POST /webhooks/stripe]
  SW --> MS[PaymentService.mark_succeeded]
  MS --> CF[BookingConfirmationService<br/>complete_payment_and_create_order]
  CF --> ORD[Order BOOKED + Invoice]
  CF --> EV1[Events: booking.confirmed, order.booked]
  CF --> DR[transition_to_dispatch_ready<br/>DISPATCH_READY]
  DR --> EV2[order.dispatch_ready]
  EV2 --> FB[BookingSyncService.push_order<br/>via event bus handler]
  FB --> DISP[Fleetbase Dispatch]
  DISP --> DEL[Webhook status updates<br/>WebhookProcessor]
  DEL --> POD[POD_COMPLETED]
  POD --> INV[INVOICED / order.invoiced]
  INV --> CLS[CLOSED]
```

## PlantUML

See [plantuml/booking_flow.puml](./plantuml/booking_flow.puml)
