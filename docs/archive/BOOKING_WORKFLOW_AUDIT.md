# Booking Workflow Audit — Porterchain Platform

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §10, §14 · ADR-004, ADR-006  
**Flows:** [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md) · [docs/architecture/BOOKING_FLOW.md](./docs/architecture/BOOKING_FLOW.md)

---

## Executive verdict

| Area | Status |
| ---- | ------ |
| Booking draft persistence | **Complete** |
| State machine | **Complete** |
| Stripe webhook finalization | **Complete** (BW-C01 fixed) |
| Idempotency | **Complete** — DB + Stripe dedupe |
| Draft recovery | **Complete** (Clerk + session) |
| Expiration / reconciliation | **Complete** — worker job (300s interval) |

Retail booking is **functionally complete** for the happy path. Platform production readiness still gated on Fleetbase runtime and prod Stripe webhooks — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md).

---

## Lifecycle compliance (§10.1)

```
Visitor → Quote → Booking Draft → Clerk auth → Stripe Checkout
→ Webhook verification → PAYMENT_COMPLETED → BOOKING_CONFIRMED → Order
→ DISPATCH_READY → Planning Queue → Fleetbase (event bus)
```

| Step | Implementation | Status |
| ---- | -------------- | ------ |
| Quote | `QuoteService` | ✅ |
| Booking draft | `BookingDraftService` + models | ✅ |
| Clerk session merge | `merge_session_to_customer` | ✅ |
| Stripe Checkout | `PaymentService.start_payment` | ✅ |
| Webhook only finalizes | `StripeWebhookService` — `POST /webhooks/stripe` | ✅ |
| Order creation | `BookingConfirmationService` | ✅ |
| Planning queue | `transition_to_dispatch_ready` → Route Center | ✅ |
| Fleetbase sync | `fleetbase_sync_handler` on `order.dispatch_ready` | ✅ |

---

## Critical fix — EXPIRED draft during payment (BW-C01) ✅

| Fix | Location |
| --- | -------- |
| `EXPIRED → PAYMENT_COMPLETED` on verified webhook | `domain/states.py` |
| `_raw_by_quote_id()` skips expiry during payment | `booking_draft_service.py` |
| Active checkout protection (`PAYMENT_PENDING` + session id) | `booking_draft_service.py` |
| TTL extension on `on_payment_started` | `booking_draft_service.py` |
| `GET /quotes/{id}` handles `draft_expired` | `quotes.py` |
| Unique `orders.quote_id` | Alembic `n2o3p4q5r6s7` |

---

## Worker reconciliation (BW-H01) ✅ implemented

`apps/worker/run.py` → `BookingDraftReconciliationService` every **300s**:

- `expire_stale_drafts()` — skips active Stripe checkout sessions
- `reconcile_paid_orders()` — repairs draft/order mismatches after verified payment

Module: `booking_engine/draft_reconciliation_service.py`

---

## Remaining findings

### BW-M01 — Website `draft_id` query param unused (Medium)

Continue URL may include `draft_id`; client loads by `quote_id` only. Optional: `GET /v1/booking-drafts/{draft_id}` when param present.

### BW-M02 — Local Stripe webhook forwarding (Medium)

Dev requires `stripe listen --forward-to localhost:8001/webhooks/stripe` for checkout finalization without mock-complete.

### BW-L01 — `restore_draft` edge cases (Low)

Verify payment status before resuming EXPIRED drafts to `PAYMENT_FAILED`.

---

## Component scorecard

| Component | Status |
| --------- | ------ |
| `BookingDraftService` | ✅ |
| `PaymentService` | ✅ |
| `BookingConfirmationService` | ✅ |
| `StripeWebhookService` | ✅ |
| `BookingDraftAdminService` | ✅ |
| `BookingDraftReconciliationService` | ✅ Worker |
| Planning queue integration | ✅ |
| Draft recovery (Clerk) | ✅ `GET /booking-drafts/active` |

---

## Idempotency matrix

| Mechanism | Status |
| --------- | ------ |
| Stripe event dedupe | ✅ |
| Order lookup by `quote_id` | ✅ |
| Unique `orders.quote_id` (partial index) | ✅ |
| Multiple payment rows on retry | ⚠️ Acceptable |

---

## Related

| Document | Purpose |
| -------- | ------- |
| [INTEGRATION_AUDIT.md](./INTEGRATION_AUDIT.md) | Stripe setup |
| [EVENT_BUS.md](./EVENT_BUS.md) | `payment.succeeded` / `booking.confirmed` |
