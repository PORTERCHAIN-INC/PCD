# Porterchain — Business Workflow

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Operational specification — reflects current implementation

---

## Overview

This document describes how Porterchain operates as a **logistics technology company** — from first website visit through delivery, billing, and exception resolution. Fleetbase executes dispatch; Porterchain owns commercial and customer layers.

---

## Workflow map

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   RETAIL    │     │   MERCHANT  │     │   DRIVER    │
│  (Website)  │     │  (Portal)   │     │   (App)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌────────────────────────┐
              │   PORTERCHAIN API    │
              │  Orders · Pricing ·  │
              │  Billing · CRM · Auth│
              └───────────┬────────────┘
                          │ bridge
                          ▼
              ┌────────────────────────┐
              │      FLEETBASE         │
              │ Dispatch · Routes · GPS│
              └───────────┬────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ DISPATCHER  │   │   SUPPORT   │   │   BILLING   │
│  (Admin)    │   │   (Admin)   │   │   (Admin)   │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## 1. Retail customer workflow

### 1.1 Discovery → quote (anonymous)

1. Visitor lands on website (`/`).
2. Enters pickup, dropoff, vehicle, package, weight, dimensions, schedule in booking widget.
3. System calls **pricing engine** (distance, vehicle, weight, time window, surcharges).
4. Returns **instant estimate** + `quote_id` (state: `QUOTE`).
5. Visitor may browse site without logging in.

### 1.2 Quote → booking → payment

1. Visitor clicks **Continue Booking**.
2. System collects **email** and **phone**.
3. **Clerk** authentication (sign-up or sign-in).
4. Porterchain merges **anonymous session** → **customer account**.
5. CRM creates/updates **lead** and **visitor** record.
6. Order state: `BOOKING_PENDING` → `PAYMENT_PENDING`.
7. **Stripe Checkout** for quoted amount (+ tax per jurisdiction).
8. On `checkout.session.completed`:
   - State → `BOOKED`
   - Create **Order**
   - Emit `order.booked` event
   - Bridge → Fleetbase create payload/order
   - Send confirmation (email + optional SMS)
9. Redirect to **customer portal** (`apps/customer/` :3004) or website track page.

### 1.3 Abandoned checkout

| Checkpoint abandoned            | Stored data         | Action                                      |
| ------------------------------- | ------------------- | ------------------------------------------- |
| After quote, before continue    | `quote_id`, session | Retargeting pixel / email if captured later |
| After email/phone, before Clerk | quote + contact     | Abandoned checkout record                   |
| After Clerk, before Stripe      | customer_id + quote | Remarketing email with resume link          |
| Stripe started, not completed   | payment_intent id   | Stripe recovery + internal follow-up        |

### 1.4 Post-booking customer workflow

1. Customer tracks shipment on dashboard (`apps/customer/` or website `/track/{tracking_number}`).
2. On delivery: POD visible (photo, signature, timestamp, GPS).
3. **Invoice/receipt** downloadable (Stripe receipt + Porterchain invoice PDF).
4. **Rebook** pre-fills addresses from history.
5. Profile management via Clerk.

---

## 2. Business customer workflow

### 2.1 Lead → approval

1. Business submits contact / for-business inquiry (website or sales).
2. CRM creates **lead** (source, company, contact).
3. **Sales** qualifies lead → opportunity.
4. Sales approves → triggers **merchant account provisioning** (Clerk org + portal invite).
5. Merchant receives onboarding link.

### 2.2 Merchant onboarding

1. Company profile (legal name, tax/HST, billing email, addresses).
2. Document upload (registration, insurance, tax).
3. **Commercial agreement** acceptance (`contract_status = signed`).
4. Admin **compliance review**.
5. On approval: merchant status → `ACTIVE`.
6. Payment terms assigned (Net 15 / Net 30 / Net 45 / card / Stripe per-order if configured).

### 2.3 Merchant operations

1. Merchant users log in via **Clerk** (merchant portal).
2. Book delivery (single), **CSV upload** (batch), or **API** (integration).
3. Orders created in Porterchain → bridge to Fleetbase (no per-order Stripe unless configured).
4. Track all shipments; saved addresses & recipients.
5. **Recurring routes** (scheduled) generate orders on cadence.
6. Monthly **statements** and **invoices** per payment terms.
7. Reports: volume, spend, SLA performance.

### 2.4 Merchant billing workflow

| Term                | Flow                                                             |
| ------------------- | ---------------------------------------------------------------- |
| Net 30/45           | Order → delivered → line on monthly invoice → due date → payment |
| Credit card on file | Optional auto-charge on invoice                                  |
| Per-order Stripe    | Checkout link per shipment (merchant setting)                    |
| Immediate           | Stripe at order creation                                         |

---

## 3. Driver partner workflow

### 3.1 Onboarding

1. Driver applies (web or invite link).
2. Submits identity, license, vehicle, insurance documents.
3. **Admin** reviews → approve / reject.
4. On approve: Clerk + driver credentials; Fleetbase driver record created via bridge.
5. Driver installs app; completes invite/password setup.

### 3.2 Daily operations

1. Dispatcher assigns order/route in **Fleetbase console** (or auto-assign rules).
2. Driver notified (FCM push when configured; in-app list always).
3. Driver **accepts** or **rejects** job.
4. En route → **at pickup** → **picked up** → **in transit** → **at destination** → **delivered**.
5. **POD**: photo, signature, barcode scan, OTP if required.
6. Location pings during active route.
7. Earnings accrue to **wallet**; periodic **payout**.

### 3.3 Compliance maintenance

- Document expiry alerts (insurance, license).
- Suspension if documents lapse or rating threshold breached.

---

## 4. Internal operations workflow

### 4.1 Dispatch

1. New orders appear in dispatch queue (`DISPATCH_READY`).
2. Dispatcher reviews (flagged orders, capacity, SLA).
3. Assigns driver + vehicle in Fleetbase.
4. State sync: `DRIVER_ASSIGNED` → notify driver.
5. Monitor live map; intervene on delays.

### 4.2 Support

1. Customer/merchant/driver opens ticket (portal, email, phone).
2. Support views order timeline + exceptions.
3. Actions: reschedule, reassign, refund initiate, escalate to claims.
4. All actions append to **audit log**.

### 4.3 Billing & finance

1. Retail: payment at booking (Stripe); adjustments via credit note if exception.
2. Merchant: invoice generation cycle; overdue reminders; Stripe pay link on invoice.
3. Driver: payout batch (weekly/biweekly); deductions for chargebacks if policy.

### 4.4 Claims & insurance

1. Exception triggers `CLAIM_OPEN` (damaged, lost).
2. Ops collects evidence (POD, photos, statements).
3. Insurance workflow external; status tracked in Porterchain.
4. Resolution → `REFUNDED` or closed claim.

---

## 5. Fleetbase bridge workflow

| Porterchain event       | Fleetbase action                              |
| ----------------------- | --------------------------------------------- |
| `order.booked`          | Create order/payload                          |
| `order.dispatch_ready`  | Available in dispatch queue                   |
| `order.driver_assigned` | Assign driver to order/route                  |
| Fleetbase status update | Webhook/poll → update Porterchain order state |
| `pod.completed`         | Sync POD artifacts to Porterchain storage     |
| `order.cancelled`       | Cancel Fleetbase order                        |

**Rule:** Porterchain order ID is canonical; Fleetbase ID stored as `fleetbase_order_id`.

---

## 6. Notification workflow

| Event             | Retail customer | Merchant              | Driver | Ops   |
| ----------------- | --------------- | --------------------- | ------ | ----- |
| Booking confirmed | Email, SMS      | —                     | —      | —     |
| Driver assigned   | Email, SMS      | Email (if configured) | Push   | —     |
| Out for delivery  | SMS             | —                     | —      | —     |
| Delivered         | Email           | Email                 | —      | —     |
| Exception         | Email, SMS      | Email                 | Push   | Email |
| Invoice due       | —               | Email                 | —      | —     |
| Payout sent       | —               | —                     | Email  | —     |

---

## 7. Pricing workflow

1. **Quote request** → pricing engine inputs: distance (Valhalla/OSRM), vehicle class, weight, dimensions, time window, zone, fuel surcharge.
2. **Quote** stored with breakdown (line items for audit).
3. **Booking** locks quote price (or re-validates if expired).
4. **Merchant** may use contract rates (volume discounts) instead of retail tariff.
5. **Adjustments** post-delivery (wait time, wrong address fee) → billing adjustment record.

---

## Related documents

- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [EVENT_BUS.md](./EVENT_BUS.md)
- [EXCEPTION_WORKFLOWS.md](./EXCEPTION_WORKFLOWS.md)
- [USER_JOURNEYS.md](./USER_JOURNEYS.md)

---

_Operational specification reflecting current monorepo. Platform not yet production certified — see `PRODUCTION_READINESS_REPORT.md`._
---

## Governance

| Document                                                                | Role              |
| ----------------------------------------------------------------------- | ----------------- |
| [masterrule.md](masterrule.md)                                          | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](docs/archive/reports-2026-08/CTO_AUDIT_REPORT.md) | Doc vs code audit |
