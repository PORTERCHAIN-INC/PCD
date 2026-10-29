# 66 · Now vs Phase 0: state machines

## Order: now (08, `domain/states.py:105`)

Now has `DELIVERED --> FAILED` and no claim path after `CLOSED` (A18). Full diagram in 08.

## Order: Phase 0

```mermaid
stateDiagram-v2
  [*] --> BOOKED
  BOOKED --> DISPATCH_READY
  BOOKED --> CANCELLED
  DISPATCH_READY --> DRIVER_ASSIGNED
  DISPATCH_READY --> CANCELLED
  DRIVER_ASSIGNED --> DRIVER_ACCEPTED
  DRIVER_ASSIGNED --> DRIVER_REJECTED
  DRIVER_ASSIGNED --> CANCELLED
  DRIVER_REJECTED --> DRIVER_ASSIGNED
  DRIVER_REJECTED --> DISPATCH_READY
  DRIVER_ACCEPTED --> DRIVER_EN_ROUTE
  DRIVER_ACCEPTED --> CANCELLED
  DRIVER_EN_ROUTE --> AT_PICKUP
  AT_PICKUP --> PICKED_UP
  PICKED_UP --> IN_TRANSIT
  IN_TRANSIT --> AT_DESTINATION
  AT_DESTINATION --> DELIVERED
  DRIVER_EN_ROUTE --> FAILED
  AT_PICKUP --> FAILED
  PICKED_UP --> FAILED
  IN_TRANSIT --> FAILED
  IN_TRANSIT --> DAMAGED
  AT_DESTINATION --> FAILED
  DELIVERED --> POD_COMPLETED
  DELIVERED --> DAMAGED
  DELIVERED --> LOST
  POD_COMPLETED --> INVOICED
  INVOICED --> CLOSED
  CLOSED --> CLAIM_OPEN: within 60 d of delivery
  FAILED --> DISPATCH_READY
  FAILED --> RETURN_TO_SENDER
  FAILED --> LOST
  FAILED --> CANCELLED
  DAMAGED --> CLAIM_OPEN
  LOST --> CLAIM_OPEN
  CLAIM_OPEN --> REFUNDED
  CLAIM_OPEN --> CLOSED
  RETURN_TO_SENDER --> CLOSED
  RETURN_TO_SENDER --> CLAIM_OPEN
```

Changes: removed `DELIVERED → FAILED`; added `IN_TRANSIT → DAMAGED`; added `CLOSED → CLAIM_OPEN` (O. Reg. 643/05 60-day notice). `IN_TRANSIT → DAMAGED` is a proposal (U66-1, Ravi/ops confirm).

## Quote: now vs Phase 0

```mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> QUOTE
  DRAFT --> CANCELLED
  QUOTE --> BOOKING_PENDING
  BOOKING_PENDING --> PAYMENT_PENDING
  BOOKING_PENDING --> QUOTE_EXPIRED
  BOOKING_PENDING --> CANCELLED
  PAYMENT_PENDING --> QUOTE_EXPIRED
  PAYMENT_PENDING --> CANCELLED
  PAYMENT_PENDING --> CONVERTED: P0 adds (A08)
  BOOKING_PENDING --> CONVERTED: P0 adds, merchant Interac terms
  CONVERTED --> [*]
```

## Invoice: now (two sources, A02) vs Phase 0

```mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> ISSUED
  ISSUED --> PARTIALLY_PAID
  ISSUED --> PAID
  PARTIALLY_PAID --> PAID
  ISSUED --> OVERDUE
  OVERDUE --> PAID
  ISSUED --> VOID
  PAID --> CREDITED: credit note (one issuer)
```

Phase 0: status is stored only as the enum above and written only by the billing workflow; `invoice_status()` computation becomes a CHECK-backed derivation test, not a second reader. State names are a proposal derived from 22; confirm against `billing_engine/models.py:140` during W3 (U66-2).

## Dispatch job offer: now vs Phase 0

Now: `DispatchJobOffer.status` String(16) default `"pending"` (`dispatch_engine/models.py:20`), no transition map.

```mermaid
stateDiagram-v2
  [*] --> OFFERED
  OFFERED --> ACCEPTED
  OFFERED --> DECLINED
  OFFERED --> EXPIRED: DBOS timer replaces job_offer_sweep
  OFFERED --> WITHDRAWN
  ACCEPTED --> [*]
```

## Driver: now vs Phase 0

Now: `domain/admin_states.py:40` `DriverStatus` with no transition table.

```mermaid
stateDiagram-v2
  [*] --> APPLIED
  APPLIED --> SCREENING: police check + abstract (L30)
  SCREENING --> APPROVED
  SCREENING --> REJECTED
  APPROVED --> ACTIVE
  ACTIVE --> SUSPENDED: notice per DPWRA s.11 (A10)
  SUSPENDED --> ACTIVE
  ACTIVE --> OFFBOARDED
  SUSPENDED --> OFFBOARDED
```
