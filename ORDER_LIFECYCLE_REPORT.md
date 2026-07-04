# Porterchain — Order Lifecycle Report

**Reference:** [masterrule.md](masterrule.md) §10  
**Date:** June 30, 2026

---

## Order ownership fields

| Field           | Values                                                   | Set by                                | Status       |
| --------------- | -------------------------------------------------------- | ------------------------------------- | ------------ |
| `order_source`  | WEBSITE, MERCHANT, API, CSV, ADMIN, PHONE, PARTNER       | Service at creation                   | ✅ **Added** |
| `order_type`    | INSTANT, CONTRACT, RECURRING, EXPRESS, SCHEDULED         | `order_metadata.resolve_order_type()` | ✅ **Added** |
| `payment_terms` | IMMEDIATE, NET_7, NET_14, NET_15, NET_30, NET_45, CUSTOM | Merchant profile or IMMEDIATE retail  | ✅           |
| `merchant_id`   | UUID                                                     | Merchant bookings                     | ✅           |
| `customer_id`   | UUID                                                     | Retail bookings                       | ✅           |

### Source assignment

| Channel                 | `order_source`      | File                                                         |
| ----------------------- | ------------------- | ------------------------------------------------------------ |
| Website retail checkout | `WEBSITE`           | `confirmation_service.py`                                    |
| Merchant portal manual  | `MERCHANT`          | `merchant_engine/booking_service.py`                         |
| Merchant CSV bulk       | `CSV`               | `bulk_service.py` → `create_shipment(..., order_source=CSV)` |
| Merchant API            | `API`               | ❌ Not wired (no API-key booking endpoint)                   |
| Admin manual            | `ADMIN`             | ❌ Not implemented                                           |
| Phone / Partner         | `PHONE` / `PARTNER` | ❌ Not implemented                                           |

### Type assignment

| Condition                   | `order_type`           |
| --------------------------- | ---------------------- |
| Active merchant contract    | `CONTRACT`             |
| `schedule_mode == "later"`  | `SCHEDULED`            |
| Rush / same-day             | `EXPRESS` or `INSTANT` |
| Recurring template (future) | `RECURRING`            |

Helper: `apps/api/.../booking_engine/order_metadata.py`

---

## State machine (canonical — Porterchain)

```
BOOKED → DISPATCH_READY → DRIVER_ASSIGNED → DRIVER_ACCEPTED
  → AT_PICKUP → PICKED_UP → IN_TRANSIT → AT_DESTINATION
  → DELIVERED → POD_COMPLETED → INVOICED → CLOSED
```

Translator: `fleetbase_engine/status_translator.py` ← `porterchain_fleetbase_adapter/events/lifecycle.py`

---

## Operations queue (unified)

`AdminOperationsService.dispatch_queue()` filters `Order.state == DISPATCH_READY` only.

**Does not filter by `order_source` or `merchant_id`.** Website and merchant orders share the same ops queue after creation. ✅ Step 10 requirement met.

---

## Retail lifecycle

```
Quote → Draft → Clerk → Stripe webhook → Order (WEBSITE, INSTANT|EXPRESS|SCHEDULED)
  → dispatch_requested → dispatch_ready → Fleetbase
  → webhooks / driver stops → POD → receipt (Stripe URL) + invoice row
```

---

## Merchant lifecycle

```
Manual/CSV → Order (MERCHANT|CSV, CONTRACT|…) → NET payment_terms from merchant
  → dispatch_ready → Fleetbase → POD
  → billing_cycle (WEEKLY|BIWEEKLY|MONTHLY) on Merchant — invoice batch TBD
```

---

## Billing models

| Model            | Flow                                  | Status                                          |
| ---------------- | ------------------------------------- | ----------------------------------------------- |
| **Website**      | Stripe → Receipt → Invoice at payment | ✅                                              |
| **Merchant NET** | Contract → Order → Cycle → Statement  | ⚠️ Cycle field added; batch invoice job roadmap |

---

## Migration

`alembic/versions/d5f6a7b8c9d0_order_source_type_billing_cycle.py` — adds columns + backfills `MERCHANT` for existing merchant orders.
