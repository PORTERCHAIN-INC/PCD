# Porterchain — System Architecture

**Document version:** 1.0  
**Date:** June 29, 2026  
**Status:** Foundation audit — architecture specification  
**Audience:** Engineering, DevOps, Security, Product

---

## Executive summary

Porterchain is a commercial logistics platform comprising a public website, merchant portal, admin/control-tower console, driver mobile app, Porterchain API, and Fleetbase dispatch backbone. This document defines the **target system architecture** based on platform documentation and the code present in the PCD repository.

### Repository scope (important)

| Layer | In PCD repo today | Documented / external |
|-------|-------------------|------------------------|
| Public website (`website/`) | **Yes** — Next.js 16 marketing + booking UI | — |
| Merchant portal | No | `portal.porterchain.com`, port 3001 |
| Admin / control tower | No | Fleetbase console, port 4200 |
| Driver app | No | `apps/mobile-driver` (Expo 52) |
| Porterchain API | No | `apps/api` (FastAPI), port 8000 |
| Fleetbase API | No | Laravel stack, port 8000 (shared or aliased) |
| Docker / infra | No | Referenced in `details.md` |

The PCD workspace is the **website slice** of a larger platform. Architecture below describes the **full Porterchain system** with clear boundaries for consolidation into a monorepo.

---

## Overall architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT APPLICATIONS                             │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│   Website    │   Merchant   │    Admin     │   Driver     │   Integrations  │
│  (Next.js)   │   Portal     │  (Fleetbase  │  (Expo RN)   │  (ERP / Webhooks)│
│   :3000      │   :3001      │  Console)    │   mobile     │                 │
│              │              │   :4200      │              │                 │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴────────┬────────┘
       │              │              │              │                │
       └──────────────┴──────────────┴──────────────┴────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   Edge / Reverse   │
                          │   Proxy (Nginx or  │
                          │   Traefik)         │
                          └─────────┬─────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
┌──────▼──────┐            ┌────────▼────────┐          ┌────────▼────────┐
│ Porterchain │            │   Fleetbase     │          │  Routing Engine │
│ API         │◄──bridge──►│   API (Laravel) │          │  Valhalla :8002 │
│ (FastAPI)   │            │   MySQL + Redis │          │  OSRM (fallback)│
│   :8000     │            │   :8000         │          └─────────────────┘
└──────┬──────┘            └────────┬────────┘
       │                            │
       └────────────┬───────────────┘
                    │
         ┌──────────▼──────────┐
         │  MySQL (fleetbase)  │
         │  Redis (cache/queue)│
         └─────────────────────┘
```

### Application boundaries

| Application | Responsibility | Must NOT do |
|-------------|----------------|-------------|
| **Website** | Marketing, booking UI, blog, contact, retail tracking entry | Dispatch, billing settlement, driver assignment |
| **Merchant portal** | Onboarding, invoices, shipment management, Stripe checkout | Direct Fleetbase schema writes |
| **Admin / Fleetbase console** | Dispatch, route optimization, driver assignment, control tower | Merchant contract logic |
| **Driver app** | Route execution, POD capture, location pings | Pricing, merchant billing |
| **Porterchain API** | Auth, bookings, merchant lifecycle, driver execution API, webhooks, Stripe | Replace Fleetbase dispatch engine |
| **Fleetbase** | Fleet ops, orders, drivers (Fleetbase model), routing orchestration | Merchant legal agreements |

---

## Data flow

### Retail booking (website → delivery)

```
User (Website)
  → Google Places autocomplete (client, browser key)
  → Booking widget state (client-only today; target: Porterchain API)
  → Supabase OTP (business: email / personal: SMS via Twilio)
  → Porterchain API: create shipment / quote
  → Fleetbase bridge: create order + assign driver (if configured)
  → Stripe (retail pay-after-delivery on /track/{id})
  → Notifications (email via Zoho SMTP, push via FCM when enabled)
```

### Merchant B2B flow

```
Merchant sign-up (Clerk JWT)
  → Merchant portal onboarding wizard
  → Porterchain API: company profile, documents, contract acceptance
  → Admin review → status ACTIVE
  → Merchant creates shipments via portal or API integration
  → Billing: Net 30/45 or Stripe checkout
  → Invoice PDF + overdue reminders
```

### Driver execution flow

```
Dispatcher assigns route (Admin / Fleetbase)
  → Porterchain API exposes route to driver
  → Driver app: GET /driver-api/v1/routes/assigned
  → Start route → arrive → deliver → POD upload (photo, signature)
  → Location pings: POST /driver/location
  → Status sync back to Fleetbase + merchant tracking
```

### Dispatch flow

```
Ops creates / optimizes route (Fleetbase console)
  → ROUTING_ENGINE=valhalla (self-hosted) or OSRM fallback
  → route_polyline encoded (OSRM polyline format)
  → Driver app decodes polyline for map display
  → PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE=true enables Porterchain ↔ Fleetbase sync
  → PORTERCHAIN_FLEETBASE_ASSIGNMENT_REQUIRED=true enforces assignment in production
```

### Billing flow

| Segment | Trigger | Payment rail | Redirect URLs |
|---------|---------|--------------|---------------|
| Merchant invoice | Monthly / on-demand | Stripe Checkout | `localhost:3001/invoices?paid=1` |
| Retail tracking | Post-delivery | Stripe on `/track/{id}` | `localhost:3000/track/{id}?paid=1` |

Webhook: `STRIPE_WEBHOOK_SECRET` validates events server-side (API only).

### Notification flow

| Channel | Provider | Use case |
|---------|----------|----------|
| Email (transactional) | Zoho SMTP (`smtp.zohocloud.ca:465`) | Ops, booking OTP, invoices |
| Email (booking OTP) | Dedicated SMTP vars `BOOKING_OTP_SMTP_*` | Business booking verification |
| SMS | Twilio | Personal booking OTP |
| Push (driver) | Firebase FCM via Fleetbase path | Driver job alerts (API-side; not in driver app today) |
| Live chat | Zoho SalesIQ | Website support widget |

---

## Authentication flow

Porterchain uses **multiple identity providers by surface** — not a single SSO product end-to-end.

```
┌─────────────┐     Clerk JWT      ┌──────────────────┐
│ Merchant /  │ ─────────────────► │ Porterchain API  │
│ Driver web  │     JWKS verify    │ (Clerk middleware) │
└─────────────┘                    └──────────────────┘

┌─────────────┐   Supabase OTP     ┌──────────────────┐
│ Website     │ ─────────────────► │ Porterchain API  │
│ booking     │   email / SMS      │ + website OTP key│
└─────────────┘                    └──────────────────┘

┌─────────────┐   Porterchain JWT  ┌──────────────────┐
│ Driver app  │ ─────────────────► │ /driver-api/v1   │
│ (Expo)      │   Bearer + headers │ X-Driver-Id, etc.│
└─────────────┘                    └──────────────────┘

┌─────────────┐   Sanctum / API key┌──────────────────┐
│ Dispatcher  │ ─────────────────► │ Fleetbase API    │
│ control tower│ PORTERCHAIN_      │                  │
└─────────────┘   DISPATCHER_API_KEY└──────────────────┘
```

See [AUTHENTICATION.md](./AUTHENTICATION.md) for roles and permissions.

---

## API communication

### Porterchain API (FastAPI) — documented paths

| Domain | Base path | Auth |
|--------|-----------|------|
| Auth | `/auth/*` | Public (login) / refresh token |
| Driver execution | `/driver-api/v1/*` | Bearer JWT + `X-Driver-Id` |
| Legacy driver | `/driver/*` | Bearer JWT |
| Routes / earnings | `/routes/{id}/*` | Bearer JWT |

Production: `https://api.porterchain.com`  
Local: `http://localhost:8000`

### Fleetbase API

- URL aliases `FLEETBASE_API_URL` and `PORTERCHAIN_API_URL` (both `:8000` locally — **port conflict risk**; see [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md))
- Registry: `https://registry.fleetbase.io`
- Bridge flags: `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE`, `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE`

### Website → API (target state)

Today the website booking widget is **client-side only** (no API submit). Target wiring:

- `NEXT_PUBLIC_PORTERCHAIN_API_URL` for browser-safe endpoints
- Server-side secrets (`PORTERCHAIN_WEBSITE_OTP_KEY`, Stripe) stay on API

---

## Fleetbase integration

Fleetbase is the **dispatch and fleet operations backbone**.

| Integration point | Configuration |
|-------------------|---------------|
| Default company | `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` |
| Assignment enforcement | `PORTERCHAIN_FLEETBASE_ASSIGNMENT_REQUIRED` |
| Dispatch bridge | `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE` |
| Driver job bridge | `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE` |
| Dispatcher auth | `PORTERCHAIN_DISPATCHER_API_KEY` |
| Console UI | `CONSOLE_HOST` (port 4200) |
| Database | MySQL database `fleetbase` |
| Push credentials | `FIREBASE_CREDENTIALS_PATH` under Fleetbase storage |

Porterchain-owned domain logic (merchant contracts, billing terms, retail pay URLs) lives in **Porterchain API / Laravel extensions** (`api/app/Models/Porterchain/*`), not in Fleetbase core tables.

---

## Deployment architecture

### Target production topology

```
                    ┌─────────────────┐
                    │  CDN / Vercel   │  website.porterchain.com
                    │  (Next.js SSR)  │
                    └────────┬────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│ DigitalOcean / K8s / VM    │                                │
│  ┌──────────┐  ┌───────────▼──────────┐  ┌───────────────┐ │
│  │ Nginx /  │  │ Porterchain API      │  │ Merchant      │ │
│  │ Traefik  │──│ + Fleetbase stack    │  │ Portal :3001  │ │
│  └──────────┘  │ (Docker Compose)     │  └───────────────┘ │
│                │  - api :8000         │                    │
│                │  - console :4200     │                    │
│                │  - mysql :3306       │                    │
│                │  - redis :6379       │                    │
│                │  - valhalla :8002    │                    │
│                └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘

Mobile: EAS Build → App Store / Play Store
Driver API: https://api.porterchain.com
```

### Current PCD deployment gap

- No `Dockerfile`, `docker-compose.yml`, or CI/CD in PCD repo
- Website deploys independently (likely Vercel or Node host)
- Platform stack documented in `details.md` assumes Docker Compose with service hostnames (`database`, `cache`, `valhalla`)

---

## Cross-cutting concerns

| Concern | Approach |
|---------|----------|
| i18n | `next-intl` — `en`, `fr` on website |
| Observability | Sentry recommended — not installed |
| Secrets | Never in client bundles; rotate `details.md` if exposed |
| API docs | OpenAPI on Porterchain API — not in PCD repo |

---

## Related documents

| Document | Purpose |
|----------|---------|
| [TECH_STACK.md](./TECH_STACK.md) | Versions and technology choices |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) | Full env var catalog |
| [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) | Port allocation |
| [DOCKER_ARCHITECTURE.md](./DOCKER_ARCHITECTURE.md) | Container design |
| [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md) | Data stores |
| [AUTHENTICATION.md](./AUTHENTICATION.md) | Identity and RBAC |
| [INTEGRATIONS.md](./INTEGRATIONS.md) | Third-party services |
| [SECURITY.md](./SECURITY.md) | Security controls |
| [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md) | Monorepo layout target |
| [DEPENDENCY_REPORT.md](./DEPENDENCY_REPORT.md) | Package audit |

---

## Immediate architectural priorities

1. **Consolidate repositories** — bring `apps/api`, `apps/mobile-driver`, merchant portal, and Fleetbase stack into one monorepo with shared tooling.
2. **Resolve port 8000 conflict** — Porterchain API and Fleetbase API both default to `:8000`; separate ports or reverse-proxy paths in dev.
3. **Wire website booking to API** — booking widget currently has no backend submit path.
4. **Add Docker Compose + CI/CD** — reproducible local and staging environments.
5. **Remove secrets from `details.md`** — use `.env.example` templates only; rotate all exposed credentials.
6. **Unify auth documentation** — Clerk for portal users, Supabase for retail OTP, Porterchain JWT for drivers; document role matrix in one place.

---

*This document describes architecture intent. It does not modify business logic, UI, or booking flow behavior.*
