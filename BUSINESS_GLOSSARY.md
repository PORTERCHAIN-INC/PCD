# Porterchain — Business Glossary


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Canonical terminology — all modules must use these definitions  
**See also:** [DOMAIN_MODEL.md](./DOMAIN_MODEL.md), [ENTITY_RELATIONSHIP_MODEL.md](./ENTITY_RELATIONSHIP_MODEL.md)

---

## How to use this glossary

- **Preferred term** is the Porterchain canonical name (PascalCase in docs, snake_case in DB).
- **Do not use** synonyms listed under "Avoid" in code, APIs, or UI copy without explicit mapping.
- **Fleetbase** terms appear only in adapter/sync context — never as customer-facing language.

---

## A

### Abandoned Checkout

A retail funnel record created when a user provides contact information or starts Stripe checkout but does not complete payment. Linked to a **Quote** and optionally a **Customer**.

### Address

Value object representing a geographic location: formatted string, coordinates (lat/lng), and structured fields (street, city, province, postal code, country). Used on **Quote**, **Order**, and **Stop**.

### Admin User

Operations staff account authenticated via Clerk. Has an **Admin** role (dispatcher, support, sales, finance, super_admin). Distinct from **Merchant User** and **Driver**.

### API Key

Merchant-issued credential for programmatic API access. Scoped to **Merchant** with permission scopes. Never stores raw key — only hash and prefix.

### Audit Log

Immutable record of who changed what and when. Types: **Admin Audit Log**, **Merchant Audit Log**, **Domain Event** (system-wide).

### Aggregate

Cluster of domain objects treated as a single consistency boundary. Example: **Order** aggregate includes **Shipment**, **Stop**, **Parcel**, **OrderEvent**.

---

## B

### Booking

Commercial confirmation that a **Quote** will proceed to fulfillment. Created after successful payment (retail) or merchant submission. Links **Quote** → **Customer** → **Order**. Identified by `booking_number`.

**Avoid:** Using "booking" interchangeably with "order" after payment — post-payment the **Order** is the fulfillment aggregate.

### B2B / Business Customer

See **Merchant**.

### B2C / Retail Customer

See **Customer**.

---

## C

### Campaign Discount

Time-limited promotional pricing configured in **Merchant Contract** or **Promotion**. Distinct from one-time **Coupon**.

### Claim

Formal insurance or damage request linked to an **Order**. Triggers investigation workflow; may result in **Refund**. States: open, investigating, resolved, denied.

### Commercial Order

See **Order**.

### Contract

See **Merchant Contract**.

### Coupon

**Promotion** subtype (`promotion_type = coupon`) redeemed at quote time via `promo_code`. Provides percent or fixed discount.

### Customer

Authenticated retail user (individual shipper). Authenticated via Clerk. May originate from **Visitor** session merge. Owns **Quotes**, **Bookings**, **Orders**, and **Wallet** (retail credits).

**Avoid:** "User" without qualifier — specify Customer, Merchant User, Driver, or Admin User.

---

## D

### Delivery

A **Stop** with `type = DELIVERY` — the destination handoff point. Not a separate aggregate; always part of **Shipment**.

### Dispatch

The act and record of assigning a **Driver** and **Vehicle** to an **Order**. Triggers `order.driver_assigned` event. Operational execution delegated to Fleetbase via adapter.

### Dispatch Bridge

Porterchain integration flag (`FLEETBASE_DISPATCH_BRIDGE`) enabling order sync to Fleetbase. Does not imply Fleetbase owns commercial data.

### Driver

Vetted delivery partner (not open marketplace). Has compliance status, **Vehicle**(s), **Wallet** balance, and **Driver Payout** history. Synced to Fleetbase via `fleetbase_driver_id`.

### Driver Payout

Batch or individual payment to **Driver** for completed deliveries. Distinct from **Customer Payment** and **Merchant Invoice**.

---

## E

### Entity

Persisted business object with identity (UUID). Contrasts with **Value Object** (no independent id).

### Event (Domain Event)

Immutable fact that something happened (`order.booked`, `payment.succeeded`). Stored in **Domain Event** log and fan-out to workers, webhooks, notifications.

### Exception (Order Exception)

Delivery failure or ops issue tied to an **Order** (wrong address, damaged parcel, driver timeout). Part of exception taxonomy in `ExceptionType`. Distinct from **Incident**.

### Express

**Service type** — faster-than-standard delivery with surcharge. See **Service Type**.

---

## F

### Fleet

Logical grouping of **Drivers** and **Vehicles** under Porterchain operations. Maps to Fleetbase `company` via `company_uuid`. Not customer-facing.

### Fleetbase

Upstream logistics engine (dispatch, routing, GPS, POD capture). **Never** calculates Porterchain prices. Accessed only via `services/fleetbase-adapter/`.

### Fleetbase Order ID

Operational foreign key on **Order** (`fleetbase_order_id`). Internal reference — not the customer tracking number.

### Fuel Surcharge

Percentage added to base charges based on **Fuel Config**. Applied by **Pricing Engine** — not Fleetbase.

---

## I

### Incident

Safety, compliance, or fraud event that may or may not link to an **Order**. Higher severity than **Order Exception**. Examples: accident, policy violation.

### Invoice

Billing document for **Order** charges. Retail: receipt at booking. B2B: Net terms statement. May link to Stripe invoice id and PDF in object storage.

---

## L

### Lane

Directed pricing path between two **Zones** (e.g. `gta_core → gta_outer`). Defined in **Merchant Contract** rules or **Pricing Rule** config.

### Lead

CRM prospect from website contact, business inquiry, or abandoned **Quote**. May convert to **Merchant** or **Customer**.

---

## M

### Merchant

B2B business account (company). Has **Merchant Users**, **Merchant Contract**, **Api Keys**, **Webhooks**, and **Orders**. Payment terms: Net 15/30/45 or immediate.

### Merchant Contract

Signed commercial agreement governing **Merchant** pricing: zone rates, lane rates, flat rates, volume discounts, minimum commitment. Active contract required for ACTIVE merchant status.

### Merchant User

Person belonging to a **Merchant** org (owner, admin, ops, finance, readonly). Authenticated via Clerk organization.

### Minimum Charge

Floor price per vehicle class or contract. Enforced by **Pricing Engine** as `minimum` line item.

### Multi-Stop

Delivery with more than pickup + dropoff — additional **Stops** between or after primary route. Surcharge per extra stop.

---

## N

### Notification

Outbound message (email, SMS, push) triggered by **Domain Event**. Ephemeral delivery record — not the marketing campaign itself.

---

## O

### Order

**Canonical aggregate root** for fulfillment. Has `tracking_number` (public), `order_number` (internal), state machine, locked `amount_cents`, and Fleetbase sync reference. Parent of **Shipment**.

**Golden rule:** Customer tracks an **Order**, not a Fleetbase order.

### Order Event

Append-only state transition log on **Order** (`from_state`, `to_state`, actor, timestamp). Subset of customer-visible **Tracking Event**.

### Order Exception

See **Exception (Order Exception)**.

---

## P

### Package

Classification of goods being shipped (looseParcel, medical, furniture, ltlPallet, etc.). Value object on **Quote** and **Parcel** — not a physical container entity.

### Parcel

Physical shipment unit within a **Shipment**: weight, dimensions, declared value, package type. MVP: one parcel per order.

### Payment

Money collection attempt via Stripe linked to **Quote** and/or **Order**. States: PENDING, PROCESSING, SUCCEEDED, FAILED.

### Permission

Atomic authorization capability (`order:read`, `dispatch:manage`). Granted to **Role**.

### Pickup

A **Stop** with `type = PICKUP` — origin collection point.

### POD / Proof of Delivery

Evidence of successful delivery: photo, signature, barcode scan, or OTP. **ProofOfDelivery** entity linked to **Order**. Required before `POD_COMPLETED` state.

### Pricing Engine

Porterchain-owned service (`services/pricing-engine/`) calculating all quotes and order amounts. Independent of Fleetbase.

### Pricing Rule

Configurable tariff (retail, zone, lane, vehicle, flat, merchant). Persisted as `pricing_tariffs`. Evaluated by **Pricing Engine**.

### Promotion

Discount instrument: coupon, referral credit, wallet credit, campaign, merchant discount. Identified by `code`.

---

## Q

### Quote

Non-binding price estimate with TTL. Created anonymously or by **Customer**. Contains locked `amount_cents` and **Price Breakdown**. States: QUOTE, QUOTE_EXPIRED, BOOKING_PENDING, PAYMENT_PENDING.

**Avoid:** Calling a paid order a "quote" — after payment it is an **Order**.

---

## R

### Refund

Reversal of **Payment** via Stripe. Linked to **Order** and optionally **Claim**.

### Referral Credit

**Promotion** subtype applied as **Wallet** credit for customer acquisition.

### Role

Named collection of **Permissions** (visitor, customer, merchant, driver, dispatcher, admin, super_admin).

### Route

Optimized driving path for one or more **Orders**. Geometry from Fleetbase; Porterchain stores snapshot for **Driver** app. Encoded polyline.

### Rush Delivery

Immediate pickup expectation (`schedule_mode = now` or `is_rush`). Surcharge in **Pricing Engine**.

---

## S

### Scheduled Delivery

Future-dated delivery (`schedule_mode = later`). May have lower or different pricing than rush.

### Service Area

Geographic boundary where Porterchain offers service. **Quote** validation rejects addresses outside active service area.

### Service Type

Delivery product classification: same_day, express, scheduled, recurring, multi_stop, ltl, ftl, furniture, medical, construction, wholesale.

### Shipment

Physical movement unit under an **Order**. Contains **Stops** and **Parcels**. MVP: 1:1 with Order.

### Stop

Waypoint on a **Shipment** route: PICKUP, DELIVERY, or WAYPOINT. Ordered by `sequence`.

### Support Ticket

Customer service case. May reference **Customer**, **Merchant**, **Driver**, or **Order**. Distinct from **Claim** (financial/insurance).

---

## T

### Tax Rule

Configuration for HST/sales tax (`pricing_tax` system config). Applied by **Tax Service** in pricing engine.

### Tracking Event

Customer-visible timeline entry: status change, GPS ping, ETA update. Sourced from driver app, Fleetbase webhook, or system.

### Tracking Number

Public identifier on **Order** for shipment tracking (e.g. `PC-…`). Unique. Used on website `/track/{tracking_number}`.

---

## V

### Value Object

Immutable object without identity: **Address**, **PackageDimensions**, **PriceBreakdown**, **Money**, **TimeWindow**.

### Vehicle

Registered automobile/van/truck operated by **Driver**. Classes: sedan, suv, pickup, cargoVan, highRoof, box16, box20. Synced via `fleetbase_vehicle_id`.

### Visitor

Anonymous website user identified by session cookie before Clerk authentication. Tracked as **Visitor Session** for analytics and quote attribution.

### Volume Discount

Tiered discount in **Merchant Contract** based on shipment count in period.

---

## W

### Wallet

Ledger of credits for **Customer** (promo/referral) or **Driver** (earnings). Balance in cents; transactions append-only.

### Webhook (Inbound)

Fleetbase → Porterchain HTTP callback (`POST /webhooks/fleetbase`). Validated by HMAC. Updates **Order** state.

### Webhook (Outbound)

Merchant-configured HTTP callback on **Domain Events** (shipment.created, shipment.delivered, etc.). HMAC-signed by Porterchain.

---

## Z

### Zone

Geographic pricing region (e.g. `gta_core`, `gta_outer`) with bounds and multiplier. Part of **Service Area**. Used by **Zone Service** in pricing engine.

---

## Term relationships (quick reference)

```
Visitor ──► Quote ──► Booking ──► Order ──► Shipment ──► Stop (Pickup/Delivery)
                                    │           └── Parcel (Package type)
                                    ├── Payment / Invoice / Refund
                                    ├── Dispatch ──► Driver ──► Vehicle
                                    ├── TrackingEvent / ProofOfDelivery
                                    └── Claim / OrderException

Merchant ──► MerchantContract ──► Zone / Lane / PricingRule
          └── MerchantUser ──► Order (B2B)

Pricing Engine ◄── Quote.amount_cents, Order.amount_cents
Fleetbase Adapter ◄── Order.fleetbase_order_id (execution only)
```

---

## Forbidden conflations

| Wrong                            | Correct                                                                  |
| -------------------------------- | ------------------------------------------------------------------------ |
| Fleetbase order = customer order | **Order** is Porterchain; Fleetbase is sync target                       |
| Package = Parcel                 | **Package** = type; **Parcel** = physical unit                           |
| Booking = Order (always)         | **Booking** converts to **Order** once; then use Order                   |
| Quote = Order                    | **Quote** is pre-payment estimate only                                   |
| Delivery = Order                 | **Delivery** is a stop type on **Shipment**                              |
| Dispatch = Route                 | **Dispatch** = assignment; **Route** = path geometry                     |
| Coupon ≠ Promotion               | **Coupon** is a **Promotion** subtype                                    |
| Exception = Incident             | **Order Exception** = delivery failure; **Incident** = safety/compliance |
| Fleetbase pricing                | Does not exist — use **Pricing Engine**                                  |
| User (generic)                   | Specify Customer / Merchant User / Driver / Admin User                   |

---

## Module terminology alignment

| Module                        | Must use these terms                                           |
| ----------------------------- | -------------------------------------------------------------- |
| `website/`                    | Visitor, Quote, Customer, Tracking Number                      |
| `apps/merchant-portal/`       | Merchant, Merchant User, Order, Shipment, Invoice              |
| `apps/admin/`                 | Order, Driver, Dispatch, Claim, Support Ticket, Pricing Rule   |
| `apps/api/booking_engine/`    | Quote, Booking, Order, Payment                                 |
| `apps/api/merchant_engine/`   | Merchant, Order, Shipment                                      |
| `services/pricing-engine/`    | Quote inputs, Price Breakdown, Zone, Lane, Tax Rule, Promotion |
| `services/fleetbase-adapter/` | fleetbase_order_id, fleetbase_driver_id (sync refs only)       |
| `packages/events/`            | Domain event names from catalog                                |
| `packages/types/`             | Role, Permission enums                                         |

---

## Related documents

- [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)
- [ENTITY_RELATIONSHIP_MODEL.md](./ENTITY_RELATIONSHIP_MODEL.md)
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md)
- [PRICING_ENGINE.md](./PRICING_ENGINE.md)
- [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)

---

_Canonical business vocabulary for Porterchain. Update this glossary when adding new domain entities._
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
