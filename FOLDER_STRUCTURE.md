# Porterchain — Folder Structure

**Document version:** 1.0  
**Date:** June 29, 2026  

---

## Current state (PCD repo)

```
PCD/
├── CONNECTIONS.md                    # Driver app integration reference
├── PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md
├── details.md                        # ⚠ Contains secrets — remove from git
├── website/                          # Only application in repo
│   ├── content/blog/{en,fr}/        # Blog markdown posts
│   ├── messages/                     # i18n JSON namespaces
│   ├── public/                       # Static assets
│   ├── src/
│   │   ├── app/[locale]/             # Next.js App Router pages
│   │   ├── components/             # React components
│   │   ├── context/                  # React context (booking)
│   │   ├── data/                     # Static data (vehicles, industries)
│   │   ├── i18n/                     # next-intl routing
│   │   └── lib/                      # Utilities (blog, maps)
│   ├── env.example
│   ├── package.json
│   └── AGENTS.md
└── (architecture docs — this audit)
```

---

## Target monorepo structure

Enterprise layout for consolidated Porterchain development:

```
porterchain/                              # Root monorepo
│
├── .github/
│   └── workflows/
│       ├── ci.yml                        # Lint, typecheck, test, build
│       ├── deploy-website.yml
│       ├── deploy-api.yml
│       └── deploy-mobile.yml
│
├── .nvmrc                                # 20.18.0
├── package.json                          # Root workspace scripts
├── pnpm-workspace.yaml
├── turbo.json
├── .env.example                          # Docker Compose + shared secrets template
│
├── apps/
│   ├── website/                          # Public marketing + booking (port 3000)
│   │   ├── src/
│   │   │   ├── app/[locale]/             # Pages
│   │   │   ├── components/
│   │   │   │   ├── layout/               # SiteNavbar, SiteFooter, SiteShell
│   │   │   │   ├── booking/              # Booking widget, schedule picker
│   │   │   │   ├── maps/                 # Google Maps provider
│   │   │   │   ├── corporate/            # Company, contact, careers
│   │   │   │   ├── business/             # B2B landing sections
│   │   │   │   └── blog/
│   │   │   ├── context/
│   │   │   ├── data/
│   │   │   ├── i18n/
│   │   │   └── lib/
│   │   ├── content/blog/
│   │   ├── messages/
│   │   └── env.example
│   │
│   ├── merchant-portal/                # B2B dashboard (port 3001)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── portal/merchant/      # Dashboard
│   │   │   │   └── portal/merchant/onboarding/
│   │   │   ├── components/
│   │   │   └── lib/
│   │   └── env.example
│   │
│   ├── api/                              # Porterchain FastAPI (port 8001)
│   │   ├── src/
│   │   │   ├── domains/
│   │   │   │   ├── auth/                 # Login, refresh, driver invite
│   │   │   │   ├── bookings/             # Retail + business bookings
│   │   │   │   ├── drivers/              # Driver execution API
│   │   │   │   ├── merchants/            # Merchant lifecycle
│   │   │   │   ├── billing/              # Stripe webhooks
│   │   │   │   └── webhooks/             # Outbound merchant webhooks
│   │   │   ├── middleware/               # Auth, rate limit, CORS
│   │   │   ├── models/                   # SQLAlchemy models
│   │   │   └── main.py
│   │   ├── alembic/                      # PostgreSQL migrations
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── env.example
│   │
│   └── mobile-driver/                    # Expo driver app
│       ├── app/                          # Expo Router screens
│       ├── src/
│       │   ├── config/env.ts
│       │   ├── services/                 # apiClient, driverService
│       │   ├── auth/                     # storage, refresh
│       │   └── lib/routePolyline.ts
│       ├── credentials/                  # gitignored — ASC .p8
│       ├── eas.json
│       └── env.example
│
├── packages/                             # Shared libraries
│   ├── ui/                               # @porterchain/ui — design system
│   │   ├── src/components/
│   │   └── package.json
│   ├── types/                            # @porterchain/types — shared TS types
│   ├── config/                           # @porterchain/config — ESLint, TS, Tailwind
│   │   ├── eslint/
│   │   ├── typescript/
│   │   └── tailwind/
│   └── api-client/                       # Generated OpenAPI client
│
├── services/
│   └── fleetbase/                        # Fleetbase Laravel fork / config
│       ├── api/                          # Laravel API (port 8000)
│       │   ├── app/
│       │   │   ├── Models/Porterchain/   # Porterchain extensions
│       │   │   └── Services/Porterchain/
│       │   └── database/migrations/
│       └── console/                      # Fleetbase Ember console (port 4200)
│
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.prod.yml
│   │   ├── .env.example
│   │   └── nginx/
│   │       └── default.conf
│   ├── terraform/                        # DigitalOcean / cloud IaC
│   └── scripts/
│       ├── deploy-driver-appstore.sh
│       └── seed-dev.sh
│
└── docs/                                 # Architecture documentation
    ├── SYSTEM_ARCHITECTURE.md
    ├── TECH_STACK.md
    ├── ENVIRONMENT_VARIABLES.md
    ├── PORT_CONFIGURATION.md
    ├── DOCKER_ARCHITECTURE.md
    ├── DATABASE_ARCHITECTURE.md
    ├── AUTHENTICATION.md
    ├── INTEGRATIONS.md
    ├── SECURITY.md
    ├── FOLDER_STRUCTURE.md
    ├── DEPENDENCY_REPORT.md
    ├── CONNECTIONS.md
    └── DRIVER-ONBOARDING-ARCHITECTURE.md
```

---

## Directory responsibilities

### `apps/website`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Marketing pages, blog, booking UI | Business logic, DB access, Stripe secrets |
| Google Maps client integration | Direct Fleetbase calls |
| i18n (en/fr) | Merchant portal routes |

### `apps/merchant-portal`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Merchant dashboard, onboarding wizard | Dispatch logic |
| Clerk-authenticated routes | Driver execution |
| Invoice UI (Stripe redirect) | Raw payment processing |

### `apps/api`

| Responsibility | Must NOT contain |
|----------------|------------------|
| All business logic, auth, webhooks | UI components |
| Driver execution endpoints | Fleetbase schema migrations |
| Stripe webhook handler | Frontend assets |

### `apps/mobile-driver`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Route execution, POD capture | Pricing, billing |
| Location tracking | Merchant data |
| Google Maps display | Direct OSRM/Valhalla calls |

### `services/fleetbase`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Dispatch, routing, fleet ops | Merchant contracts |
| Fleetbase core schema | Porterchain retail booking logic |
| Control tower console | Website content |

### `packages/ui`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Shared Button, Container, tokens | Page-specific layouts |
| Design system primitives | API clients |

### `packages/api-client`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Type-safe API calls from OpenAPI spec | Hand-written fetch wrappers |
| Shared request/response types | Business logic |

### `infrastructure/`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Docker, Terraform, deploy scripts | Application source code |
| Nginx/Traefik config | Secrets (use `.env`) |

### `docs/`

| Responsibility | Must NOT contain |
|----------------|------------------|
| Architecture, runbooks, ADRs | Live credentials |

---

## Website component organization (current — in repo)

```
website/src/components/
├── layout/           # SiteNavbar, SiteFooter, SiteShell — shared chrome
├── home/             # HomePageShell, BookingProvider wrapper
├── booking/          # ScheduleDateTimePicker
├── maps/             # GoogleMapsProvider, AddressAutocompleteInput
├── sections/         # Home page sections (Hero, FAQ, etc.)
├── business/         # B2B page sections + StickyCta
├── corporate/        # Company, contact, careers sections + CorporateShell
│   ├── layout/       # CorporateShell (wraps SiteShell)
│   ├── sections/     # Reusable corporate section components
│   ├── illustrations/
│   └── ui/           # LinkButton, corporate-specific UI
├── blog/             # Blog components
├── illustrations/    # Shared SVG illustrations
└── ui/               # Primitive UI (Button, Container, Accordion)
```

### Naming conventions

| Pattern | Example |
|---------|---------|
| Page sections | `*Section.tsx` or descriptive (`Hero.tsx`) |
| Layout shells | `*Shell.tsx` |
| Data files | `data/*.ts` — static, no API calls |
| Lib utilities | `lib/*.ts` — pure functions |
| i18n messages | `messages/{namespace}-{locale}.json` |

---

## File placement rules

1. **Colocate by feature** — booking components live under `components/booking/`, not a global `components/`
2. **Shared UI in `packages/ui`** — once monorepo is established; until then `components/ui/`
3. **No API calls in `data/`** — static content only
4. **Server components by default** — add `"use client"` only when needed
5. **Env vars** — only in `env.example` templates; never in source code literals
6. **Secrets** — never in `docs/` or markdown files

---

## Migration path from current PCD

| Step | Action |
|------|--------|
| 1 | Move `website/` → `apps/website/` |
| 2 | Add root `pnpm-workspace.yaml` + `turbo.json` |
| 3 | Create `packages/config` with shared ESLint/TS/Tailwind |
| 4 | Clone `apps/api`, `apps/mobile-driver` into monorepo |
| 5 | Move architecture docs to `docs/` |
| 6 | Delete `details.md`; replace with `docs/ENVIRONMENT_VARIABLES.md` |
| 7 | Add `infrastructure/docker/docker-compose.yml` |

---

*This structure supports independent deployability per app while sharing types, UI, and tooling.*
