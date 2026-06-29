# Porterchain — Entity Relationship Model

**Document version:** 2.0  
**Date:** June 29, 2026  
**Status:** Canonical — aligned with [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)

---

## Data ownership

| Store                      | Owner                                | Entities                                 |
| -------------------------- | ------------------------------------ | ---------------------------------------- |
| **Porterchain PostgreSQL** | Porterchain API                      | All entities below except Fleetbase refs |
| **Fleetbase MySQL**        | Fleetbase (read-only to Porterchain) | Operational orders, drivers, routes, GPS |
| **Redis**                  | Infrastructure                       | Queues, cache, rate limits               |
| **Object storage**         | Porterchain                          | POD images, invoice PDFs, documents      |
| **Clerk**                  | Clerk                                | Credentials, org memberships             |
| **Stripe**                 | Stripe                               | Payment intents, refunds, invoices       |

**Golden rule:** `order.id` and `tracking_number` are customer-facing. `fleetbase_order_id` is an operational foreign key — never exposed as primary identity.

---

## Master ER diagram

```mermaid
erDiagram
    VISITOR ||--o{ QUOTE : generates
    VISITOR ||--o| CUSTOMER : merges_into

    CUSTOMER ||--o{ QUOTE : requests
    CUSTOMER ||--o{ BOOKING : confirms
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ PAYMENT : makes
    CUSTOMER ||--o| WALLET : owns

    QUOTE ||--o| BOOKING : converts_to
    QUOTE ||--o| PAYMENT : checkout_for
    QUOTE }o--o| PROMOTION : applies

    BOOKING ||--|| ORDER : creates

    ORDER ||--|| SHIPMENT : contains
    ORDER ||--o{ ORDER_EVENT : logs
    ORDER ||--o{ TRACKING_EVENT : tracks
    ORDER ||--o{ PAYMENT : paid_by
    ORDER ||--o{ INVOICE : billed_by
    ORDER ||--o{ REFUND : may_refund
    ORDER ||--o{ ORDER_EXCEPTION : may_have
    ORDER ||--o| DISPATCH : assigned_via
    ORDER ||--o{ PROOF_OF_DELIVERY : proves
  ORDER }o--o| FLEETBASE_ORDER : syncs_to

    SHIPMENT ||--|{ STOP : has
    SHIPMENT ||--|{ PARCEL : carries
    SHIPMENT }o--|| SERVICE_TYPE : classified_as

    STOP }o--|| ADDRESS : at
    STOP ||--o| PICKUP : subtype
    STOP ||--o| DELIVERY : subtype

    MERCHANT ||--o{ MERCHANT_USER : employs
    MERCHANT ||--o{ MERCHANT_CONTRACT : governed_by
    MERCHANT ||--o{ ORDER : ships
    MERCHANT ||--o{ API_KEY : issues
    MERCHANT ||--o{ WEBHOOK : configures
    MERCHANT ||--o{ SAVED_ADDRESS : stores
    MERCHANT }o--o{ PROMOTION : scoped_to

    MERCHANT_CONTRACT }o--o{ PRICING_RULE : references
    MERCHANT_CONTRACT }o--o{ LANE : defines
    MERCHANT_CONTRACT }o--o{ ZONE : defines

    DISPATCH }o--|| DRIVER : assigns
    DISPATCH }o--o| VEHICLE : uses

    DRIVER ||--o{ VEHICLE : operates
    DRIVER ||--o{ DRIVER_PAYOUT : receives
    DRIVER }o--o| FLEET : member_of
    DRIVER }o--o| FLEETBASE_DRIVER : syncs_to
    DRIVER }o--o| WALLET : owns

    FLEET ||--o{ DRIVER : includes
    FLEET }o--|| SERVICE_AREA : operates_in

    ROUTE }o--o{ ORDER : serves
    ROUTE }o--|| DRIVER : driven_by
    ROUTE }o--o| FLEETBASE_ROUTE : syncs_to

    SERVICE_AREA ||--|{ ZONE : contains
    ZONE ||--o{ LANE : connects

    PRICING_RULE }o--o| ZONE : applies_in
    PRICING_RULE }o--o| VEHICLE : applies_to
    TAX_RULE ||--o{ QUOTE : taxes
    TAX_RULE ||--o{ ORDER : taxes

    CLAIM }o--|| ORDER : filed_on
    INCIDENT }o--o| ORDER : related_to
    INCIDENT }o--o| DRIVER : involves
    SUPPORT_TICKET }o--o| ORDER : about
    SUPPORT_TICKET }o--o| CUSTOMER : from
    SUPPORT_TICKET }o--o| MERCHANT : from
    SUPPORT_TICKET }o--o| DRIVER : from

    NOTIFICATION }o--o| CUSTOMER : sent_to
    NOTIFICATION }o--o| MERCHANT_USER : sent_to
    NOTIFICATION }o--o| DRIVER : sent_to

    ADMIN_USER }o--o{ ROLE : has
    ROLE ||--|{ PERMISSION : grants
    MERCHANT_USER }o--o{ ROLE : has_merchant_role

    AUDIT_LOG }o--o| ORDER : audits
    AUDIT_LOG }o--o| MERCHANT : audits

    LEAD ||--o| MERCHANT : converts_to
    LEAD }o--o| QUOTE : sourced_from
    ABANDONED_CHECKOUT }o--|| QUOTE : abandoned
```

---

## Acquisition context

```mermaid
erDiagram
    VISITOR {
        string id PK
        string ip_hash
        json utm
        bool quote_generated
        string last_quote_id FK
        timestamp created_at
    }

    QUOTE {
        uuid id PK
        string state
        string visitor_session_id FK
        uuid customer_id FK
        json pickup
        json dropoff
        json additional_stops
        string vehicle_class
        string package_type
        string service_type
        int amount_cents
        json pricing_breakdown
        int distance_meters
        timestamp expires_at
    }

    LEAD {
        uuid id PK
        string source
        string email
        string phone
        string stage
        uuid quote_id FK
        uuid customer_id FK
    }

    ABANDONED_CHECKOUT {
        uuid id PK
        uuid quote_id FK
        uuid customer_id FK
        string email
        string stripe_checkout_session_id
    }

    VISITOR ||--o{ QUOTE : generates
    QUOTE ||--o| LEAD : creates
    QUOTE ||--o| ABANDONED_CHECKOUT : may_abandon
```

---

## Commercial context

```mermaid
erDiagram
    CUSTOMER {
        uuid id PK
        string clerk_user_id UK
        string email
        string phone
        string visitor_session_id
    }

    BOOKING {
        uuid id PK
        string booking_number UK
        string state
        uuid quote_id FK UK
        uuid customer_id FK
        uuid order_id FK UK
    }

    MERCHANT {
        uuid id PK
        string status
        string company_name
        string clerk_org_id UK
        string payment_terms
        int credit_limit_cents
        json pricing_config
    }

    MERCHANT_USER {
        uuid id PK
        uuid merchant_id FK
        string clerk_user_id UK
        string role
        string email
    }

    MERCHANT_CONTRACT {
        uuid id PK
        uuid merchant_id FK
        string name
        json rules
        int minimum_monthly_commitment_cents
        bool is_active
        timestamp effective_from
        timestamp effective_to
    }

    CUSTOMER ||--o{ BOOKING : confirms
    MERCHANT ||--o{ MERCHANT_USER : has
    MERCHANT ||--o{ MERCHANT_CONTRACT : signs
```

---

## Fulfillment context

```mermaid
erDiagram
    ORDER {
        uuid id PK
        string order_number UK
        string tracking_number UK
        string state
        uuid quote_id FK
        uuid customer_id FK
        uuid merchant_id FK
        string payment_terms
        int amount_cents
        string fleetbase_order_id
        json pickup
        json dropoff
        timestamp scheduled_at
    }

    SHIPMENT {
        uuid id PK
        uuid order_id FK UK
        string service_type
        string status
        string fleetbase_payload_id
    }

    PARCEL {
        uuid id PK
        uuid shipment_id FK
        string package_type
        float weight_kg
        json dimensions
        int declared_value_cents
    }

    STOP {
        uuid id PK
        uuid shipment_id FK
        int sequence
        string type
        json address
        string status
        timestamp completed_at
    }

    DISPATCH {
        uuid id PK
        uuid order_id FK
        uuid driver_id FK
        uuid vehicle_id FK
        string status
        timestamp assigned_at
    }

    ORDER_EVENT {
        uuid id PK
        uuid order_id FK
        string event_type
        string from_state
        string to_state
        string actor_type
        timestamp occurred_at
    }

    TRACKING_EVENT {
        uuid id PK
        uuid order_id FK
        string event_type
        float latitude
        float longitude
        timestamp occurred_at
        string source
    }

    PROOF_OF_DELIVERY {
        uuid id PK
        uuid order_id FK
        string type
        string storage_url
        float gps_lat
        float gps_lng
        bool verified
    }

    ORDER ||--|| SHIPMENT : has
    SHIPMENT ||--|{ PARCEL : contains
    SHIPMENT ||--|{ STOP : has
    ORDER ||--o| DISPATCH : dispatch
    ORDER ||--o{ ORDER_EVENT : events
    ORDER ||--o{ TRACKING_EVENT : tracking
    ORDER ||--o{ PROOF_OF_DELIVERY : pod
```

---

## Fleet context

```mermaid
erDiagram
    FLEET {
        uuid id PK
        string name
        string company_uuid
        uuid service_area_id FK
    }

    DRIVER {
        uuid id PK
        string status
        string clerk_user_id
        string full_name
        string fleetbase_driver_id
        int wallet_balance_cents
        bool is_online
    }

    VEHICLE {
        uuid id PK
        uuid driver_id FK
        string vehicle_class
        string plate_number UK
        string fleetbase_vehicle_id
        float capacity_kg
    }

    ROUTE {
        uuid id PK
        string fleetbase_route_id
        uuid driver_id FK
        json order_ids
        string polyline
        int distance_meters
    }

    DRIVER_PAYOUT {
        uuid id PK
        uuid driver_id FK
        int amount_cents
        string status
        string reference
    }

    FLEET ||--o{ DRIVER : includes
    DRIVER ||--o{ VEHICLE : operates
    DRIVER ||--o{ DRIVER_PAYOUT : paid
    DRIVER ||--o{ ROUTE : drives
```

---

## Billing context

```mermaid
erDiagram
    PAYMENT {
        uuid id PK
        uuid quote_id FK
        uuid order_id FK
        uuid customer_id FK
        string status
        int amount_cents
        string stripe_payment_intent_id
        string stripe_checkout_session_id
    }

    INVOICE {
        uuid id PK
        string invoice_number UK
        uuid order_id FK
        uuid customer_id FK
        int amount_cents
        string pdf_url
    }

    REFUND {
        uuid id PK
        uuid payment_id FK
        uuid order_id FK
        int amount_cents
        string status
        string stripe_refund_id
    }

    WALLET {
        uuid id PK
        string owner_type
        uuid owner_id
        int balance_cents
        string currency
    }

    WALLET_TRANSACTION {
        uuid id PK
        uuid wallet_id FK
        string type
        int amount_cents
        string reference
    }

    ORDER ||--o{ PAYMENT : payments
    ORDER ||--o{ INVOICE : invoices
    PAYMENT ||--o{ REFUND : refunds
    WALLET ||--o{ WALLET_TRANSACTION : ledger
```

---

## Pricing context

```mermaid
erDiagram
    PRICING_RULE {
        uuid id PK
        string name
        string tariff_type
        string vehicle_class
        string zone
        uuid merchant_id FK
        int base_cents
        int per_km_cents
        float fuel_surcharge_percent
        json config
    }

    TAX_RULE {
        string key PK
        float hst_percent
        bool tax_included
        json exempt_merchant_ids
    }

    ZONE {
        uuid id PK
        string code UK
        string name
        json bounds
        float multiplier
    }

    LANE {
        string id PK
        string origin_zone_code FK
        string destination_zone_code FK
        int flat_rate_cents
    }

    SERVICE_AREA {
        uuid id PK
        string name
        json boundary
        bool is_active
    }

    PROMOTION {
        uuid id PK
        string code UK
        string promotion_type
        uuid merchant_id FK
        float discount_percent
        int discount_cents
        bool is_active
    }

    SERVICE_AREA ||--|{ ZONE : contains
    ZONE ||--o{ LANE : origin
    ZONE ||--o{ LANE : destination
    PRICING_RULE }o--o| ZONE : zone
    PRICING_RULE }o--o| MERCHANT : merchant
    PROMOTION }o--o| MERCHANT : scoped
```

---

## Support & governance context

```mermaid
erDiagram
    CLAIM {
        uuid id PK
        uuid order_id FK
        string claim_type
        string status
        json evidence
        json resolution
    }

    INCIDENT {
        uuid id PK
        string type
        string severity
        uuid order_id FK
        uuid driver_id FK
        string status
    }

    SUPPORT_TICKET {
        uuid id PK
        string status
        string priority
        string subject
        uuid order_id FK
        uuid customer_id FK
        uuid merchant_id FK
        uuid driver_id FK
    }

    ORDER_EXCEPTION {
        uuid id PK
        uuid order_id FK
        string type
        string status
        json evidence
    }

    API_KEY {
        uuid id PK
        uuid merchant_id FK
        string key_prefix
        string key_hash
        json scopes
    }

    WEBHOOK {
        uuid id PK
        uuid merchant_id FK
        string url
        string secret
        json events
    }

    NOTIFICATION {
        uuid id PK
        string recipient_type
        uuid recipient_id
        string channel
        string template
        string status
    }

    AUDIT_LOG {
        uuid id PK
        uuid actor_user_id
        string action
        string resource_type
        uuid resource_id
        json payload
    }

    DOMAIN_EVENT {
        uuid id PK
        string event_type
        string aggregate_type
        uuid aggregate_id
        json payload
    }

    MERCHANT ||--o{ API_KEY : keys
    MERCHANT ||--o{ WEBHOOK : hooks
    ORDER ||--o{ CLAIM : claims
    ORDER ||--o{ ORDER_EXCEPTION : exceptions
```

---

## Identity & RBAC

```mermaid
erDiagram
    ADMIN_USER {
        uuid id PK
        string clerk_user_id UK
        string email
        string role
        string fleetbase_user_uuid
    }

    IDENTITY_LINK {
        uuid id PK
        string clerk_user_id
        string user_type
        uuid porterchain_user_id
        json fleetbase_permissions
    }

    ROLE {
        string id PK
        string name
    }

    PERMISSION {
        string id PK
        string scope
    }

    ROLE ||--|{ PERMISSION : grants
    ADMIN_USER }o--|| ROLE : has
    MERCHANT_USER }o--|| ROLE : has_merchant_role
    IDENTITY_LINK }o--|| ADMIN_USER : links
    IDENTITY_LINK }o--|| MERCHANT_USER : links
    IDENTITY_LINK }o--|| DRIVER : links
```

---

## Fleetbase external references

| Porterchain entity | Fleetbase entity | FK field               |
| ------------------ | ---------------- | ---------------------- |
| Order              | order            | `fleetbase_order_id`   |
| Driver             | driver           | `fleetbase_driver_id`  |
| Vehicle            | vehicle          | `fleetbase_vehicle_id` |
| Route              | route / tracker  | `fleetbase_route_id`   |
| ProofOfDelivery    | proof            | `fleetbase_proof_id`   |
| Fleet              | company          | `company_uuid`         |
| Shipment           | order payload    | `fleetbase_payload_id` |

**No Porterchain business entity is stored only in Fleetbase.**

---

## Cardinality summary

| Relationship        | Cardinality | Notes                                |
| ------------------- | ----------- | ------------------------------------ |
| Visitor → Quote     | 1:N         | Session may generate multiple quotes |
| Quote → Booking     | 1:1         | Retail conversion                    |
| Booking → Order     | 1:1         | Post-payment                         |
| Order → Shipment    | 1:1         | MVP; future 1:N                      |
| Shipment → Stop     | 1:N         | Min 2 (pickup + delivery)            |
| Shipment → Parcel   | 1:N         | MVP often 1                          |
| Order → Payment     | 1:N         | Retries, partial (future)            |
| Order → Invoice     | 1:N         | Adjustments, merchant statements     |
| Merchant → Contract | 1:N         | Historical versions                  |
| Merchant → Order    | 1:N         | B2B volume                           |
| Driver → Vehicle    | 1:N         | Partner may have multiple            |
| Driver → Dispatch   | 1:N         | Over time                            |
| Order → Dispatch    | 1:1         | Active assignment                    |
| Promotion → Quote   | N:1         | One code per quote                   |
| Zone → Lane         | N:M         | Via origin/destination codes         |

---

## Persistence mapping (current implementation)

| Logical entity    | Physical table                      | Status                          |
| ----------------- | ----------------------------------- | ------------------------------- |
| Visitor           | `visitor_sessions`                  | Live                            |
| Customer          | `customers`                         | Live                            |
| Quote             | `quotes`                            | Live                            |
| Booking           | `bookings`                          | Live                            |
| Order             | `orders`                            | Live                            |
| Payment           | `payments`                          | Live                            |
| Invoice           | `invoices`                          | Live                            |
| OrderEvent        | `order_events`                      | Live                            |
| DomainEvent       | `domain_events`                     | Live                            |
| OrderException    | `order_exceptions`                  | Live                            |
| Lead              | `leads`                             | Live                            |
| AbandonedCheckout | `abandoned_checkouts`               | Live                            |
| Merchant          | `merchants`                         | Live                            |
| MerchantUser      | `merchant_users`                    | Live                            |
| MerchantContract  | `merchant_contracts`                | Live                            |
| ApiKey            | `merchant_api_keys`                 | Live                            |
| Webhook           | `merchant_webhooks`                 | Live                            |
| Driver            | `drivers`                           | Live                            |
| Vehicle           | `vehicles`                          | Live                            |
| DriverPayout      | `driver_payouts`                    | Live                            |
| Promotion         | `promotions`                        | Live                            |
| PricingRule       | `pricing_tariffs`                   | Live                            |
| Zone              | `pricing_zones`                     | Live                            |
| TaxRule           | `system_config` (key=`pricing_tax`) | Live                            |
| Claim             | `claims`                            | Live                            |
| SupportTicket     | `support_tickets`                   | Live                            |
| AuditLog          | `admin_audit_logs`                  | Live                            |
| Shipment          | —                                   | Target (`shipments`)            |
| Parcel            | —                                   | Target (`parcels`)              |
| Stop              | —                                   | Target (`stops`)                |
| Dispatch          | —                                   | Target (`dispatches`)           |
| TrackingEvent     | —                                   | Target (extend `order_events`)  |
| ProofOfDelivery   | —                                   | Target (`proof_of_delivery`)    |
| Refund            | —                                   | Target (`refunds`)              |
| Wallet            | —                                   | Target (`wallets`)              |
| Incident          | —                                   | Target (`incidents`)            |
| Notification      | —                                   | Target (`notifications`)        |
| Route             | —                                   | Target (`routes`)               |
| Fleet             | —                                   | Target (`fleets`)               |
| ServiceArea       | —                                   | Target (`service_areas`)        |
| Lane              | —                                   | Embedded in contract/rules JSON |

---

## Recommended indexes

| Table             | Index                              | Purpose          |
| ----------------- | ---------------------------------- | ---------------- |
| `orders`          | `(state, scheduled_at)`            | Dispatch queue   |
| `orders`          | `(tracking_number)` UNIQUE         | Public tracking  |
| `orders`          | `(merchant_id, created_at)`        | Merchant list    |
| `orders`          | `(customer_id, created_at)`        | Customer history |
| `orders`          | `(fleetbase_order_id)`             | Webhook lookup   |
| `quotes`          | `(visitor_session_id)`             | Session merge    |
| `quotes`          | `(expires_at) WHERE state='QUOTE'` | Expiry job       |
| `dispatches`      | `(driver_id, status)`              | Driver app       |
| `tracking_events` | `(order_id, occurred_at)`          | Timeline         |
| `domain_events`   | `(aggregate_type, aggregate_id)`   | Event replay     |
| `promotions`      | `(code)` UNIQUE                    | Redemption       |
| `pricing_zones`   | `(code)` UNIQUE                    | Zone lookup      |

---

## Anonymous session merge

```
visitor_sessions.id (cookie)
    → quotes.visitor_session_id
    → customers.visitor_session_id (on Clerk auth)
    → UPDATE quotes, abandoned_checkouts SET customer_id = :id
    → EMIT visitor.session_merged
```

---

## Related documents

- [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) — Aggregate boundaries, validation, lifecycle
- [BUSINESS_GLOSSARY.md](./BUSINESS_GLOSSARY.md) — Term definitions
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)
- [EVENT_FLOW.md](./EVENT_FLOW.md)

---

_Logical ER model for Porterchain-owned data. Fleetbase schema governed by upstream._
