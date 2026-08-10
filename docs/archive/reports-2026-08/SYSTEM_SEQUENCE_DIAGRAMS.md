# Porterchain — System Sequence Diagrams

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

---

## 1. Instant quote (anonymous)

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    participant Web as Website
    participant API as Porterchain API
    participant Maps as Google Maps
    participant Route as Valhalla/OSRM
    participant DB as PostgreSQL

    Visitor->>Web: Enter pickup, dropoff, vehicle, package, schedule
    Web->>Maps: Validate addresses (Places)
    Maps-->>Web: place_ids, lat/lng
    Web->>API: POST /v1/quotes
    API->>Route: Distance / duration
    Route-->>API: meters, seconds
    API->>API: Pricing engine
    API->>DB: Save Quote (QUOTE)
    API-->>Web: quote_id, amount, breakdown
    Web-->>Visitor: Display estimate (no login)
```

---

## 2. Retail booking — continue, Clerk, Stripe

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    participant Web as Website
    participant Clerk as Clerk
    participant API as Porterchain API
    participant Stripe as Stripe
    participant CRM as CRM DB

    Visitor->>Web: Continue Booking
    Web->>Visitor: Collect email + phone
    Web->>Clerk: Sign-up / Sign-in
    Clerk-->>Web: JWT session
    Web->>API: POST /v1/bookings (quote_id, contact, clerk_user_id)
    API->>API: Merge anonymous_session → customer
    API->>CRM: Upsert lead
    API->>API: State BOOKING_PENDING → PAYMENT_PENDING
    API->>Stripe: Create Checkout Session
    Stripe-->>API: session_url
    API-->>Web: redirect URL
    Web->>Stripe: Customer pays
    Stripe->>API: Webhook checkout.session.completed
    API->>API: Create Order (BOOKED)
    API->>API: Emit order.booked
    API-->>Stripe: 200 OK
    Stripe-->>Visitor: Redirect success URL
    Web->>Visitor: Customer portal (`apps/customer/`)
```

---

## 3. Abandoned checkout

```mermaid
sequenceDiagram
    autonumber
    participant API as Porterchain API
    participant DB as PostgreSQL
    participant Stripe as Stripe
    participant Mkt as Marketing job
    actor Customer

    API->>DB: checkout.started (PAYMENT_PENDING)
    Note over Customer: User leaves
    Stripe->>API: session.expired (optional)
    API->>DB: checkout.abandoned
    Mkt->>DB: Query abandoned (24h)
    Mkt->>Customer: Remarketing email with resume link
    Customer->>API: Resume checkout (same quote if valid)
```

---

## 4. Order → Fleetbase dispatch

```mermaid
sequenceDiagram
    autonumber
    participant API as Porterchain API
    participant Bridge as fleetbase_engine / Adapter
    participant FB as Fleetbase API
    participant Disp as Dispatcher (Admin)
    participant Driver as Driver App

    API->>Bridge: order.booked event
    Bridge->>FB: Create order/payload
    FB-->>Bridge: fleetbase_order_id
    Bridge->>API: Update order DISPATCH_READY
    Disp->>FB: Assign driver + vehicle
    FB->>Bridge: Webhook status / poll
    Bridge->>API: order.driver_assigned
    API->>Driver: Push / poll assigned jobs
    Driver->>API: Accept job
    API->>API: DRIVER_ACCEPTED
```

---

## 5. Driver execution & POD

```mermaid
sequenceDiagram
    autonumber
    actor Driver
    participant App as Driver App
    participant API as Porterchain API
    participant FB as Fleetbase API
    participant Store as Object Storage

    Driver->>App: Start route
    App->>API: POST routes/{id}/start
    API->>FB: Sync EN_ROUTE
    loop Location
        App->>API: POST /driver/location
    end
    Driver->>App: Arrive pickup
    App->>API: POST .../arrive
    Driver->>App: Confirm pickup
    App->>API: POST .../pickup
    Driver->>App: Deliver + POD photo/signature
    App->>API: Multipart POD upload
    API->>Store: Save artifacts
    API->>FB: Sync DELIVERED + POD
    API->>API: order.pod_completed
```

---

## 6. Merchant onboarding

```mermaid
sequenceDiagram
    autonumber
    actor Prospect
    participant Sales as Sales (Admin)
    participant API as Porterchain API
    participant Clerk as Clerk
    actor Merchant
    participant Portal as Merchant Portal
    participant Compliance as Compliance (Admin)

    Prospect->>API: For-business inquiry
    API->>API: Create lead
    Sales->>API: Approve merchant
    API->>Clerk: Create organization + invite
    Clerk->>Merchant: Invite email
    Merchant->>Portal: Complete onboarding wizard
    Portal->>API: Profile, documents, contract sign
    API->>Compliance: Review queue
    Compliance->>API: Approve ACTIVE
    API->>Merchant: Welcome + portal access
```

---

## 7. Merchant shipment (Net 30)

```mermaid
sequenceDiagram
    autonumber
    actor Merchant
    participant Portal as Merchant Portal
    participant API as Porterchain API
    participant FB as Fleetbase API

    Merchant->>Portal: Book delivery
    Portal->>API: POST /v1/merchant/shipments
    API->>API: Validate contract ACTIVE, terms NET_30
    API->>API: Create Order (BOOKED)
    API->>FB: Bridge create order
    Note over API,FB: Same execution flow as retail
    API->>API: Monthly invoice batch
    API->>Merchant: Invoice email
```

---

## 8. Exception — driver reject & reassign

```mermaid
sequenceDiagram
    autonumber
    actor Driver
    participant App as Driver App
    participant API as Porterchain API
    participant FB as Fleetbase API
    participant Disp as Dispatcher

    API->>App: New assignment
    Driver->>App: Reject
    App->>API: POST reject + reason
    API->>API: exception.opened (DRIVER_REJECT)
    API->>API: Auto re-assign attempt
    alt Auto assign success
        API->>FB: Reassign driver
        API->>App: Notify next driver
    else Max retries
        API->>Disp: Escalation alert
        Disp->>FB: Manual assign
    end
```

---

## 9. Refund workflow

```mermaid
sequenceDiagram
    autonumber
    actor Support
    participant Admin as Admin
    participant API as Porterchain API
    participant Stripe as Stripe
    actor Customer

    Support->>Admin: Approve refund
    Admin->>API: POST /orders/{id}/refund
    API->>Stripe: Create refund
    Stripe-->>API: refund_id
    API->>API: State REFUNDED → CLOSED
    API->>Customer: Email confirmation
```

---

## 10. Customer tracking (read path)

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Dash as Customer Dashboard
    participant API as Porterchain API
    participant FB as Fleetbase API

    Customer->>Dash: View active order
    Dash->>API: GET /v1/customer/orders/{id}
    API->>FB: Fetch live GPS (cached)
    FB-->>API: location, ETA
    API-->>Dash: status + map data
    Dash-->>Customer: Tracking UI
```

---

## Component context

```mermaid
flowchart LR
    subgraph Porterchain
        Web[Website]
        CP[Customer Portal]
        MP[Merchant Portal]
        AD[Admin]
        DA[Mobile Driver]
        MC[Mobile Customer]
        DP[Driver Portal]
        API[Porterchain API]
    end
    subgraph External
        Clerk[Clerk]
        Stripe[Stripe]
        Maps[Google Maps]
    end
    subgraph Engine
        FB[Fleetbase]
        Val[Valhalla/OSRM]
    end
    Web --> API
    CP --> API
    MP --> API
    AD --> API
    DA --> API
    MC --> API
    DP --> API
    Web --> Clerk
    MP --> Clerk
    API --> Clerk
    API --> Stripe
    API --> FB
    API --> Val
    Web --> Maps
    DA --> Maps
```

---

## Related documents

- [BUSINESS_WORKFLOW.md](./BUSINESS_WORKFLOW.md)
- [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [EVENT_BUS.md](./EVENT_BUS.md)

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
