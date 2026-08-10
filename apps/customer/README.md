# Customer Portal

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Retail customer web dashboard — tracking, booking, invoices, and support.

| Item        | Value                                             |
| ----------- | ------------------------------------------------- |
| **Port**    | 3004 (`pnpm dev:customer`)                        |
| **Package** | `@porterchain/customer`                           |
| **Auth**    | Clerk                                             |
| **API**     | Porterchain API `/v1/customers/*`, `/v1/orders/*` |

> The marketing website ([`website/`](../../website/)) also exposes booking flows at `/book`. This app is the **authenticated customer portal** per masterrule §4.

---

## Setup

```bash
pnpm install
cp env/customer-portal.env.example apps/customer/.env.local
pnpm dev:customer
```

Open [http://localhost:3004](http://localhost:3004).

---

## Routes

| Route                     | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| `/`                       | Landing / redirect                       |
| `/sign-in`                | Clerk sign-in                            |
| `/dashboard`              | Active shipments, invoices, support      |
| `/book`                   | New booking flow                         |
| `/book/success`           | Stripe return + `sync-checkout` polling  |
| `/track/[trackingNumber]` | Public-style tracking by tracking number |
| `/onboarding`             | Customer onboarding                      |

---

## Architecture

```
Customer portal (:3004)
    ↓ Clerk Bearer token
Porterchain API (:8001) /v1/*
    ↓
booking_engine, billing_engine
```

No direct Fleetbase, Stripe SDK, or merchant/admin API calls from this app.

---

## Environment

| Variable                            | Purpose                            |
| ----------------------------------- | ---------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk auth                         |
| `CLERK_SECRET_KEY`                  | Server-side Clerk                  |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | API base (`http://localhost:8001`) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`   | Tracking map embeds                |

See [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md) · [PORT_CONFIGURATION.md](../../PORT_CONFIGURATION.md).

For Stripe Checkout from this portal, set `RETAIL_CHECKOUT_SUCCESS_URL=http://localhost:3004/book/success` in `apps/api/.env` (API creates the Stripe session redirect).

---

## Related Documents

| Document                                                                           | Purpose              |
| ---------------------------------------------------------------------------------- | -------------------- |
| [../../USER_JOURNEYS.md](../../USER_JOURNEYS.md)                                   | Customer journeys    |
| [../../docs/architecture/BOOKING_FLOW.md](../../docs/architecture/BOOKING_FLOW.md) | Booking architecture |

---
