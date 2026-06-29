# Porterchain — Integrations

**Document version:** 1.0  
**Date:** June 29, 2026  

---

## Integration map

| Integration | Status in PCD repo | Used by | Purpose |
|-------------|-------------------|---------|---------|
| **Fleetbase** | Documented | API, Admin | Dispatch, fleet ops, routing |
| **Google Maps** | **Implemented** (website) | Website, Driver app, API | Autocomplete, maps, geocoding |
| **OSRM** | Documented | Fleetbase/API | Route polyline encoding (fallback) |
| **Valhalla** | Documented | Fleetbase | Primary routing engine |
| **Stripe** | Documented | API, Merchant portal, Website | Payments, invoicing |
| **Clerk** | Documented | Merchant portal, API | Identity, JWT |
| **Firebase** | Documented (FCM only) | API | Driver push notifications |
| **Supabase** | Documented | Website | Booking OTP |
| **Twilio** | Documented | API | SMS OTP |
| **Zoho SMTP** | Documented | API | Transactional email |
| **Zoho SalesIQ** | Documented | Website | Live chat |
| **Mapbox** | Driver app only | Driver app | Polyline decode (`@mapbox/polyline`) |

---

## Fleetbase

### What it does

Open-source logistics and dispatch platform. Porterchain uses Fleetbase as the **operational backbone** for order management, driver assignment, route optimization, and control-tower UI.

### Configuration

| Variable | Value |
|----------|-------|
| `FLEETBASE_API_URL` | API endpoint |
| `REGISTRY_HOST` | `https://registry.fleetbase.io` |
| `CONSOLE_HOST` | Admin UI (`:4200`) |
| `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` | Default org |
| `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE` | Enable dispatch sync |
| `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE` | Enable driver job sync |
| `PORTERCHAIN_FLEETBASE_ASSIGNMENT_REQUIRED` | Prod assignment gate |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Bridge authentication |

### Data flow

```
Porterchain API → Fleetbase API → MySQL (orders, routes, drivers)
Fleetbase Console → Ops dispatch → Driver assignment
Driver app ← Porterchain API ← Fleetbase route data
```

### Verification checklist

- [ ] Fleetbase API responds at `FLEETBASE_API_URL/health` (or equivalent)
- [ ] Console loads at `CONSOLE_HOST`
- [ ] Default company UUID exists in Fleetbase
- [ ] Dispatch bridge creates orders from Porterchain bookings
- [ ] Driver job bridge surfaces routes to `/driver-api/v1/routes/assigned`

---

## Google Maps

### Implementation status

| Surface | Package | Status |
|---------|---------|--------|
| Website | `@vis.gl/react-google-maps` 1.8.3 | **Live** — Places API (New) |
| Driver app | `react-native-maps` + `PROVIDER_GOOGLE` | External repo |
| API | Server key for geocoding / distance | Documented |

### Website files

| File | Role |
|------|------|
| `website/src/lib/maps.ts` | API key, GTA bounds, address normalization |
| `website/src/components/maps/GoogleMapsProvider.tsx` | Maps JS API loader |
| `website/src/components/maps/AddressAutocompleteInput.tsx` | `PlaceAutocompleteElement` |
| `website/env.example` | `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` |

### API keys (three keys required)

| Key | Restriction | Used for |
|-----|-------------|----------|
| Browser | HTTP referrer | Website autocomplete |
| Server (IP) | Server IP | Geocoding, Distance Matrix |
| Mobile (iOS/Android) | Bundle ID `com.porterchain.PCD` | Driver map tiles |

### Required GCP APIs

- Maps JavaScript API
- **Places API (New)** — migrated from legacy Places API
- Geocoding API
- Distance Matrix API (if server-side ETA)
- Maps SDK for iOS
- Maps SDK for Android

### Verification checklist

- [ ] Browser key works on `localhost:3000` and production domain
- [ ] Places autocomplete returns GTA-bounded results
- [ ] No legacy Places API console errors
- [ ] Server key restricted to API server IP
- [ ] Driver app maps render on EAS build (not Expo Go)

---

## OSRM

### Role

Fallback routing engine and polyline encoding format. Driver app receives `route_polyline` (OSRM-encoded) from API — **does not call OSRM directly**.

### Configuration

```
OSRM_HOST=https://router.project-osrm.org
```

### Flow

```
Ops optimizes route (Fleetbase/Valhalla)
  → API encodes polyline (OSRM format)
  → Driver app: GET /driver-api/v1/routes/{id}/stops
  → route_polyline field
  → @mapbox/polyline decode
  → react-native-maps Polyline
```

### Verification checklist

- [ ] `route_polyline` present on assigned routes
- [ ] Polyline decodes without error in driver app
- [ ] Fallback straight-line drawing works when polyline missing

---

## Valhalla

### Role

**Primary** self-hosted routing engine (`ROUTING_ENGINE=valhalla`).

### Configuration

| Variable | Docker | Host |
|----------|--------|------|
| `VALHALLA_BASE_URI` | `http://valhalla:8002` | — |
| `VALHALLA_BASE_URL` | — | `http://localhost:8002` |

### Deployment

- Docker image: `ghcr.io/gis-ops/docker-valhalla/valhalla`
- Requires OSM tile build for Ontario/GTA region
- Port **8002** reserved

### Verification checklist

- [ ] Valhalla `/status` returns healthy
- [ ] Route request returns valid geometry for GTA coordinates
- [ ] Fleetbase uses Valhalla when `ROUTING_ENGINE=valhalla`

---

## Stripe

### Use cases

| Flow | URL pattern |
|------|-------------|
| Merchant invoice payment | Redirect to Stripe Checkout → `localhost:3001/invoices?paid=1` |
| Retail post-delivery pay | `/track/{tracking_number}` → Stripe |

### Configuration (server-only)

| Variable | Purpose |
|----------|---------|
| `STRIPE_KEY` | Publishable (`pk_*`) |
| `STRIPE_SECRET` | Secret (`sk_*`) |
| `STRIPE_WEBHOOK_SECRET` | Webhook verification |
| `PORTERCHAIN_STRIPE_SUCCESS_URL` | Merchant success |
| `PORTERCHAIN_STRIPE_CANCEL_URL` | Merchant cancel |
| `PORTERCHAIN_RETAIL_PAY_URL_BASE` | Retail pay base |

### Webhook events (expected)

- `checkout.session.completed`
- `invoice.paid`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`

### Verification checklist

- [ ] Test mode checkout completes end-to-end
- [ ] Webhook signature validation passes
- [ ] Merchant invoice status updates on `checkout.session.completed`
- [ ] Retail tracking page shows paid state

---

## Clerk

### Use cases

- Merchant portal authentication
- Driver web invite flow
- JWT verification on Porterchain API

### SDK (target — not in PCD repo)

- `@clerk/nextjs` for merchant portal
- JWKS verification in FastAPI middleware

### Verification checklist

- [ ] Sign-up / sign-in works on merchant portal
- [ ] JWT validates against `CLERK_JWKS_URL`
- [ ] Expired tokens return 401
- [ ] Org-scoped merchant data isolation

---

## Firebase

### Scope

**FCM push notifications only** — NOT used for authentication.

| Variable | Purpose |
|----------|---------|
| `FIREBASE_PROJECT_ID` | GCP project |
| `FIREBASE_CREDENTIALS_PATH` | Service account JSON |
| `PORTERCHAIN_DRIVER_PUSH_ENABLED` | Master toggle |
| `PORTERCHAIN_DRIVER_PUSH_SEND` | Send toggle |

### Important distinction

`CONNECTIONS.md` confirms the **driver mobile app does not use Firebase**. Push is API-side only. Driver app has no FCM token registration today.

### Verification checklist

- [ ] Service account JSON accessible at credentials path
- [ ] Test push reaches device (when driver app adds `expo-notifications`)
- [ ] Push disabled in dev when `PORTERCHAIN_DRIVER_PUSH_SEND=false`

---

## SMTP (Zoho Mail)

### Channels

| Channel | Config |
|---------|--------|
| Platform mail | `MAIL_*` vars |
| Booking OTP email | `BOOKING_OTP_SMTP_*` vars |

### Provider

- Host: `smtp.zohocloud.ca`
- Port: `465` SSL
- From: `ops@porterchain.com`

### Verification checklist

- [ ] OTP email delivers to business booking address
- [ ] Invoice emails deliver from `ops@porterchain.com`
- [ ] SPF/DKIM configured for `porterchain.com`

---

## Twilio (SMS)

### Use case

Personal booking OTP via Supabase Auth SMS channel.

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | Account |
| `TWILIO_AUTH_TOKEN` | Secret |
| `TWILIO_FROM_NUMBER` | E.164 sender |

### Verification checklist

- [ ] SMS OTP delivers to Canadian mobile numbers
- [ ] Rate limiting prevents SMS abuse
- [ ] Twilio webhook for delivery status (optional)

---

## Push notifications

| Layer | Status |
|-------|--------|
| API (FCM) | Configured in docs |
| Driver app | **Not implemented** |
| Merchant portal | Not required |
| Website | Not required |

**Future:** `expo-notifications` + APNs/FCM in driver app.

---

## Webhooks

### Inbound (Porterchain receives)

| Source | Endpoint | Secret |
|--------|----------|--------|
| Stripe | `/webhooks/stripe` | `STRIPE_WEBHOOK_SECRET` |
| Clerk | `/webhooks/clerk` | Clerk signing secret (add) |
| Fleetbase | `/webhooks/fleetbase` | Shared secret (add) |

### Outbound (Porterchain sends to merchants)

Documented on `/api-integrations` page:
- Shipment created
- Dispatch assigned
- Delivery completed
- POD available

**Status:** Not implemented in PCD repo.

### Verification checklist

- [ ] Stripe webhook idempotency (store event IDs)
- [ ] Retry with exponential backoff for outbound webhooks
- [ ] HMAC signature on outbound payloads

---

## Zoho SalesIQ (live chat)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE` | Widget hash |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED` | Toggle |

**Status:** Documented in legal doc; component `ZohoSalesIQ.tsx` not in PCD repo.

---

## Integration health dashboard (recommended)

Monitor these endpoints in staging/production:

| Service | Health check |
|---------|--------------|
| Porterchain API | `GET /health` |
| Fleetbase API | Fleetbase health endpoint |
| Valhalla | `GET /status` |
| Redis | `PING` |
| MySQL | Connection pool check |
| Stripe | Webhook delivery success rate |
| Clerk | JWKS fetch latency |
| Google Maps | Places autocomplete smoke test |

---

*Re-verify each integration when monorepo services are consolidated into PCD.*
