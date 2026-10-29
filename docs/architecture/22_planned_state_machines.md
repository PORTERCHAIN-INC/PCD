# 22 — PLANNED state machines (Phase 1)

Sources: 17 (planned states), 12/15/21, strict plan locked decisions L1–L24. **(P)** = not in code today. All transitions run inside DBOS workflows (L18); agents (LangGraph, L14) may only request transitions, never write status columns. Enums + transition maps live in `domain/states.py` (21 step 3).

## 22.1 Order (17: remove `DELIVERED → FAILED`; add `CLOSED → CLAIM_OPEN` ≤ 60 d)

```mermaid
stateDiagram-v2
  [*] --> BOOKED
  BOOKED --> DISPATCH_READY: goods gate + service area pass (L1, L3)
  BOOKED --> CANCELLED
  DISPATCH_READY --> DRIVER_ASSIGNED
  DISPATCH_READY --> CANCELLED
  DRIVER_ASSIGNED --> DRIVER_ACCEPTED
  DRIVER_ASSIGNED --> DRIVER_REJECTED
  DRIVER_ASSIGNED --> CANCELLED
  DRIVER_REJECTED --> DRIVER_ASSIGNED: reassign
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
  AT_DESTINATION --> FAILED
  DELIVERED --> POD_COMPLETED: photo/signature/OTP (ECA)
  DELIVERED --> DAMAGED
  DELIVERED --> LOST
  POD_COMPLETED --> INVOICED
  INVOICED --> CLOSED
  CLOSED --> CLAIM_OPEN: within 60 d of delivery (O. Reg. 643/05)
  FAILED --> DISPATCH_READY: retry
  FAILED --> RETURN_TO_SENDER
  FAILED --> LOST
  FAILED --> CANCELLED
  DAMAGED --> CLAIM_OPEN
  LOST --> CLAIM_OPEN
  CLAIM_OPEN --> REFUNDED: under $100 auto (L22), else approval case 1
  CLAIM_OPEN --> CLOSED
  RETURN_TO_SENDER --> CLOSED
  RETURN_TO_SENDER --> CLAIM_OPEN
  CANCELLED --> [*]
  CLOSED --> [*]
  REFUNDED --> [*]
```

## 22.2 Job offer (P; as-built is a free string, default `pending`, `dispatch_engine/models.py:30`)

```mermaid
stateDiagram-v2
  [*] --> PENDING: dispatch workflow offers job
  PENDING --> ACCEPTED: driver accepts
  PENDING --> DECLINED: driver declines
  PENDING --> EXPIRED: workflow timer (replaces sweep, L20)
  PENDING --> WITHDRAWN: order cancelled or reassigned
  ACCEPTED --> [*]
  DECLINED --> [*]
  EXPIRED --> [*]
  WITHDRAWN --> [*]
```

## 22.3 Invoice (single computed status, A02 fix; values seen in `billing_engine`, `merchant_engine/billing_*`)

```mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> ISSUED: HST + BN 743402620 RT0001 checked (L8, L11)
  DRAFT --> VOID
  ISSUED --> PARTIALLY_PAID: Interac match / Stripe
  ISSUED --> PAID
  PARTIALLY_PAID --> PAID
  ISSUED --> OVERDUE: DBOS billing timer
  OVERDUE --> PAID
  ISSUED --> CREDITED: credit note issued for full balance
  PARTIALLY_PAID --> CREDITED
  ISSUED --> VOID: before any payment
  PAID --> [*]
  CREDITED --> [*]
  VOID --> [*]
```

## 22.4 Credit note (one issuer, A03 fix; `pending_approval` when > $500, L15/L17 case 2)

```mermaid
stateDiagram-v2
  [*] --> REQUESTED
  REQUESTED --> ISSUED: amount <= $500, auto
  REQUESTED --> PENDING_APPROVAL: amount > $500
  PENDING_APPROVAL --> ISSUED: Ravi approves
  PENDING_APPROVAL --> REJECTED
  ISSUED --> APPLIED: against invoice balance
  ISSUED --> REFUNDED: cash refund, cap L22
  APPLIED --> [*]
  REFUNDED --> [*]
  REJECTED --> [*]
```

## 22.5 Driver (contractor, L4; DPWRA notices, A10)

```mermaid
stateDiagram-v2
  [*] --> PENDING: onboarding
  PENDING --> APPROVED: licence class, abstract, Checkr, insurance verified
  PENDING --> REJECTED
  APPROVED --> SUSPENDED: document expiry or incident, with written notice (DPWRA s.11)
  SUSPENDED --> APPROVED: documents renewed
  APPROVED --> REMOVED: access removal notice issued (DPWRA s.11)
  SUSPENDED --> REMOVED
  REJECTED --> [*]
  REMOVED --> [*]
```

## 22.6 Quote (17: price >= cost / 0.50 before QUOTE; ACCEPTED exit)

```mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> QUOTE: margin floor cost / 0.50 passes (L2)
  DRAFT --> REFUSED: goods gate or outside 150 km (L1, L3)
  DRAFT --> CANCELLED
  QUOTE --> QUOTE_EXPIRED: DBOS timer
  QUOTE --> BOOKING_PENDING
  QUOTE --> CANCELLED
  QUOTE_EXPIRED --> QUOTE: re-price
  BOOKING_PENDING --> PAYMENT_PENDING
  BOOKING_PENDING --> QUOTE_EXPIRED
  BOOKING_PENDING --> CANCELLED
  PAYMENT_PENDING --> ACCEPTED: Stripe paid (retail) or merchant terms (Interac, L10)
  PAYMENT_PENDING --> QUOTE_EXPIRED
  PAYMENT_PENDING --> CANCELLED
  ACCEPTED --> [*]
  REFUSED --> [*]
```

## 22.7 Box truck booking (L5, L23: runs only after BOL, CVOR and cargo insurance)

```mermaid
stateDiagram-v2
  [*] --> REQUESTED
  REQUESTED --> PRICED: Ravi day price (L5, due week 3)
  PRICED --> COMPLIANCE_GATE
  COMPLIANCE_GATE --> BLOCKED: CVOR missing/expired, cargo insurance missing, or BOL not generated
  COMPLIANCE_GATE --> CONFIRMED: CVOR valid + cargo insurance valid + BOL for freight > 45 kg (O. Reg. 643/05 s.4)
  BLOCKED --> COMPLIANCE_GATE: document fixed
  BLOCKED --> CANCELLED
  CONFIRMED --> LOADING
  LOADING --> IN_TRANSIT: BOL signed by shipper
  IN_TRANSIT --> DELIVERED: BOL signed by consignee + POD
  IN_TRANSIT --> EXCEPTION
  EXCEPTION --> IN_TRANSIT
  EXCEPTION --> CLAIM_OPEN
  DELIVERED --> INVOICED
  INVOICED --> [*]
  CANCELLED --> [*]
```

## 22.8 Cooler run with temperature log (L3; GUI-0069; `temp_readings`, `pc.cooler.temp.v1`)

```mermaid
stateDiagram-v2
  [*] --> SCHEDULED
  SCHEDULED --> PRECOOL_CHECK
  PRECOOL_CHECK --> LOADED: reading in range before loading
  PRECOOL_CHECK --> SCHEDULED: out of range, re-cool
  LOADED --> IN_TRANSIT: logger streaming temp_readings
  IN_TRANSIT --> EXCURSION: reading out of range
  EXCURSION --> ON_HOLD: load held within 5 min (week 5 check)
  ON_HOLD --> IN_TRANSIT: back in range, excursion recorded
  ON_HOLD --> REJECTED: consignee or merchant refuses
  IN_TRANSIT --> DELIVERED
  DELIVERED --> LOG_CLOSED: temp log attached to POD and invoice
  REJECTED --> CLAIM_OPEN
  LOG_CLOSED --> [*]
  CLAIM_OPEN --> [*]
```

## 22.9 Agent autonomy ladder (L17, L23; strict plan section 3)

```mermaid
stateDiagram-v2
  [*] --> SHADOW
  SHADOW --> SUGGEST: >= 99% agreement over 500 jobs (200 low-volume), 0 critical
  SUGGEST --> AUTO_SAMPLED: same bar
  AUTO_SAMPLED --> FULL_AUTO: same bar
  FULL_AUTO --> AUTO_SAMPLED: critical error or KPI breach, last change reverted
  AUTO_SAMPLED --> SUGGEST: critical error or KPI breach
  SUGGEST --> SHADOW: critical error or KPI breach
  SHADOW --> KILLED: kill switch
  SUGGEST --> KILLED: kill switch
  AUTO_SAMPLED --> KILLED: kill switch
  FULL_AUTO --> KILLED: kill switch
  KILLED --> SHADOW: reset by Ravi only (approval case 6)
```

## 22.10 Agent run and approval (17)

```mermaid
stateDiagram-v2
  [*] --> QUEUED
  QUEUED --> RUNNING
  RUNNING --> WAITING_APPROVAL: one of the six cases
  WAITING_APPROVAL --> RUNNING: approval.decided approved
  WAITING_APPROVAL --> FAILED: rejected or expired
  RUNNING --> DONE: output verified
  RUNNING --> FAILED: invalid output after retries
  RUNNING --> KILLED: kill switch
  DONE --> [*]
  FAILED --> [*]
  KILLED --> [*]
```
