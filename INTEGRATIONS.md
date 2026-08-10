# Porterchain — Integrations

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-08

**Registry:** [integrations.yaml](./integrations.yaml) — CI guard `pnpm validate:integrations-matrix`

---

## Integration map

| Integration           | Status            | Used by                  | Purpose                                         |
| --------------------- | ----------------- | ------------------------ | ----------------------------------------------- |
| **Porterchain API**   | ✅ Live (`:8001`) | All apps                 | Orchestration, RBAC, events                     |
| **Fleetbase**         | ✅ Adapter        | API, admin SSO           | Dispatch, GPS, POD execution                    |
| **Google Maps**       | ✅ Implemented    | Website, portals, mobile | Autocomplete, map viz                           |
| **Valhalla**          | ✅ Docker profile | API pricing              | Primary routing (`:8002`)                       |
| **OSRM**              | ✅ Fallback       | API                      | Route distance fallback                         |
| **Stripe**            | ✅ Live           | API, website, merchant   | Payments, checkout                              |
| **Clerk**             | ✅ Live           | All portals + mobile     | Sole user identity provider                     |
| **Firebase FCM**      | ⚠️ Partial        | API + mobile-driver      | Push notifications (prod creds needed)          |
| **SMTP**              | ✅ Live           | API/worker               | Transactional email                             |
| **Merchant webhooks** | ✅ Implemented    | API                      | Outbound HMAC delivery                          |
| **Merchant API keys** | ✅ Implemented    | `/v1/merchant-api`       | B2B programmatic access                         |
| **OAuth third-party** | ✅ Implemented    | `/v1/oauth`              | Partner authorization_code + client_credentials |
| **PostgreSQL**        | ✅ Live           | API/worker               | Primary datastore (v18)                         |
| **Redis**             | ✅ Live           | API/worker               | Cache, OAuth tokens, rate limits                |
| **Mailpit**           | ✅ Dev            | Docker compose           | Local transactional email                       |
| **Zoho SalesIQ**      | ✅ Optional       | Website                  | Live chat widget                                |

**Removed (do not use):** Supabase OTP, Twilio SMS OTP, `BOOKING_OTP_*` — see [AUTHENTICATION_ARCHITECTURE.md](AUTHENTICATION_ARCHITECTURE.md).

---

## Porterchain API

| App             | Port | API base                                       |
| --------------- | ---- | ---------------------------------------------- |
| Website         | 3000 | `NEXT_PUBLIC_PORTERCHAIN_API_URL` → `:8001/v1` |
| Merchant portal | 3001 | `:8001/v1/merchant`                            |
| Admin           | 3002 | `:8001/v1/admin`                               |
| Driver portal   | 3003 | BFF → `:8001/driver-api/v1`                    |
| Customer portal | 3004 | `:8001/v1/customers`                           |
| Mobile driver   | Expo | `EXPO_PUBLIC_API_URL` → `:8001`                |
| Mobile customer | Expo | `:8001/v1/customers`                           |

Database: **PostgreSQL 18** (Porterchain). Fleetbase uses separate MySQL.

---

## Fleetbase

Operational backbone for dispatch, driver assignment, and execution. Reached **only** via `fleetbase_engine` adapter — never from frontends.

| Variable                         | Purpose                    |
| -------------------------------- | -------------------------- |
| `FLEETBASE_API_URL`              | API (`:8000`)              |
| `FLEETBASE_CONSOLE_URL`          | Console (`:4200`)          |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Dispatch bridge auth       |
| `PORTERCHAIN_FLEETBASE_*`        | Sync toggles, company UUID |

**Flow:** Porterchain emits `order.dispatch_ready` → event handler → `FleetbaseAdapter` → Fleetbase API.

**SSO:** Admin opens console via `POST /v1/auth/sso/fleetbase` — see [SSO.md](./SSO.md).

---

## Google Maps

| Surface       | Package                     | Role                         |
| ------------- | --------------------------- | ---------------------------- |
| Website       | `@vis.gl/react-google-maps` | Places autocomplete, map viz |
| Portals       | `@porterchain/maps`         | Shared map components        |
| Mobile driver | `react-native-maps`         | Route map tiles              |
| API           | Server key                  | Geocoding (server-side only) |

**Rule:** Google Maps is **UI + geocoding only** — pricing uses Valhalla/OSRM server-side.

Env: `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_SERVER_API_KEY`. See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md).

---

## Valhalla & OSRM

| Engine   | Port         | Role                                        |
| -------- | ------------ | ------------------------------------------- |
| Valhalla | 8002         | Primary routing (`ROUTING_ENGINE=valhalla`) |
| OSRM     | configurable | Fallback polyline / distance                |

Used by `pricing_engine` via `resolve_route_distance()` — not called from browsers for billing.

---

## Stripe

| Flow                 | Endpoint / webhook                        |
| -------------------- | ----------------------------------------- |
| Retail checkout      | Stripe Checkout → `POST /webhooks/stripe` |
| Merchant invoice pay | Redirect checkout → webhook               |
| Refunds              | Stripe API from billing/claims            |

Server-only secrets: `STRIPE_SECRET`, `STRIPE_WEBHOOK_SECRET`.

---

## Clerk

**Sole authentication provider** for Porterchain users. See [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md).

| Surface                          | SDK                                                                        |
| -------------------------------- | -------------------------------------------------------------------------- |
| Next.js retail portals + website | `@clerk/nextjs` (Platform / Driver)                                        |
| Admin portal                     | PorterChain staff IdP (no Clerk)                                           |
| Mobile apps                      | Blank Expo shells — Clerk deferred (`@clerk/clerk-expo` not installed yet) |
| API                              | JWKS verification (`auth/clerk.py`)                                        |

Local/dev/prod: **`CLERK_MODE=platform_driver`** — PorterChain Platform triad (customer, merchant, website) + Porterchain Driver triad (driver portal / mobile). Admin uses PorterChain staff IdP (no Clerk). `CLERK_MODE=unified` and `enterprise` are retired. See [docs/SECRETS_MAP.md](./docs/SECRETS_MAP.md) and [SSO.md](SSO.md).

---

## Firebase / FCM

| Layer         | Status                                                                   |
| ------------- | ------------------------------------------------------------------------ |
| API           | FCM send path in notification engine                                     |
| mobile-driver | `@react-native-firebase/messaging` — token register via `/push/register` |
| Production    | Requires Firebase service account on API                                 |

SMS notifications: **log-only** until a transactional SMS provider is selected.

---

## SMTP (transactional email)

**SSOT:** [docs/notifications/ZOHO_MAIL.md](docs/notifications/ZOHO_MAIL.md)

| Environment | Transport                               |
| ----------- | --------------------------------------- |
| Local       | Mailpit `localhost:1025` (UI `:8025`)   |
| Production  | Zoho Canada `smtp.zohocloud.ca:465` SSL |

| Variable                    | Purpose                     |
| --------------------------- | --------------------------- |
| `MAIL_*` / `SMTP_*`         | Platform transactional mail |
| `NEXT_PUBLIC_CONTACT_EMAIL` | Public contact (not auth)   |

Aliases `@porterchain.com`: `peter`, `ravi`, `billing`, `no-reply`, `ops`, `sales`, `support`.

Used for invoices, ops alerts, driver invites — **not** login OTP.

---

## Merchant integrations (implemented)

### API keys

`POST /v1/merchant-api/bookings`, `/orders`, `/track/{tracking_number}` — scoped via API key (`shipments:read`, `shipments:write`, etc.).

Implementation: `auth/merchant_api.py`, `routers/merchant_api.py`.

### Outbound webhooks

Merchants register webhook URLs; `order.*` events fan out via `WebhookDeliveryService` (HMAC signature, retries, delivery history).

Portal: merchant portal → Integrations. Admin visibility: delivery logs + manual retry.

---

## Inbound webhooks

| Source    | Endpoint                   | Verification            |
| --------- | -------------------------- | ----------------------- |
| Stripe    | `POST /webhooks/stripe`    | `STRIPE_WEBHOOK_SECRET` |
| Fleetbase | `POST /webhooks/fleetbase` | Shared secret           |

---

## Zoho SalesIQ (live chat)

Optional website widget: `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED`, `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE`.

Code: `website/src/components/integrations/ZohoSalesIQ.tsx`.

---

## Integration health checks

| Service         | Check                                        |
| --------------- | -------------------------------------------- |
| Porterchain API | `GET /health`, `GET /health/ready`           |
| PostgreSQL      | DB ping in `/health/ready`                   |
| Redis           | PING in readiness                            |
| Fleetbase       | Adapter health in `/health`                  |
| Valhalla        | `GET /status` (when routing profile enabled) |
| Clerk           | JWKS fetch latency                           |
| Stripe          | Webhook delivery success rate                |

---

## Related documents

| Document                                                                     | Purpose                         |
| ---------------------------------------------------------------------------- | ------------------------------- |
| [INTEGRATIONS.md](INTEGRATIONS.md)                                           | Mobile-driver connection detail |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)                       | Env reference                   |
| [docs/architecture/API_DEPENDENCY.md](./docs/architecture/API_DEPENDENCY.md) | Service dependencies            |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                       | Fleetbase bridge detail         |

---
