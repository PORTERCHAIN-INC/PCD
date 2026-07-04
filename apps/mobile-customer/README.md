# Porterchain Customer Mobile App

Expo SDK 52 customer app — bookings, tracking, billing, and support. Calls **Porterchain API only** (`EXPO_PUBLIC_API_URL` → `:8001/v1/*`).

## Run

```bash
pnpm dev:mobile-customer
```

## Tabs

| Tab | Features |
|-----|----------|
| **Home** | Dashboard metrics, active shipment, quick quote |
| **Bookings** | Quote, booking, drafts, Stripe checkout, confirmation |
| **Tracking** | Public lookup, live map, order history |
| **Notifications** | FCM foreground + local inbox (remote inbox when API supports customers) |
| **Profile** | Invoices, receipts, support, claims, settings, sign out |

## Auth

- **Production:** set `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` (Clerk JWT → Bearer on API)
- **Local dev:** sign in uses `dev` token when Clerk is not configured (`CLERK_DEV_BYPASS` on API)

## Features

- Quote & booking flow (`POST /v1/quotes`, `POST /v1/bookings`)
- Booking drafts (`/v1/booking-drafts/*`)
- Stripe checkout via in-app browser + confirmation polling
- Live tracking map (`GET /v1/orders/{tracking}/tracking`)
- Dashboard invoices & receipts (`GET /v1/customers/me/dashboard`)
- Support tickets & claims (`POST /v1/customers/me/support`)
- Dark mode, offline support queue, biometric unlock, Firebase push registration

## Env

See `.env.example`:

```
EXPO_PUBLIC_API_URL=http://localhost:8001
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=
```
