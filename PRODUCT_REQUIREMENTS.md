# Porterchain — Product Requirements


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Implemented with known gaps — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)  
**Audience:** Product, Engineering, Operations, Sales, Executive

---

## Vision

Porterchain is a **professional commercial logistics platform** for Canada — combining instant retail booking (Uber Direct–style) with enterprise merchant programs (Porter.in–style B2B), powered by **Fleetbase** as the non–customer-facing dispatch engine.

Porterchain owns customer experience, pricing, billing, CRM, and contracts. Fleetbase owns fleet operations, routing, GPS, and execution mechanics.

---

## Strategic positioning

| Dimension      | Porterchain                                            |
| -------------- | ------------------------------------------------------ |
| **Market**     | GTA + Ontario expansion → Canada                       |
| **Retail**     | Instant quote → pay → track (no login for estimate)    |
| **B2B**        | Sales-led onboarding, Net terms, API, recurring routes |
| **Operations** | Dispatcher-controlled, compliance-first, insured       |
| **Technology** | Porterchain platform + Fleetbase dispatch backbone     |

Porterchain is **not** an open driver marketplace. Drivers are vetted partners; dispatch is controlled.

---

## User segments

### 1. Individual customers (retail)

**Who:** Any website visitor needing a one-time or occasional delivery.

**Goals:** Fast quote, easy payment, shipment tracking, invoice, rebook.

| Capability         | Requirement                                                                               | Priority |
| ------------------ | ----------------------------------------------------------------------------------------- | -------- |
| Instant quote      | Pickup, dropoff, vehicle, package, weight, dimensions, schedule → price **without login** | P0       |
| Continue booking   | Email + phone collection                                                                  | P0       |
| Authentication     | **Clerk** — merge anonymous quote session into account                                    | P0       |
| Payment            | **Stripe** checkout before booking confirmation                                           | P0       |
| Customer dashboard | Track, invoice download, history, rebook, profile (`apps/customer/` :3004) | P0 — ✅ Live |
| Abandoned checkout | Persist quote, email, phone; remarketing                                                  | P1       |
| Guest estimate TTL | Quote expires (`QUOTE_EXPIRED`)                                                           | P0       |

**Out of scope for retail:** Net terms, CSV bulk, API keys, multi-user org (unless they convert to business).

---

### 2. Business customers (merchants)

**Who:** Companies with recurring or volume delivery needs.

**Goals:** Reliable SLA delivery, invoicing, integrations, team access.

| Capability            | Requirement                                         | Priority |
| --------------------- | --------------------------------------------------- | -------- |
| Sales intake          | Contact / quote request → CRM lead                  | P0       |
| Sales approval        | Admin approves business before account creation     | P0       |
| Merchant account      | Created after approval                              | P0       |
| Commercial agreement  | E-sign / accept in onboarding wizard                | P0       |
| Merchant portal       | Full B2B feature set                                | P0       |
| Book deliveries       | Portal UI + saved addresses                         | P0       |
| CSV bulk upload       | Batch shipment creation                             | P1       |
| API integration       | REST + webhooks (`/v1/merchant-api` with API keys) | P1 — ✅ Live |
| Recurring routes      | Scheduled recurring lanes                           | P2       |
| Multi-user            | Org roles in merchant portal                        | P1       |
| Billing               | Net 15 / Net 30 / Net 45; optional per-order Stripe | P0       |
| Invoices & statements | PDF, payment status, overdue reminders              | P0       |
| Reports & analytics   | Volume, spend, on-time %                            | P1       |

**Payment default:** Invoice on terms — **not** per-order Stripe unless merchant or order is configured for card/immediate pay.

---

### 3. Driver partners

**Who:** Vetted independent or fleet drivers in the Porterchain network.

**Goals:** Predictable jobs, clear instructions, fair payouts, easy POD.

| Capability        | Requirement                                   | Priority |
| ----------------- | --------------------------------------------- | -------- |
| Registration      | Application with documents                    | P0       |
| Admin approval    | Vehicle + insurance verification              | P0       |
| Job acceptance    | Accept/reject assigned jobs                   | P0       |
| Navigation        | Route map, turn-by-turn (Google Maps)         | P0       |
| Execution         | Pickup → transit → delivery                   | P0       |
| Proof of delivery | Photo, signature, barcode, OTP where required | P0       |
| Wallet & payouts  | Earnings, payout history                      | P1       |
| Documents         | Compliance doc upload & expiry                | P0       |
| Ratings           | Performance feedback                          | P2       |
| Support           | In-app / ops escalation                       | P1       |

---

## Public booking flow (retail) — requirements

Aligned with current website booking widget fields; **no UI redesign** — backend and post-quote flow are specified here.

### Phase A — Anonymous quote (no auth)

| Step | Input                  | System behavior                              |
| ---- | ---------------------- | -------------------------------------------- |
| 1    | Pickup address         | Google Places validation; GTA bounds         |
| 2    | Dropoff address        | Distance / zone check                        |
| 3    | Vehicle class          | Capacity match                               |
| 4    | Package type & details | Weight, dimensions                           |
| 5    | Schedule               | Same-day or scheduled slot                   |
| 6    | **Calculate quote**    | Pricing engine returns estimate + `quote_id` |
| 7    | Display estimate       | User may leave without account               |

**Acceptance criteria:**

- Quote API responds in &lt; 3s p95 under normal load
- Quote stored with TTL (configurable, default 30 minutes)
- State: `QUOTE` → `QUOTE_EXPIRED` on TTL

### Phase B — Continue booking (auth + pay)

| Step | Action                                                 |
| ---- | ------------------------------------------------------ |
| 1    | User clicks **Continue Booking**                       |
| 2    | Collect email + phone                                  |
| 3    | **Clerk** sign-up / sign-in (or link to existing)      |
| 4    | Merge `anonymous_session_id` → `customer_id`           |
| 5    | Create lead record (CRM)                               |
| 6    | State: `BOOKING_PENDING` → `PAYMENT_PENDING`           |
| 7    | **Stripe** Checkout Session                            |
| 8    | On success: `BOOKED` → create Order → Fleetbase bridge |
| 9    | Confirmation email/SMS                                 |
| 10   | Redirect to **customer dashboard**                     |

### Phase C — Abandoned checkout

| Trigger                                       | System behavior                                  |
| --------------------------------------------- | ------------------------------------------------ |
| User leaves after email/phone, before payment | Persist abandoned checkout                       |
| Stripe session expires                        | `PAYMENT_PENDING` timeout → remarketing eligible |
| Remarketing                                   | Email campaign with quote link (respect consent) |

---

## Operations requirements

Every successful retail or merchant booking becomes an **Order** in Porterchain; execution syncs to **Fleetbase**.

| Stage           | Owner             | Requirement                                                     |
| --------------- | ----------------- | --------------------------------------------------------------- |
| NEW             | System            | Order created post-payment or merchant submit                   |
| Dispatch review | Dispatcher        | Optional manual review for high-value / flagged                 |
| Assignment      | Dispatcher / auto | Driver + vehicle assigned via Fleetbase bridge                  |
| Execution       | Driver            | Full lifecycle through POD                                      |
| Invoice         | Billing           | Retail: receipt at booking; adjustments post-delivery if needed |
| Close           | System            | `CLOSED` after POD + billing settled                            |

See [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md) and [BUSINESS_WORKFLOW.md](./BUSINESS_WORKFLOW.md).

---

## Exception management requirements

All exceptions must be **logged, stateful, and auditable**. See [EXCEPTION_WORKFLOWS.md](./EXCEPTION_WORKFLOWS.md).

| Category  | Examples                                        |
| --------- | ----------------------------------------------- |
| Driver    | Reject, timeout, unavailable, breakdown, cancel |
| Customer  | Unavailable, wrong address                      |
| Parcel    | Damaged, lost                                   |
| Delivery  | Failed, return to sender                        |
| Financial | Refund, insurance claim                         |

---

## Platform boundaries

### Porterchain owns

- Website, customer dashboard, merchant portal (UX)
- Clerk authentication (retail, merchant, admin web)
- Pricing engine
- Billing, invoices, Stripe, Net terms
- CRM, leads, contracts
- Order state machine (canonical)
- Notifications (email, SMS, push orchestration)
- Reports & analytics (business layer)
- API for merchants & public quote

### Fleetbase owns (not customer-facing)

- Driver fleet records (operational)
- Vehicle registry (operational)
- Dispatch console
- Route optimization (Valhalla / OSRM)
- GPS tracking sessions
- Waypoints & stop execution
- POD capture plumbing (synced to Porterchain)

See [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md).

---

## Non-functional requirements

| Area           | Target                           |
| -------------- | -------------------------------- |
| Availability   | 99.9% API (production)           |
| Quote latency  | &lt; 3s p95                      |
| Payment        | PCI via Stripe only              |
| Data residency | Canada-first (PIPEDA)            |
| Audit          | Full order + exception event log |
| i18n           | en-CA, fr-CA (website)           |
| Scale          | 10k orders/day design horizon    |

---

## Explicit non-goals (this phase)

- **Do not** redesign booking widget UI
- **Do not** change existing website pages or marketing copy
- **Do not** expose Fleetbase console to end customers
- **Do not** implement open marketplace bidding

---

## Success metrics

| Segment    | KPI                                                   |
| ---------- | ----------------------------------------------------- |
| Retail     | Quote-to-book conversion, abandoned checkout recovery |
| Merchant   | Time to ACTIVE, invoice DSO, API adoption             |
| Operations | On-time %, exception rate, cost per delivery          |
| Drivers    | Acceptance rate, POD compliance, payout cycle time    |

---

## Related documents

| Document                                       | Content                           |
| ---------------------------------------------- | --------------------------------- |
| [BUSINESS_WORKFLOW.md](./BUSINESS_WORKFLOW.md) | End-to-end operational flows      |
| [USER_JOURNEYS.md](./USER_JOURNEYS.md)         | Persona journeys                  |
| [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)     | State machine                     |
| [MODULE_BREAKDOWN.md](./MODULE_BREAKDOWN.md)   | Admin / merchant / driver modules |
| [ROLE_PERMISSIONS.md](./ROLE_PERMISSIONS.md)   | RBAC matrix                       |

---

## Implementation status (July 2026)

| Area              | Status | Notes                                              |
| ----------------- | ------ | -------------------------------------------------- |
| Retail booking    | ✅     | Website + Stripe; webhook required in prod         |
| Customer portal   | ✅     | `apps/customer/` — tracking map gap remains        |
| Merchant portal   | ✅     | Core B2B flows live; NET batch invoicing partial   |
| Admin ops         | ✅     | 46+ pages, dispatch, CRM, finance                  |
| Driver mobile     | ⚠️     | 72% — field ops work; EAS/Firebase prod ops needed |
| Customer mobile   | ⚠️     | 62% — core flows; store assets pending             |
| Production cert   | ❌     | See `PRODUCTION_READINESS_REPORT.md`               |

---

## Auth note

**Target (this PRD):** Retail customers use **Clerk + Stripe pre-payment** at booking.

Legacy platform notes referenced Supabase OTP for booking verification. That path is **superseded** for retail by Clerk account merge + Stripe checkout. Merchant and driver auth remain Clerk / Porterchain JWT respectively.

---

_Design specification with implementation status. Platform is **not yet production certified**._
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
