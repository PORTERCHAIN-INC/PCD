# Porterchain Customer Mobile App

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Expo SDK 52 customer retail app. Calls **Porterchain API only** (`/v1/*` on `:8001`) — Fleetbase integration is server-side via adapter.

---

## Run

```bash
pnpm dev:mobile-customer
```

Expo runs on port **8082**. The app expects the API at `EXPO_PUBLIC_API_URL` (`http://localhost:8001` locally).

---

## Architecture

```
mobile-customer (Expo)
    ↓ HTTPS
Porterchain API :8001 /v1/*
    ↓
booking_engine, billing_engine, notification_engine
    ↓
Fleetbase adapter → Fleetbase :8000
```

Shared packages: `@porterchain/mobile-api`, `mobile-security`, `mobile-offline`, `mobile-notifications`, `mobile-performance`, `mobile-maps`, `mobile-ui`.

---

## Tabs

| Tab               | Features                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| **Home**          | Dashboard metrics, active shipment, quick quote                          |
| **Bookings**      | Quote, booking, drafts, Stripe checkout, confirmation                    |
| **Tracking**      | Order lookup, live map, history                                          |
| **Notifications** | FCM + inbox, preferences, deep links                                     |
| **Profile**       | Invoices, receipts, support, claims, offline sync, settings, performance |

---

## Features

| Flow             | API                                               |
| ---------------- | ------------------------------------------------- |
| Quote / booking  | `POST /v1/quotes`, `POST /v1/bookings`            |
| Booking drafts   | `/v1/booking-drafts/*`                            |
| Stripe checkout  | Hosted checkout URL + confirmation polling        |
| Live tracking    | `GET /v1/orders/{tracking}/tracking`              |
| Dashboard        | `GET /v1/customers/me/dashboard`                  |
| Support / claims | `POST /v1/customers/me/support`                   |
| Push register    | `POST /v1/notifications/devices/register`         |
| Payment retry    | `POST /v1/payments/retry` (API wired; UI partial) |

---

## Auth

Production auth uses Clerk:

1. `ClerkSignInPanel` signs in with Clerk (email/password or Google OAuth).
2. App uses Clerk bearer with `/v1/auth/me` to resolve the customer principal.
3. Tokens stored securely via auth store.

Local development shows `DevEmailSignInPanel` only when `EXPO_PUBLIC_APP_ENV=local` and API has `CLERK_DEV_BYPASS=true`.

---

## Environment

```bash
EXPO_PUBLIC_API_URL=http://localhost:8001
EXPO_PUBLIC_APP_KIND=customer
EXPO_PUBLIC_APP_ENV=local
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=
GOOGLE_SERVICES_JSON=
GOOGLE_SERVICES_INFO_PLIST=
EAS_PROJECT_ID=
```

Production values via EAS secrets. See [MOBILE_PRODUCTION_READINESS.md](../../MOBILE_PRODUCTION_READINESS.md) for store blockers (icons, Firebase creds).

---

## Related Documents

| Document                                                                     | Purpose             |
| ---------------------------------------------------------------------------- | ------------------- |
| [../../MOBILE_ARCHITECTURE_REPORT.md](../../MOBILE_ARCHITECTURE_REPORT.md)   | Mobile architecture |
| [../../MOBILE_PRODUCTION_READINESS.md](../../MOBILE_PRODUCTION_READINESS.md) | Release readiness   |
| [../customer/README.md](../customer/README.md)                               | Web customer portal |

---

## Governance

| Document                                                       | Role              |
| -------------------------------------------------------------- | ----------------- |
| [../../masterrule.md](../../masterrule.md)                     | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
