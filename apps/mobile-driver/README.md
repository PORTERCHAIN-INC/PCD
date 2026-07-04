# Porterchain Driver Mobile App

Expo SDK 52 driver execution app. Calls **Porterchain API only** (`/driver-api/v1/*`) — Fleetbase integration is server-side via adapter (`masterrule.md`).

## Run

```bash
pnpm dev:mobile-driver
```

## Tabs

| Tab | Features |
|-----|----------|
| **Home** | Dashboard, today's stops/earnings, quick actions |
| **Jobs** | Current/upcoming/completed, job detail, assignment queue |
| **Navigation** | Live map, GPS pings, Fleetbase routing via API |
| **Earnings** | Today/week/month, wallet |
| **Shift** | Online/offline, start/end shift, breaks |
| **More** | Profile, Notifications, Support, SOS, Settings |

## Execution flows

- **Accept / Reject** — `POST /orders/{id}/accept|reject` (offline queue when disconnected)
- **Pickup / Transit / Delivered** — stop arrive/deliver + state timeline from API
- **POD** — OTP, signature, photo, complete (`/routes/.../pod-*`)
- **Incident** — `POST /incidents`
- **SOS** — `POST /emergency` with GPS
- **Realtime GPS** — `expo-location` → `POST /location`
- **Offline** — MMKV queue → `/offline/queue` + `/offline/sync`
- **Push** — Firebase → `/push/register`

## Auth

Dev sign-in uses Clerk bearer `dev` token. Set `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` for production.

## Env

```
EXPO_PUBLIC_API_URL=http://localhost:8001
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=
```
