# Porterchain — Domain Model

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Canonical domain specification — implemented in `apps/api/` (PostgreSQL + Alembic)  
**Audience:** Engineering, Product, Operations

---

## Purpose

This document defines the **complete Porterchain domain model**: business entities, aggregate boundaries, ownership, validation rules, lifecycles, and event mappings. Every module (website, merchant portal, admin, API, pricing engine, fleetbase adapter, worker) must reference these same entities and terms.

**Golden rules:**

1. **Porterchain owns** commercial truth: quotes, orders, pricing, billing, CRM, customer-facing status.
2. **Fleetbase owns** operational execution: dispatch console, live GPS sessions, Fleetbase-native routes — synced via adapter only.
3. **Fleetbase never calculates prices.**
4. **`order.id` + `tracking_number`** are customer-facing identifiers; `fleetbase_order_id` is an operational foreign reference.

---

## Bounded contexts

| Context         | Responsibility                          | Primary aggregates                                      |
| --------------- | --------------------------------------- | ------------------------------------------------------- |
| **Acquisition** | Anonymous traffic, quotes, leads        | Visitor, Quote, Lead                                    |
| **Identity**    | Auth mapping across Clerk / Porterchain | Customer, MerchantUser, Driver, AdminUser, IdentityLink |
| **Commercial**  | Bookings, contracts, promotions         | Booking, Merchant, MerchantContract, Promotion          |
| **Fulfillment** | Shipments, stops, execution state       | Order, Shipment, Stop, Parcel, Dispatch                 |
| **Fleet**       | Drivers, vehicles, payouts              | Driver, Vehicle, Fleet, DriverPayout, Wallet            |
| **Tracking**    | Customer-visible status & POD           | TrackingEvent, ProofOfDelivery                          |
| **Billing**     | Payments, invoices, refunds             | Payment, Invoice, Refund                                |
| **Pricing**     | Rules independent of Fleetbase          | PricingRule, TaxRule, Zone, Lane, ServiceArea           |
| **Support**     | Tickets, claims, incidents              | SupportTicket, Claim, Incident, OrderException          |
| **Integration** | API keys, webhooks, notifications       | ApiKey, Webhook, Notification                           |
| **Governance**  | RBAC, audit                             | Role, Permission, AuditLog                              |

---

## Context map

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Acquisition │────►│  Commercial  │────►│ Fulfillment  │
│ Visitor/Quote│     │ Booking/Merch│     │ Order/Ship   │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                     ┌──────▼───────┐      ┌──────▼───────┐
                     │   Pricing    │      │ Fleet/Track  │
                     │ Rules/Zones  │      │ Driver/Route │
                     └──────────────┘      └──────┬───────┘
                                                  │ adapter
                                           ┌──────▼───────┐
                                           │  Fleetbase   │
                                           │  (external)  │
                                           └──────────────┘
```

---

## Aggregate catalog

| Aggregate root       | Entities (internal)                              | Value objects                        | Consistency boundary        |
| -------------------- | ------------------------------------------------ | ------------------------------------ | --------------------------- |
| **Visitor**          | VisitorSession                                   | UTM tags, device fingerprint         | Session analytics           |
| **Quote**            | —                                                | Address, PackageSpec, PriceBreakdown | Single estimate TTL         |
| **Customer**         | —                                                | ContactInfo                          | Retail account              |
| **Booking**          | —                                                | BookingNumber                        | Quote → Order conversion    |
| **Order**            | Shipment, Stops, Parcels, OrderEvents            | TrackingNumber, Money                | Canonical lifecycle         |
| **Merchant**         | MerchantUsers, SavedAddresses, ApiKeys, Webhooks | PaymentTerms                         | B2B org                     |
| **MerchantContract** | —                                                | ContractRules                        | Pricing terms               |
| **Driver**           | Vehicles (optional)                              | ComplianceStatus                     | Partner profile             |
| **Fleet**            | Driver assignments                               | —                                    | Ops grouping                |
| **Dispatch**         | DispatchAssignment                               | —                                    | Driver ↔ Order link         |
| **Payment**          | —                                                | StripeRefs                           | Payment attempt             |
| **Invoice**          | InvoiceLines                                     | —                                    | Billing document            |
| **Refund**           | —                                                | —                                    | Money reversal              |
| **Wallet**           | WalletTransactions                               | Balance                              | Credits / driver earnings   |
| **Promotion**        | Coupon (subtype)                                 | DiscountSpec                         | Promo redemption            |
| **Claim**            | —                                                | Evidence                             | Insurance / damage          |
| **SupportTicket**    | —                                                | —                                    | Customer support            |
| **Incident**         | —                                                | —                                    | Ops safety / fleet incident |
| **PricingRule**      | —                                                | TariffConfig                         | Admin pricing               |
| **ServiceArea**      | Zones, Lanes                                     | GeoBounds                            | Serviceability              |
| **Notification**     | —                                                | ChannelPayload                       | Outbound comms              |
| **AuditLog**         | —                                                | —                                    | Immutable audit             |

---

## Entity reference

### Visitor

| Attribute         | Type   | Required | Notes                 |
| ----------------- | ------ | -------- | --------------------- |
| `id`              | string | ✓        | Session id (cookie)   |
| `ip_hash`         | string |          | Privacy-safe          |
| `utm_*`           | string |          | Marketing attribution |
| `quote_generated` | bool   |          | Funnel flag           |
| `last_quote_id`   | UUID   |          | Link to Quote         |

**Ownership:** Porterchain API — `visitor` module  
**Aggregate:** Visitor (root = VisitorSession)  
**Lifecycle:** `started` → `active` → `merged` (on Customer auth) → `archived`  
**Validation:** Session id unique; TTL 90 days inactive  
**Events:** `visitor.session_started`, `visitor.session_merged`

---

### Customer

| Attribute                | Type   | Required | Notes          |
| ------------------------ | ------ | -------- | -------------- |
| `id`                     | UUID   | ✓        | Porterchain PK |
| `clerk_user_id`          | string | ✓        | IdP reference  |
| `email`                  | string | ✓        |                |
| `phone`                  | E.164  |          |                |
| `visitor_session_id`     | string |          | Pre-merge link |
| `default_payment_method` | string |          | Stripe PM id   |

**Ownership:** Porterchain API — `customer` domain  
**Aggregate:** Customer  
**Lifecycle:** `provisional` (post-Clerk) → `active` → `suspended` → `deleted` (GDPR)  
**Validation:** Unique `clerk_user_id`; email format; phone E.164  
**Events:** `customer.registered`, `customer.authenticated`

---

### Merchant

| Attribute            | Type   | Required | Notes                              |
| -------------------- | ------ | -------- | ---------------------------------- |
| `id`                 | UUID   | ✓        |                                    |
| `status`             | enum   | ✓        | PENDING, ACTIVE, SUSPENDED, CLOSED |
| `company_name`       | string | ✓        |                                    |
| `clerk_org_id`       | string | ✓        |                                    |
| `payment_terms`      | enum   | ✓        | NET_15/30/45, IMMEDIATE            |
| `credit_limit_cents` | int    |          |                                    |
| `pricing_config`     | JSON   |          | Contract overrides                 |
| `delivery_zones`     | JSON   |          | Allowed zones                      |

**Ownership:** Porterchain API — `merchant` domain  
**Aggregate:** Merchant (includes MerchantUsers, ApiKeys, Webhooks)  
**Lifecycle:** `PENDING` → `ONBOARDING` → `ACTIVE` → `SUSPENDED` → `CLOSED`  
**Validation:** ACTIVE requires signed MerchantContract; credit within limit  
**Events:** `merchant.lead_created`, `merchant.approved`, `merchant.activated`

---

### MerchantContract

| Attribute                          | Type      | Required | Notes                                                    |
| ---------------------------------- | --------- | -------- | -------------------------------------------------------- |
| `id`                               | UUID      | ✓        |                                                          |
| `merchant_id`                      | UUID      | ✓        | FK                                                       |
| `name`                             | string    | ✓        | e.g. "2026 Standard B2B"                                 |
| `rules`                            | JSON      | ✓        | lane_pricing, zone_pricing, flat_rates, volume_discounts |
| `minimum_monthly_commitment_cents` | int       |          |                                                          |
| `effective_from` / `effective_to`  | timestamp |          |                                                          |
| `signed_at`                        | timestamp |          | Legal acceptance                                         |
| `is_active`                        | bool      | ✓        |                                                          |

**Ownership:** Porterchain API — `merchant` + `pricing-engine`  
**Aggregate:** MerchantContract  
**Lifecycle:** `draft` → `pending_signature` → `active` → `expired` → `superseded`  
**Validation:** One active contract per merchant per service type (configurable)  
**Events:** `contract.signed`, `contract.activated`, `pricing.updated`

---

### MerchantUser

| Attribute       | Type   | Required | Notes                                |
| --------------- | ------ | -------- | ------------------------------------ |
| `id`            | UUID   | ✓        |                                      |
| `merchant_id`   | UUID   | ✓        |                                      |
| `clerk_user_id` | string | ✓        |                                      |
| `role`          | enum   | ✓        | owner, admin, ops, finance, readonly |
| `email`         | string | ✓        |                                      |
| `is_active`     | bool   | ✓        |                                      |

**Ownership:** Merchant aggregate (child)  
**Validation:** User belongs to exactly one merchant org per Clerk org id  
**Events:** `merchant.user_invited`, `merchant.user_role_changed`

---

### Quote

| Attribute              | Type              | Required | Notes                         |
| ---------------------- | ----------------- | -------- | ----------------------------- |
| `id`                   | UUID              | ✓        |                               |
| `state`                | QuoteState        | ✓        | See lifecycle                 |
| `visitor_session_id`   | string            |          | Pre-auth                      |
| `customer_id`          | UUID              |          | Post-auth                     |
| `pickup` / `dropoff`   | Address           | ✓        |                               |
| `additional_stops`     | Address[]         |          | Multi-stop                    |
| `vehicle_class`        | enum              | ✓        | sedan…box20                   |
| `package_type`         | enum              | ✓        | looseParcel…ftlLoad           |
| `service_type`         | enum              |          | same_day, express, scheduled… |
| `weight_kg`            | decimal           |          |                               |
| `dimensions`           | PackageDimensions |          | L×W×H cm                      |
| `declared_value_cents` | int               |          |                               |
| `amount_cents`         | int               | ✓        | Locked at quote time          |
| `pricing_breakdown`    | PriceBreakdown    | ✓        | Audit                         |
| `promo_code`           | string            |          |                               |
| `expires_at`           | timestamp         | ✓        | Default 30 min                |
| `distance_meters`      | int               |          |                               |

**Ownership:** Porterchain API — `booking_engine`  
**Aggregate:** Quote  
**Lifecycle:** See [Quote lifecycle](#quote-lifecycle)  
**Validation:** Pickup/dropoff in ServiceArea; vehicle capacity ≥ package; amount > 0; expires_at > now  
**Events:** `quote.created`, `quote.expired`, `quote.accepted`

---

### Booking

| Attribute        | Type         | Required | Notes                       |
| ---------------- | ------------ | -------- | --------------------------- |
| `id`             | UUID         | ✓        |                             |
| `booking_number` | string       | ✓        | Human-readable              |
| `state`          | BookingState | ✓        | BOOKED, CANCELLED, REFUNDED |
| `quote_id`       | UUID         | ✓        | 1:1                         |
| `customer_id`    | UUID         | ✓        |                             |
| `order_id`       | UUID         |          | Set after payment           |

**Ownership:** Porterchain API — `booking_engine`  
**Aggregate:** Booking (bridge Quote → Order)  
**Lifecycle:** Created on payment success; terminal on cancel/refund  
**Validation:** quote.state must allow conversion; customer_id required  
**Events:** `booking.confirmed`, `booking.cancelled`

---

### Order

| Attribute            | Type       | Required | Notes                   |
| -------------------- | ---------- | -------- | ----------------------- |
| `id`                 | UUID       | ✓        |                         |
| `order_number`       | string     | ✓        | Internal                |
| `tracking_number`    | string     | ✓        | Public (unique)         |
| `state`              | OrderState | ✓        | Canonical               |
| `quote_id`           | UUID       |          | Retail only             |
| `customer_id`        | UUID       |          | Retail                  |
| `merchant_id`        | UUID       |          | B2B                     |
| `payment_terms`      | enum       | ✓        |                         |
| `amount_cents`       | int        | ✓        | Locked commercial price |
| `fleetbase_order_id` | string     |          | Adapter sync            |
| `pickup` / `dropoff` | Address    | ✓        | Denormalized snapshot   |
| `scheduled_at`       | timestamp  | ✓        |                         |
| `internal_reference` | string     |          | Merchant PO ref         |

**Ownership:** Porterchain API — **canonical aggregate root for fulfillment**  
**Aggregate:** Order (includes Shipment, Stops, Parcels, OrderEvents, Payments, Invoices)  
**Lifecycle:** See [Order lifecycle](#order-lifecycle)  
**Validation:** Retail requires payment or IMMEDIATE terms; B2B requires ACTIVE merchant; state transitions enforced  
**Events:** Full order event catalog — see [Event mappings](#event-mappings)

---

### Shipment

| Attribute              | Type   | Required | Notes                         |
| ---------------------- | ------ | -------- | ----------------------------- |
| `id`                   | UUID   | ✓        |                               |
| `order_id`             | UUID   | ✓        | Parent                        |
| `service_type`         | enum   | ✓        | same_day, express, LTL…       |
| `status`               | string |          | Mirrors order execution slice |
| `fleetbase_payload_id` | string |          | Optional multi-payload        |

**Ownership:** Order aggregate (child)  
**Note:** MVP is 1:1 Order↔Shipment; multi-shipment orders are a future extension.  
**Validation:** At least one Pickup Stop and one Delivery Stop

---

### Parcel

| Attribute              | Type              | Required | Notes          |
| ---------------------- | ----------------- | -------- | -------------- |
| `id`                   | UUID              | ✓        |                |
| `shipment_id`          | UUID              | ✓        |                |
| `package_type`         | enum              | ✓        | Classification |
| `weight_kg`            | decimal           |          |                |
| `dimensions`           | PackageDimensions |          |                |
| `declared_value_cents` | int               |          |                |
| `description`          | string            |          |                |
| `barcode`              | string            |          | Optional scan  |

**Ownership:** Shipment aggregate (child)  
**Validation:** weight ≤ vehicle capacity; dimensions fit vehicle class

---

### Package (value object)

Not a persisted entity — **classification** used on Quote/Parcel:

| Value          | Description            |
| -------------- | ---------------------- |
| `looseParcel`  | General parcel         |
| `documents`    | Documents only         |
| `medical`      | Medical supplies       |
| `furniture`    | Furniture / bulky      |
| `foodBeverage` | Perishable             |
| `construction` | Construction materials |
| `ltlPallet`    | LTL pallet             |
| `ftlLoad`      | Full truckload         |

---

### Stop

| Attribute          | Type       | Required | Notes                               |
| ------------------ | ---------- | -------- | ----------------------------------- |
| `id`               | UUID       | ✓        |                                     |
| `shipment_id`      | UUID       | ✓        |                                     |
| `sequence`         | int        | ✓        | Route order                         |
| `type`             | enum       | ✓        | PICKUP, DELIVERY, WAYPOINT          |
| `address`          | Address    | ✓        |                                     |
| `contact_name`     | string     |          |                                     |
| `contact_phone`    | string     |          |                                     |
| `instructions`     | string     |          |                                     |
| `scheduled_window` | TimeWindow |          |                                     |
| `completed_at`     | timestamp  |          |                                     |
| `status`           | enum       |          | pending, arrived, completed, failed |

**Ownership:** Shipment aggregate  
**Subtypes:** **Pickup** = `type=PICKUP`; **Delivery** = `type=DELIVERY`  
**Validation:** sequence unique per shipment; first stop typically PICKUP, last DELIVERY

---

### Driver

| Attribute              | Type   | Required | Notes                      |
| ---------------------- | ------ | -------- | -------------------------- |
| `id`                   | UUID   | ✓        |                            |
| `status`               | enum   | ✓        | PENDING, ACTIVE, SUSPENDED |
| `clerk_user_id`        | string |          | App auth                   |
| `full_name`            | string | ✓        |                            |
| `email`                | string | ✓        |                            |
| `fleetbase_driver_id`  | string |          | Adapter sync               |
| `license_verified`     | bool   |          |                            |
| `insurance_verified`   | bool   |          |                            |
| `vehicle_verified`     | bool   |          |                            |
| `wallet_balance_cents` | int    |          | Earnings ledger            |
| `is_online`            | bool   |          |                            |

**Ownership:** Porterchain API — `admin_engine` / `driver` domain  
**Aggregate:** Driver  
**Lifecycle:** `PENDING` → `UNDER_REVIEW` → `ACTIVE` → `SUSPENDED` → `OFFBOARDED`  
**Validation:** ACTIVE requires all compliance flags; unique fleetbase_driver_id  
**Events:** `driver.applied`, `driver.approved`, `driver.online`, `driver.offline`

---

### Vehicle

| Attribute               | Type      | Required | Notes                   |
| ----------------------- | --------- | -------- | ----------------------- |
| `id`                    | UUID      | ✓        |                         |
| `driver_id`             | UUID      |          | Nullable (pool vehicle) |
| `vehicle_class`         | enum      | ✓        |                         |
| `plate_number`          | string    | ✓        |                         |
| `make_model`            | string    |          |                         |
| `capacity_kg`           | decimal   |          |                         |
| `fleetbase_vehicle_id`  | string    |          |                         |
| `compliance_expires_at` | timestamp |          |                         |

**Ownership:** Driver aggregate (child) or Fleet  
**Validation:** plate unique; class matches assigned orders

---

### Fleet

| Attribute         | Type   | Required | Notes                 |
| ----------------- | ------ | -------- | --------------------- |
| `id`              | UUID   | ✓        |                       |
| `name`            | string | ✓        | e.g. "GTA Core Fleet" |
| `company_uuid`    | string |          | Fleetbase company ref |
| `service_area_id` | UUID   |          |                       |
| `is_active`       | bool   | ✓        |                       |

**Ownership:** Porterchain admin — logical grouping of drivers/vehicles  
**Note:** Operational dispatch uses Fleetbase; Fleet is Porterchain's partner registry view.

---

### Route

| Attribute            | Type      | Required | Notes            |
| -------------------- | --------- | -------- | ---------------- |
| `id`                 | UUID      | ✓        | Porterchain ref  |
| `fleetbase_route_id` | string    |          | External         |
| `driver_id`          | UUID      |          |                  |
| `order_ids`          | UUID[]    |          | Multi-stop batch |
| `polyline`           | string    |          | Encoded path     |
| `distance_meters`    | int       |          |                  |
| `duration_seconds`   | int       |          |                  |
| `optimized_at`       | timestamp |          |                  |

**Ownership:** **Reference entity** — geometry from Fleetbase via adapter; Porterchain stores snapshot for driver app  
**Validation:** Linked orders must be DISPATCH_READY or later

---

### Dispatch

| Attribute               | Type      | Required | Notes                                            |
| ----------------------- | --------- | -------- | ------------------------------------------------ |
| `id`                    | UUID      | ✓        |                                                  |
| `order_id`              | UUID      | ✓        |                                                  |
| `driver_id`             | UUID      |          |                                                  |
| `vehicle_id`            | UUID      |          |                                                  |
| `status`                | enum      | ✓        | pending, assigned, accepted, rejected, completed |
| `assigned_at`           | timestamp |          |                                                  |
| `assigned_by`           | actor     |          | dispatcher / system                              |
| `fleetbase_dispatch_id` | string    |          |                                                  |

**Ownership:** Order aggregate (DispatchAssignment)  
**Lifecycle:** `pending` → `assigned` → `accepted` | `rejected` → re-assign  
**Events:** `order.driver_assigned`, `order.driver_accepted`, `order.driver_rejected`

---

### TrackingEvent

| Attribute     | Type       | Required | Notes                                    |
| ------------- | ---------- | -------- | ---------------------------------------- |
| `id`          | UUID       | ✓        |                                          |
| `order_id`    | UUID       | ✓        |                                          |
| `event_type`  | string     | ✓        | status_change, location_ping, eta_update |
| `state`       | OrderState |          | Customer-visible                         |
| `latitude`    | float      |          |                                          |
| `longitude`   | float      |          |                                          |
| `occurred_at` | timestamp  | ✓        |                                          |
| `source`      | enum       | ✓        | driver_app, fleetbase_webhook, system    |

**Ownership:** Order aggregate (append-only timeline)  
**Validation:** Immutable after write; GPS within service area bounds (soft check)

---

### ProofOfDelivery (POD)

| Attribute             | Type      | Required | Notes                          |
| --------------------- | --------- | -------- | ------------------------------ |
| `id`                  | UUID      | ✓        |                                |
| `order_id`            | UUID      | ✓        |                                |
| `type`                | enum      | ✓        | photo, signature, barcode, otp |
| `storage_url`         | string    | ✓        | Object storage                 |
| `captured_at`         | timestamp | ✓        |                                |
| `gps_lat` / `gps_lng` | float     |          |                                |
| `fleetbase_proof_id`  | string    |          |                                |
| `verified`            | bool      |          | Compliance gate                |

**Ownership:** Order aggregate  
**Lifecycle:** `captured` → `verified` → `archived`  
**Events:** `order.pod_completed`, `fleetbase.pod_received`

---

### Payment

| Attribute                    | Type          | Required | Notes            |
| ---------------------------- | ------------- | -------- | ---------------- |
| `id`                         | UUID          | ✓        |                  |
| `quote_id`                   | UUID          | ✓        |                  |
| `order_id`                   | UUID          |          | Set post-booking |
| `customer_id`                | UUID          |          |                  |
| `status`                     | PaymentStatus | ✓        |                  |
| `amount_cents`               | int           | ✓        |                  |
| `stripe_payment_intent_id`   | string        |          |                  |
| `stripe_checkout_session_id` | string        |          |                  |
| `failure_reason`             | string        |          |                  |

**Ownership:** Order / Quote aggregate boundary  
**Lifecycle:** `PENDING` → `PROCESSING` → `SUCCEEDED` | `FAILED` | `CANCELLED`  
**Events:** `payment.succeeded`, `payment.failed`, `checkout.started`, `checkout.abandoned`

---

### Invoice

| Attribute           | Type   | Required | Notes     |
| ------------------- | ------ | -------- | --------- |
| `id`                | UUID   | ✓        |           |
| `invoice_number`    | string | ✓        |           |
| `order_id`          | UUID   | ✓        |           |
| `merchant_id`       | UUID   |          | B2B batch |
| `customer_id`       | UUID   | ✓        |           |
| `amount_cents`      | int    | ✓        |           |
| `due_date`          | date   |          | Net terms |
| `pdf_url`           | string |          |           |
| `stripe_invoice_id` | string |          |           |

**Ownership:** Billing context — linked to Order  
**Lifecycle:** `draft` → `issued` → `paid` | `overdue` → `void`  
**Events:** `order.invoiced`, `merchant.invoice_generated`, `merchant.invoice_overdue`

---

### Refund

| Attribute          | Type   | Required | Notes                               |
| ------------------ | ------ | -------- | ----------------------------------- |
| `id`               | UUID   | ✓        |                                     |
| `payment_id`       | UUID   | ✓        |                                     |
| `order_id`         | UUID   | ✓        |                                     |
| `amount_cents`     | int    | ✓        | ≤ original payment                  |
| `reason`           | string | ✓        |                                     |
| `status`           | enum   | ✓        | requested, approved, issued, failed |
| `stripe_refund_id` | string |          |                                     |

**Ownership:** Billing aggregate (child of Payment/Order)  
**Events:** `refund.requested`, `refund.issued`

---

### Wallet

| Attribute       | Type   | Required | Notes            |
| --------------- | ------ | -------- | ---------------- |
| `id`            | UUID   | ✓        |                  |
| `owner_type`    | enum   | ✓        | customer, driver |
| `owner_id`      | UUID   | ✓        |                  |
| `balance_cents` | int    | ✓        | ≥ 0              |
| `currency`      | string | ✓        | cad              |

**Ownership:** Customer or Driver aggregate (separate ledger)  
**Transactions:** credit, debit, payout, promo_credit, referral_credit  
**Validation:** Balance never negative; idempotent transaction ids

---

### DriverPayout

| Attribute                     | Type   | Required | Notes                             |
| ----------------------------- | ------ | -------- | --------------------------------- |
| `id`                          | UUID   | ✓        |                                   |
| `driver_id`                   | UUID   | ✓        |                                   |
| `amount_cents`                | int    | ✓        |                                   |
| `status`                      | enum   | ✓        | pending, processing, paid, failed |
| `reference`                   | string |          | Bank transfer ref                 |
| `period_start` / `period_end` | date   |          |                                   |

**Ownership:** Driver aggregate  
**Events:** `driver.payout_sent`, `driver.payout_failed`

---

### Promotion

| Attribute          | Type      | Required | Notes                                                               |
| ------------------ | --------- | -------- | ------------------------------------------------------------------- |
| `id`               | UUID      | ✓        |                                                                     |
| `code`             | string    | ✓        | Unique                                                              |
| `promotion_type`   | enum      | ✓        | coupon, referral_credit, wallet_credit, campaign, merchant_discount |
| `discount_percent` | float     |          |                                                                     |
| `discount_cents`   | int       |          |                                                                     |
| `merchant_id`      | UUID      |          | Scoped promo                                                        |
| `expires_at`       | timestamp |          |                                                                     |
| `is_active`        | bool      | ✓        |                                                                     |

**Ownership:** Pricing context — `services/pricing-engine`  
**Aggregate:** Promotion  
**Validation:** code unique; not expired; usage limits in config  
**Events:** `promotion.redeemed`, `promotion.expired`

---

### Coupon

**Subtype of Promotion** where `promotion_type = coupon`. Same fields; redeemed at Quote time.

---

### Claim

| Attribute     | Type | Required | Notes                                 |
| ------------- | ---- | -------- | ------------------------------------- |
| `id`          | UUID | ✓        |                                       |
| `order_id`    | UUID | ✓        |                                       |
| `claim_type`  | enum | ✓        | damage, loss, delay, billing          |
| `status`      | enum | ✓        | open, investigating, resolved, denied |
| `description` | text |          |                                       |
| `evidence`    | JSON |          | Photos, statements                    |
| `resolution`  | JSON |          | Payout / denial reason                |

**Ownership:** Support / billing context  
**Lifecycle:** `open` → `investigating` → `resolved` | `denied`  
**Events:** `claim.opened`, `claim.resolved`

---

### Incident

| Attribute     | Type      | Required | Notes                               |
| ------------- | --------- | -------- | ----------------------------------- |
| `id`          | UUID      | ✓        |                                     |
| `type`        | enum      | ✓        | safety, accident, compliance, fraud |
| `severity`    | enum      | ✓        | low, medium, high, critical         |
| `order_id`    | UUID      |          | Optional link                       |
| `driver_id`   | UUID      |          |                                     |
| `status`      | enum      | ✓        | open, closed                        |
| `reported_at` | timestamp | ✓        |                                     |

**Ownership:** Operations — may link Order but independent lifecycle  
**Distinction from OrderException:** Incident = safety/compliance; OrderException = delivery failure taxonomy

---

### SupportTicket

| Attribute     | Type   | Required | Notes                           |
| ------------- | ------ | -------- | ------------------------------- |
| `id`          | UUID   | ✓        |                                 |
| `status`      | enum   | ✓        | open, pending, resolved, closed |
| `priority`    | enum   | ✓        | low, normal, high, urgent       |
| `subject`     | string | ✓        |                                 |
| `customer_id` | UUID   |          |                                 |
| `merchant_id` | UUID   |          |                                 |
| `driver_id`   | UUID   |          |                                 |
| `order_id`    | UUID   |          |                                 |
| `assigned_to` | UUID   |          | Admin user                      |

**Ownership:** Support context  
**Events:** `support.ticket_created`, `support.ticket_resolved`

---

### Notification

| Attribute        | Type   | Required | Notes                             |
| ---------------- | ------ | -------- | --------------------------------- |
| `id`             | UUID   | ✓        |                                   |
| `recipient_type` | enum   | ✓        | customer, merchant, driver, admin |
| `recipient_id`   | UUID   | ✓        |                                   |
| `channel`        | enum   | ✓        | email, sms, push, in_app          |
| `template`       | string | ✓        |                                   |
| `status`         | enum   | ✓        | queued, sent, failed              |
| `correlation_id` | UUID   |          | order_id / quote_id               |

**Ownership:** Notification service — ephemeral delivery record

---

### Webhook (merchant outbound)

| Attribute     | Type     | Required | Notes                  |
| ------------- | -------- | -------- | ---------------------- |
| `id`          | UUID     | ✓        |                        |
| `merchant_id` | UUID     | ✓        |                        |
| `url`         | string   | ✓        | HTTPS                  |
| `secret`      | string   | ✓        | HMAC signing           |
| `events`      | string[] | ✓        | Subscribed event types |
| `is_active`   | bool     | ✓        |                        |

**Ownership:** Merchant aggregate (child)

---

### ApiKey

| Attribute      | Type      | Required | Notes           |
| -------------- | --------- | -------- | --------------- |
| `id`           | UUID      | ✓        |                 |
| `merchant_id`  | UUID      | ✓        |                 |
| `key_prefix`   | string    | ✓        | Display only    |
| `key_hash`     | string    | ✓        | Stored hash     |
| `scopes`       | string[]  | ✓        | API permissions |
| `expires_at`   | timestamp |          |                 |
| `last_used_at` | timestamp |          |                 |

**Ownership:** Merchant aggregate (child)  
**Validation:** scopes ⊆ merchant permissions

---

### Role & Permission

| Entity         | Notes                                                                  |
| -------------- | ---------------------------------------------------------------------- |
| **Role**       | Platform role: visitor, customer, merchant, driver, dispatcher, admin… |
| **Permission** | Atomic capability: `order:read`, `dispatch:manage`…                    |

**Ownership:** `packages/auth`, `porterchain_shared/auth/roles.py`  
**Enforcement:** API middleware — never client-only  
**Fleetbase sync:** Subset mapped via `fleetbase_roles.py` for console SSO

---

### AuditLog

| Attribute       | Type      | Required | Notes |
| --------------- | --------- | -------- | ----- |
| `id`            | UUID      | ✓        |       |
| `actor_user_id` | UUID      |          |       |
| `action`        | string    | ✓        |       |
| `resource_type` | string    | ✓        |       |
| `resource_id`   | UUID      |          |       |
| `payload`       | JSON      |          |       |
| `occurred_at`   | timestamp | ✓        |       |

**Ownership:** Governance — append-only (`AdminAuditLog`, `MerchantAuditLog`, `DomainEvent`)

---

### ServiceArea

| Attribute   | Type       | Required | Notes                       |
| ----------- | ---------- | -------- | --------------------------- |
| `id`        | UUID       | ✓        |                             |
| `name`      | string     | ✓        | e.g. "Greater Toronto Area" |
| `boundary`  | GeoPolygon | ✓        |                             |
| `is_active` | bool       | ✓        |                             |

**Ownership:** Pricing / operations config  
**Validation:** Quote pickup AND dropoff must intersect active service area

---

### PricingRule

| Attribute                | Type   | Required | Notes                                       |
| ------------------------ | ------ | -------- | ------------------------------------------- |
| `id`                     | UUID   | ✓        |                                             |
| `name`                   | string | ✓        |                                             |
| `tariff_type`            | enum   | ✓        | retail, merchant, zone, lane, vehicle, flat |
| `vehicle_class`          | enum   |          |                                             |
| `zone`                   | string |          |                                             |
| `merchant_id`            | UUID   |          |                                             |
| `base_cents`             | int    |          |                                             |
| `per_km_cents`           | int    |          |                                             |
| `fuel_surcharge_percent` | float  |          |                                             |
| `config`                 | JSON   |          | Custom rules                                |

**Ownership:** `services/pricing-engine` — persisted as `PricingTariff`  
**Events:** `pricing.updated`

---

### TaxRule

| Attribute             | Type   | Required | Notes                           |
| --------------------- | ------ | -------- | ------------------------------- |
| `id`                  | UUID   | ✓        | System config key `pricing_tax` |
| `hst_percent`         | float  | ✓        | Default 13% ON                  |
| `tax_included`        | bool   |          |                                 |
| `exempt_merchant_ids` | UUID[] |          |                                 |

**Ownership:** Pricing engine — `TaxService`

---

### Zone

| Attribute    | Type      | Required | Notes           |
| ------------ | --------- | -------- | --------------- |
| `id`         | UUID      | ✓        |                 |
| `code`       | string    | ✓        | e.g. `gta_core` |
| `name`       | string    | ✓        |                 |
| `bounds`     | GeoBounds | ✓        |                 |
| `multiplier` | float     | ✓        | Pricing factor  |

**Ownership:** Pricing engine — `ZoneService` / `PricingZone` table

---

### Lane

| Attribute               | Type   | Required | Notes                      |
| ----------------------- | ------ | -------- | -------------------------- |
| `id`                    | string | ✓        | e.g. `gta_core->gta_outer` |
| `origin_zone_code`      | string | ✓        |                            |
| `destination_zone_code` | string | ✓        |                            |
| `flat_rate_cents`       | int    |          | Contract override          |

**Ownership:** Pricing engine — embedded in MerchantContract.rules or PricingRule config  
**Validation:** Origin ≠ destination unless local delivery

---

## Lifecycles

### Quote lifecycle

```
DRAFT → QUOTE → QUOTE_EXPIRED
              ↘ BOOKING_PENDING → PAYMENT_PENDING → (converts to Order)
              ↘ CANCELLED
```

| State             | Meaning                             |
| ----------------- | ----------------------------------- |
| `DRAFT`           | Incomplete input                    |
| `QUOTE`           | Valid estimate, TTL running         |
| `QUOTE_EXPIRED`   | TTL elapsed                         |
| `BOOKING_PENDING` | Contact captured, Clerk in progress |
| `PAYMENT_PENDING` | Stripe session active               |
| `CANCELLED`       | User or system cancel               |

### Order lifecycle

See [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md) for full diagram.

**Happy path:** `BOOKED` → `DISPATCH_READY` → `DRIVER_ASSIGNED` → `DRIVER_ACCEPTED` → `DRIVER_EN_ROUTE` → `AT_PICKUP` → `PICKED_UP` → `IN_TRANSIT` → `AT_DESTINATION` → `DELIVERED` → `POD_COMPLETED` → `INVOICED` → `CLOSED`

**Merchant entry:** Skips quote/payment → starts at `BOOKED` with `payment_terms=NET_*`

---

## Event mappings

### Entity → domain events

| Entity         | Created                   | State change                         | Terminal                          |
| -------------- | ------------------------- | ------------------------------------ | --------------------------------- |
| Visitor        | `visitor.session_started` | `visitor.session_merged`             | —                                 |
| Quote          | `quote.created`           | `quote.expired`                      | —                                 |
| Customer       | `customer.registered`     | `customer.authenticated`             | —                                 |
| Booking        | `booking.confirmed`       | —                                    | `booking.cancelled`               |
| Order          | `order.booked`            | `order.*` (lifecycle)                | `order.closed`, `order.cancelled` |
| Payment        | `checkout.started`        | `payment.succeeded` / `failed`       | —                                 |
| Dispatch       | `order.driver_assigned`   | `order.driver_accepted` / `rejected` | —                                 |
| POD            | `fleetbase.pod_received`  | `order.pod_completed`                | —                                 |
| Invoice        | `order.invoiced`          | `merchant.invoice_overdue`           | —                                 |
| Refund         | `refund.requested`        | `refund.issued`                      | —                                 |
| Claim          | `claim.opened`            | `claim.resolved`                     | —                                 |
| Merchant       | `merchant.approved`       | `merchant.activated`                 | —                                 |
| Driver         | `driver.approved`         | `driver.payout_sent`                 | —                                 |
| Fleetbase sync | `fleetbase.order_created` | `fleetbase.status_updated`           | `fleetbase.sync_failed`           |

### Fleetbase webhook → Porterchain state

| Fleetbase event    | Order state       | TrackingEvent      |
| ------------------ | ----------------- | ------------------ |
| `order.dispatched` | `DRIVER_ASSIGNED` | `driver_assigned`  |
| `order.started`    | `PICKED_UP`       | `pickup_completed` |
| `order.completed`  | `DELIVERED`       | `delivered`        |
| `order.canceled`   | `CANCELLED`       | `cancelled`        |

Mapped by `EventTranslator` in `services/fleetbase-adapter/`.

### Order state → merchant webhook

| Porterchain state | Merchant webhook event   |
| ----------------- | ------------------------ |
| `BOOKED`          | `shipment.created`       |
| `DRIVER_ASSIGNED` | `shipment.dispatched`    |
| `PICKED_UP`       | `shipment.picked_up`     |
| `DELIVERED`       | `shipment.delivered`     |
| `POD_COMPLETED`   | `shipment.pod_available` |
| OrderException    | `shipment.exception`     |

---

## Module → entity map

| Module / path                    | Entities used                                                        |
| -------------------------------- | -------------------------------------------------------------------- |
| `website/`                       | Visitor, Quote (create), Customer (Clerk UI)                         |
| `apps/merchant-portal/`          | Merchant, MerchantUser, Order, Shipment, Invoice, ApiKey             |
| `apps/admin/`                    | All ops entities; PricingRule, Zone, Contract simulator              |
| `apps/api/booking_engine/`       | Visitor, Quote, Booking, Order, Payment                              |
| `apps/api/merchant_engine/`      | Merchant, Order, Shipment                                            |
| `apps/api/admin_engine/`         | Driver, Vehicle, Claim, SupportTicket, PricingRule                   |
| `services/pricing-engine/`       | PricingRule, TaxRule, Zone, Lane, Promotion, MerchantContract (read) |
| `services/fleetbase-adapter/`    | Order.fleetbase_order_id, Driver, Vehicle, Route, POD (sync only)    |
| `services/python/notifications/` | Notification                                                         |
| `packages/events/`               | DomainEvent envelope for all aggregates                              |
| `packages/types/`                | Role, Permission enums                                               |

---

## Value objects (shared)

| Value object          | Fields                                                                      | Used by                           |
| --------------------- | --------------------------------------------------------------------------- | --------------------------------- |
| **Address**           | formatted, place_id, lat, lng, street, city, province, postal_code, country | Quote, Order, Stop                |
| **PackageDimensions** | length_cm, width_cm, height_cm                                              | Quote, Parcel                     |
| **PriceBreakdown**    | base, distance, vehicle, weight, fuel, tax, discount, final, items[]        | Quote, Order                      |
| **Money**             | amount_cents, currency                                                      | Payment, Invoice, Order           |
| **TimeWindow**        | start, end                                                                  | Stop, Quote                       |
| **GeoBounds**         | min_lat, max_lat, min_lng, max_lng                                          | Zone, ServiceArea                 |
| **Actor**             | type, id                                                                    | OrderEvent, DomainEvent, AuditLog |

---

## Implementation status (reference)

| Entity           | DB table today                      | Notes                                        |
| ---------------- | ----------------------------------- | -------------------------------------------- |
| Visitor          | `visitor_sessions`                  | ✓                                            |
| Customer         | `customers`                         | ✓                                            |
| Quote            | `quotes`                            | ✓                                            |
| Booking          | `bookings`                          | ✓                                            |
| Order            | `orders`                            | ✓                                            |
| Payment          | `payments`                          | ✓                                            |
| Invoice          | `invoices`                          | ✓                                            |
| Merchant         | `merchants`                         | ✓                                            |
| MerchantUser     | `merchant_users`                    | ✓                                            |
| MerchantContract | `merchant_contracts`                | ✓                                            |
| Driver           | `drivers`                           | ✓                                            |
| Vehicle          | `vehicles`                          | ✓                                            |
| DriverPayout     | `driver_payouts`                    | ✓                                            |
| Promotion        | `promotions`                        | ✓                                            |
| PricingRule      | `pricing_tariffs`                   | ✓                                            |
| Zone             | `pricing_zones`                     | ✓                                            |
| Claim            | `claims`                            | ✓                                            |
| SupportTicket    | `support_tickets`                   | ✓                                            |
| ApiKey           | `merchant_api_keys`                 | ✓                                            |
| Webhook          | `merchant_webhooks`                 | ✓                                            |
| AuditLog         | `admin_audit_logs`, `domain_events` | ✓                                            |
| Shipment         | —                                   | **Target** — currently denormalized on Order |
| Parcel           | —                                   | **Target** — on Quote JSON today             |
| Stop             | —                                   | **Target** — pickup/dropoff on Order         |
| Route            | —                                   | **Target** — Fleetbase reference only        |
| Dispatch         | —                                   | **Target** — implied by order state          |
| TrackingEvent    | `order_events` (partial)            | Extend                                       |
| POD              | —                                   | **Target** — via Fleetbase sync              |
| Refund           | —                                   | **Target**                                   |
| Wallet           | `drivers.wallet_balance_cents`      | Partial                                      |
| Incident         | —                                   | **Target**                                   |
| Notification     | —                                   | **Target** — queue only                      |
| ServiceArea      | —                                   | **Target** — zones partial                   |
| Lane             | —                                   | **Target** — contract JSON                   |
| TaxRule          | `system_config`                     | ✓                                            |
| Fleet            | —                                   | **Target**                                   |

---

## Related documents

- [ENTITY_RELATIONSHIP_MODEL.md](./ENTITY_RELATIONSHIP_MODEL.md) — ER diagrams
- [BUSINESS_GLOSSARY.md](./BUSINESS_GLOSSARY.md) — Term definitions
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md) — State machine detail
- [EVENT_BUS.md](./EVENT_BUS.md) — Event catalog
- [PRICING_ENGINE.md](./PRICING_ENGINE.md) — Pricing entities
- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) — Sync boundaries

---

_Canonical domain specification. SQLAlchemy models in `apps/api/src/porterchain_api/` implement this model; see [ENTITY_RELATIONSHIP_MODEL.md](./ENTITY_RELATIONSHIP_MODEL.md) for table mappings._
---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
