# Porterchain — Master Architecture Rules

> **You are a Principal Software Architect working on Porterchain.**
>
> Before **every** task, you must read this document. These rules override every
> future prompt unless explicitly changed by the system architect. Never violate
> these architectural boundaries.

---

## 1. Porterchain is the source of truth

- Porterchain owns **all** business logic.
- Fleetbase is **only** the logistics execution engine.
- Never move Porterchain business logic into Fleetbase.

---

## 2. Fleetbase responsibilities

Fleetbase handles **operational logistics only**:

- Driver management
- Vehicle management
- Fleet management
- Dispatch
- Route optimization
- Live GPS tracking
- Waypoints
- Proof of delivery
- Driver status
- Driver availability
- Delivery status
- Route execution
- Geofencing
- Operational maps
- Navigation
- Dispatch queue
- Route progress
- Delivery completion
- Fleet operations

**Constraints**

- Keep Fleetbase as close as possible to the upstream open-source project.
- Never place Porterchain business logic inside Fleetbase.
- Never store commercial business data inside Fleetbase unless absolutely required for operational execution.

---

## 3. Porterchain responsibilities

Porterchain owns every customer-facing and business-facing feature.

| Domain                 | Capabilities                                                                                                                           |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Web & booking**      | Website, public booking, instant quotes                                                                                                |
| **Pricing**            | Pricing engine, distance calculations, vehicle pricing, contract pricing, merchant pricing, fuel surcharge, taxes, coupons, promotions |
| **Payments & billing** | Stripe payments, invoices, billing, refunds, credit notes, wallet                                                                      |
| **Accounts & portals** | Merchant accounts, merchant portal, customer portal                                                                                    |
| **CRM & sales**        | CRM, sales pipeline, leads, companies, contacts, contracts, documents, CSV upload, Excel upload                                        |
| **Developer**          | API keys, developer portal                                                                                                             |
| **Auth**               | Authentication, authorization, Clerk, RBAC, user management                                                                            |
| **Notifications**      | Email, Firebase push, SMS, WhatsApp (future)                                                                                           |
| **Insights**           | Analytics, reports, dashboards                                                                                                         |
| **Marketing**          | SEO, blog, news                                                                                                                        |
| **Support**            | Support, claims, incidents, customer service, driver support, merchant support                                                         |
| **Platform**           | AI features, audit logs, business rules                                                                                                |

> Everything related to commercial operations belongs inside Porterchain.

---

## 4. Communication rule

Porterchain **never** communicates directly with Fleetbase from the frontend.
The flow must always be:

```
Website
  ↓
Porterchain Backend API
  ↓
Fleetbase Adapter Service
  ↓
Fleetbase API
```

Frontend applications never call Fleetbase directly.

---

## 5. Fleetbase adapter

All Fleetbase communication must go through **`services/fleetbase-adapter`**. Never bypass this layer.

**Adapter responsibilities**

- Authentication
- Order mapping
- Driver mapping
- Vehicle mapping
- Tracking mapping
- Webhook processing
- Error handling
- Retry logic
- Version compatibility
- Logging

---

## 6. Database ownership

### Porterchain database owns

- Users
- Customers
- Visitors
- Merchants
- Merchant users
- Quotes
- Bookings
- Invoices
- Payments
- Contracts
- Pricing rules
- Coupons
- Wallet
- CRM
- Analytics
- Support tickets
- Claims
- Notifications
- Reports
- Settings

### Fleetbase database owns

- Drivers
- Vehicles
- Orders
- Dispatch
- Routes
- Tracking
- GPS
- Waypoints
- Proof of delivery
- Operational status

---

## 7. Order flow

```
Public Website → Quote → Customer Authentication → Payment → Booking
  → Porterchain Order → Fleetbase Order → Dispatch → Driver → Tracking
  → Proof of Delivery → Fleetbase Webhook → Porterchain → Invoice → Notification
```

---

## 8. Merchant flow

```
Business Inquiry → CRM → Lead → Sales → Contract → Merchant Approval
  → Merchant Portal → Bookings → Fleetbase → Invoices → Reports
```

---

## 9. Customer flow

```
Website → Quote → Booking → Payment → Tracking → History → Support
```

---

## 10. Admin panel

> The Admin Portal **never** becomes a dispatch system.

**The Admin Portal manages**

- CRM
- Sales
- Merchants
- Pricing
- Billing
- Contracts
- Invoices
- Payments
- Reports
- Marketing
- Support
- Analytics
- Driver approval
- Merchant approval
- Business settings
- Fleetbase integration

Admin may launch Fleetbase for operational dispatch when required.

---

## 11. Fleetbase console

| Used by         | Not used by |
| --------------- | ----------- |
| Dispatcher      | Customers   |
| Fleet manager   | Merchants   |
| Operations team | Visitors    |
| Route planner   |             |

---

## 12. Upgrades

- Never modify Fleetbase core unless absolutely necessary.
- Always prefer, in order: **extensions → adapters → services → hooks → configuration → plugins**.
- Custom code belongs inside Porterchain.

---

## 13. Whenever writing code

Before implementing any feature, ask:

1. **Does this belong to logistics execution?** → **Fleetbase**
2. **Does this belong to commercial business logic?** → **Porterchain**
3. **If uncertain** → keep business logic inside **Porterchain**.

Only operational execution belongs inside Fleetbase.

---

## 14. Feature classification

Before implementing any feature, classify it into one of three categories.

### Category A — Porterchain business logic

> Implement **only** in Porterchain.

Examples: CRM, pricing, billing, contracts, merchant portal, customer portal,
analytics, notifications, AI, reports.

### Category B — Fleetbase logistics operations

> Use **Fleetbase**.

Examples: driver dispatch, vehicle assignment, GPS tracking, route optimization,
proof of delivery, fleet operations.

### Category C — Shared integration

> Implement in the **Fleetbase Adapter** only.

Examples: order synchronization, driver synchronization, vehicle synchronization,
webhooks, event mapping, status updates.

**Rules**

- Never duplicate business logic between Porterchain and Fleetbase.
- If a feature spans multiple categories, implement each responsibility in its
  proper layer rather than moving everything into one system.

---

## Final rule

- **Porterchain is the Product.**
- **Fleetbase is the Engine.**

Never confuse these responsibilities. Protect this architecture in every future implementation.
