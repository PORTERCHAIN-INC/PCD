# Booking Workflow Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` §10 (Retail lifecycle), §14 (Stripe rules), ADR-004, ADR-006

---

## Executive Verdict

| Area                        | Pre-Audit           | Post-Fix     |
| --------------------------- | ------------------- | ------------ |
| Booking Draft persistence   | Complete            | Complete     |
| State machine               | Partial             | **Complete** |
| Stripe webhook finalization | **Critical defect** | **Fixed**    |
| Idempotency                 | Partial             | **Improved** |
| Draft recovery              | Partial             | Partial      |
| Expiration job              | Missing             | Missing      |

Retail booking workflow is **functionally complete** for the happy path. A **Critical** race (EXPIRED draft during Stripe checkout) was identified and fixed during this audit.

---

## Lifecycle Compliance (§10.1)

```
Visitor → Quote → Booking Draft → Clerk auth → Stripe Checkout
→ Webhook verification → PAYMENT_COMPLETED → BOOKING_CONFIRMED → Order
→ DISPATCH_READY → Planning Queue → Fleetbase (event bus)
```

| Step                   | Implementation                                     | Status   |
| ---------------------- | -------------------------------------------------- | -------- |
| Quote                  | `QuoteService`                                     | Complete |
| Booking Draft          | `BookingDraftService` + `booking_draft_models.py`  | Complete |
| Clerk session merge    | `merge_session_to_customer`                        | Complete |
| Stripe Checkout        | `PaymentService.start_payment`                     | Complete |
| Webhook only finalizes | `StripeWebhookService`                             | Complete |
| Order creation         | `BookingConfirmationService`                       | Complete |
| Planning queue         | `transition_to_dispatch_ready` → Route Center      | Complete |
| Fleetbase sync         | `fleetbase_sync_handler` on `order.dispatch_ready` | Complete |

---

## Critical Finding — EXPIRED Draft During Payment (FIXED)

### Issue ID: BW-C01

| Field              | Value                                                                                                                                          |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Severity**       | Critical                                                                                                                                       |
| **Root Cause**     | `expire_if_needed()` ran during webhook finalization; `EXPIRED → PAYMENT_COMPLETED` was disallowed; order committed before draft update failed |
| **Affected Layer** | Application Services (`booking_engine`)                                                                                                        |
| **Symptom**        | Stripe payment succeeded; order created; draft stuck `EXPIRED`; success page polling forever                                                   |
| **Effort**         | 4 hours (implemented)                                                                                                                          |

### Fixes Applied

1. **`EXPIRED → PAYMENT_COMPLETED`** allowed when verified webhook arrives (`domain/states.py`)
2. **`_raw_by_quote_id()`** — payment handlers skip expiry check (`booking_draft_service.py`)
3. **Active checkout protection** — `PAYMENT_PENDING` + `stripe_checkout_session_id` never auto-expires
4. **TTL extension** on `on_payment_started` — resets `expires_at` when checkout begins
5. **`GET /quotes/{id}`** — catches `draft_expired` instead of 500 (`quotes.py`)
6. **Unique `orders.quote_id`** — DB-level idempotency (migration `n2o3p4q5r6s7`)

---

## Remaining Findings

### BW-H01 — No background expiration/reconciliation job (High)

| Field               | Value                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| **Severity**        | High                                                                                                  |
| **Root Cause**      | Expiry is lazy-on-read only; no worker sweeps stale drafts or repairs draft/order mismatches          |
| **Affected Layer**  | Worker / Application Services                                                                         |
| **Recommended Fix** | Add `apps/worker` job: expire non-checkout drafts; reconcile orders where draft ≠ `BOOKING_CONFIRMED` |
| **Effort**          | 1–2 days                                                                                              |

### BW-M01 — Website `draft_id` query param unused (Medium)

| Field               | Value                                                                |
| ------------------- | -------------------------------------------------------------------- |
| **Severity**        | Medium                                                               |
| **Root Cause**      | Continue URL includes `draft_id` but client only loads by `quote_id` |
| **Affected Layer**  | UI (Website)                                                         |
| **Recommended Fix** | Call `GET /v1/booking-drafts/{draft_id}` when param present          |
| **Effort**          | 2 hours                                                              |

### BW-M02 — Local Stripe webhook not forwarded (Medium)

| Field               | Value                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Severity**        | Medium                                                                                                       |
| **Root Cause**      | Dev uses real Stripe Checkout without `stripe listen --forward-to localhost:8001/webhooks/stripe`            |
| **Affected Layer**  | DevOps / Integration                                                                                         |
| **Recommended Fix** | Document in `ENVIRONMENT_VARIABLES.md`; add diagnostics warning when webhook secret set but no recent events |
| **Effort**          | 2 hours                                                                                                      |

### BW-L01 — `restore_draft` resumes EXPIRED+session to PAYMENT_FAILED (Low)

| Field               | Value                                                           |
| ------------------- | --------------------------------------------------------------- |
| **Severity**        | Low                                                             |
| **Root Cause**      | Restore logic assumes abandoned checkout, not succeeded payment |
| **Affected Layer**  | Application Services                                            |
| **Recommended Fix** | Check payment status before restore target state                |
| **Effort**          | 2 hours                                                         |

---

## Component Scorecard

| Component                    | Status   | Notes                               |
| ---------------------------- | -------- | ----------------------------------- |
| `BookingDraftService`        | Complete | Audited transitions, access control |
| `PaymentService`             | Complete | Revalidation at checkout            |
| `BookingConfirmationService` | Complete | Order/booking/invoice/events        |
| `StripeWebhookService`       | Complete | Signature + event dedupe            |
| `BookingDraftAdminService`   | Complete | Extend/restore/expire               |
| Planning queue integration   | Complete | `DISPATCH_READY` → Route Center     |
| Draft recovery (Clerk)       | Complete | `GET /booking-drafts/active`        |
| Draft recovery (anonymous)   | Partial  | Session-bound                       |
| Expiration worker            | Missing  |                                     |

---

## Idempotency Matrix

| Mechanism                                 | Status                            |
| ----------------------------------------- | --------------------------------- |
| Stripe event dedupe (`stripe:{event_id}`) | ✅                                |
| Order lookup by `quote_id`                | ✅                                |
| Unique `orders.quote_id` (DB)             | ✅ (fixed)                        |
| Payment rows per quote                    | ⚠️ Multiple on retry (acceptable) |

---

## Test Evidence

Recent production-like test: `iot.ravichauhan@gmail.com` paid **$74.68 CAD** (Stripe test). Order **PC-20260703-43BBAC** created after reconciliation. Root cause confirmed: missing local webhook + EXPIRED draft race.

---

_See `INTEGRATION_AUDIT.md` for Stripe setup; `EVENT_BUS_AUDIT.md` for `payment.succeeded` / `booking.confirmed` events._
