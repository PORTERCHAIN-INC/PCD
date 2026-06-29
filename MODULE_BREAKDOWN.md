# Porterchain — Module Breakdown

**Document version:** 1.0  
**Date:** June 29, 2026

---

## Application surfaces

| Application            | Users                    | URL / surface              |
| ---------------------- | ------------------------ | -------------------------- |
| **Website**            | Public, retail customers | `porterchain.com`          |
| **Customer dashboard** | Retail customers         | `/portal/customer`         |
| **Merchant portal**    | Business customers       | `portal.porterchain.com`   |
| **Admin**              | Porterchain staff        | `admin.porterchain.com`    |
| **Driver app**         | Driver partners          | iOS / Android              |
| **Fleetbase console**  | Dispatchers only         | Internal `:4200` / ops VPN |
| **Public API**         | Merchants, website       | `api.porterchain.com`      |

---

## Admin modules

### Dashboard

- KPIs: orders today, on-time %, active drivers, revenue, exceptions open
- Live map summary (Fleetbase embed or API)
- SLA alerts queue

### CRM

- Leads (website, for-business, referrals)
- Visitors (anonymous sessions linked post-auth)
- Opportunities pipeline
- Sales activities & notes

### Quotes

- All `QUOTE` and `QUOTE_EXPIRED` records
- Abandoned checkout funnel
- Quote → booking conversion analytics

### Bookings

- In-flight `BOOKING_PENDING` / `PAYMENT_PENDING`
- Stripe session status
- Manual recovery tools

### Merchants

- Merchant accounts lifecycle (`PENDING` → `ACTIVE`)
- Onboarding progress
- Contract status
- Payment terms assignment

### Drivers

- Driver applications
- Approval workflow
- Document verification
- Suspension / reinstatement
- Performance ratings

### Vehicles

- Vehicle registry (synced with Fleetbase)
- Class, capacity, compliance expiry

### Dispatch

- `DISPATCH_READY` queue
- Manual assign / auto-assign rules
- Reassign on reject
- Bulk dispatch for merchant CSV batches

### Fleet

- Fleet utilization
- Driver availability calendar
- Zone coverage

### Orders

- Master order list (all states)
- Timeline view per order
- Force state transition (super_admin only, audited)

### Tracking

- Live GPS (Fleetbase)
- Historical route replay
- Customer-facing tracking link management

### Pricing

- Tariff tables (vehicle, zone, weight)
- Surcharges (fuel, after-hours)
- Merchant contract rates
- Quote simulator

### Invoices

- Retail receipts
- Merchant invoices
- Credit notes
- PDF generation

### Billing

- Stripe reconciliation
- Net terms aging
- Payout batches (drivers)
- Refund queue

### Claims

- Open claims (`CLAIM_OPEN`)
- Evidence repository
- Insurer status tracking

### Support

- Ticket inbox
- Order-linked context
- Canned responses
- Escalation to support_lead

### Marketing

- Abandoned checkout campaigns
- Email templates
- Segment export (consent-gated)

### Contracts

- Merchant agreement versions
- Acceptance audit trail
- Expiry renewals

### Reports

- Operational, financial, SLA exports
- Scheduled report delivery

### Settings

- Global config, zones, vehicle classes
- Notification templates
- Feature flags

### Developers

- API key management
- Webhook logs
- Sandbox environment

---

## Merchant portal modules

### Dashboard

- Today's shipments, in-transit, exceptions
- Spend MTD, on-time %

### Book Delivery

- Same fields as website widget (no UI redesign — consistent API)
- Saved address picker
- Payment terms applied (no Stripe unless configured)

### CSV Upload

- Template download
- Validation report
- Batch confirm → multiple orders

### API

- Key management (owner/admin)
- Webhook endpoint config
- API docs link

### Orders

- List/filter by status, date, recipient
- Detail + timeline

### Tracking

- Live map per shipment
- Share tracking link

### Recipients

- Contact directory for deliveries

### Saved Addresses

- Pickup/dropoff library

### Invoices

- List, PDF download, pay now (Stripe link)

### Statements

- Monthly consolidated view

### Reports

- Volume, cost, SLA by lane

### Billing

- Payment methods, terms, autopay

### Users

- Invite merchant team (Clerk org)

### Settings

- Company profile, notification prefs, API defaults

### Support

- Open tickets linked to orders

---

## Driver app modules

### Today's Jobs

- Assigned routes/stops list
- Accept / reject

### Navigation

- Map + polyline (Google Maps)
- Turn-by-turn external handoff

### Pickup

- Arrive, confirm pickup, barcode optional

### Delivery

- Arrive, deliver, exceptions

### Proof of Delivery

- Photo, signature canvas, barcode scan

### OTP verification

- Customer OTP when merchant policy requires

### Wallet

- Earnings today / week

### Payouts

- History, pending, bank info

### Vehicle

- Assigned vehicle details

### Documents

- Upload / renew license, insurance

### Ratings

- Performance score (read)

### Support

- Report issue on active job

---

## Website modules (existing + target)

| Module              | Status     | Notes                 |
| ------------------- | ---------- | --------------------- |
| Marketing pages     | **Live**   | No redesign           |
| Booking widget      | **Live**   | Quote API to be wired |
| Blog / corporate    | **Live**   | —                     |
| Customer dashboard  | **Target** | Post-Clerk + Stripe   |
| Track (public link) | **Target** | `/track/{id}`         |

---

## Fleetbase modules (engine only)

| Capability                          | Customer-facing?         |
| ----------------------------------- | ------------------------ |
| Driver management                   | No                       |
| Vehicle management                  | No                       |
| Order/payload creation (via bridge) | No                       |
| Route optimization                  | No                       |
| Dispatch board                      | No (ops only)            |
| GPS tracking                        | Indirect via Porterchain |
| POD storage                         | Synced to Porterchain    |

---

## Module → service ownership

| Module layer       | Owning service                  |
| ------------------ | ------------------------------- |
| Admin UI           | Porterchain (Next.js admin app) |
| Merchant UI        | Porterchain (Next.js portal)    |
| Customer UI        | Porterchain (website /portal)   |
| Driver UI          | Porterchain (Expo app)          |
| Business logic     | Porterchain API                 |
| Dispatch execution | Fleetbase API                   |
| Auth (web)         | Clerk                           |
| Payments           | Stripe via Porterchain API      |

---

## Related documents

- [ROLE_PERMISSIONS.md](./ROLE_PERMISSIONS.md)
- [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)
