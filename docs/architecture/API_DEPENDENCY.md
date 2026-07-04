# API Dependency

> **Source:** Frontend `lib/api.ts` files, `apps/api/src/porterchain_api/routers/`

## Client → API Matrix

| Client    | Base URL              | Auth                             | Key paths                                                                                                                 |
| --------- | --------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Website   | `:8001/v1`            | Clerk bearer (booking)           | `/quotes`, `/bookings`, `/booking-drafts`, `/orders`, `/customers/me`, `/payments/retry`                                  |
| Customer  | `:8001/v1`            | Clerk bearer                     | `/customers/me/dashboard`, `/customers/me/support`, `/customers/me/rebook/{id}`                                           |
| Merchant  | `:8001/v1/merchant`   | Clerk + org headers              | `/dashboard`, `/bookings`, `/orders`, `/bulk`, `/billing`, `/profile`, `/team`, `/api-keys`                               |
| Admin     | `:8001/v1/admin`      | Clerk bearer                     | `/dashboard`, `/orders`, `/operations`, `/crm`, `/merchants`, `/drivers`, `/finance`, `/pricing`, `/reports`, `/settings` |
| Driver    | `:8001/driver-api/v1` | Porterchain JWT (via Next proxy) | `/auth/login`, `/routes`, `/stops`, `/availability`, `/location`                                                          |
| Stripe    | `:8001/webhooks`      | HMAC signature                   | `/webhooks/stripe`                                                                                                        |
| Fleetbase | `:8001/webhooks`      | HMAC signature                   | `/webhooks/fleetbase`                                                                                                     |

## External API Calls (Server-Side Only)

| System         | Caller                                 | Path                                 |
| -------------- | -------------------------------------- | ------------------------------------ |
| Fleetbase      | `fleetbase-adapter`                    | `settings.fleetbase_api_url` (:8000) |
| Stripe         | `services/stripe_service.py`           | Stripe REST API                      |
| OSRM           | `porterchain_services/maps/service.py` | `settings.osrm_url`                  |
| Valhalla       | `porterchain_services/maps/service.py` | `settings.valhalla_url` (:8002)      |
| Clerk          | `auth/clerk.py`                        | JWKS endpoint                        |
| Google Geocode | `website/src/lib/quote/geocode.ts`     | Server-only quote preview            |
| Google Maps    | `@porterchain/maps`                    | Browser JS API (viz/autocomplete)    |

## No Direct Fleetbase from UI

Admin opens Fleetbase console via `POST /v1/auth/sso/fleetbase` → SSO URL only.

## Diagram

```mermaid
flowchart LR
  subgraph Clients
    W[website :3000]
    M[merchant :3001]
    A[admin :3002]
    D[driver :3003]
    C[customer :3004]
    MOB[mobile-driver]
  end

  subgraph API["Porterchain API :8001"]
    PUB["/v1/quotes, /orders, /booking-drafts"]
    CUST_API["/v1/customers"]
    MERCH_API["/v1/merchant"]
    ADMIN_API["/v1/admin/*"]
    DRV_API["/driver-api/v1"]
    WH["/webhooks/stripe, /webhooks/fleetbase"]
    WS["WS /v1/admin/operations/live-map/ws"]
  end

  subgraph External
    STRIPE[Stripe API]
    FB_WH[Fleetbase Webhooks]
    CLERK[Clerk JWKS]
    GMAPS[Google Maps JS API]
  end

  W --> PUB & CUST_API
  C --> CUST_API
  M --> MERCH_API
  A --> ADMIN_API & WS
  D -->|"Next proxy /api/driver"| DRV_API
  MOB --> DRV_API
  W & M & A --> GMAPS
  W & M & A & C & D --> CLERK
  STRIPE --> WH
  FB_WH --> WH
  API --> STRIPE
  API -->|"fleetbase-adapter"| FB_API[Fleetbase :8000]
```

## PlantUML

See [plantuml/api_dependency.puml](./plantuml/api_dependency.puml)
