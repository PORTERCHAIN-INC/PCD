# Porterchain — Technology Stack

**Document version:** 1.0  
**Date:** June 29, 2026  
**Status:** Audit + standardization recommendations

---

## Stack overview

| Layer | Technology | Status in PCD repo |
|-------|------------|-------------------|
| Public website | Next.js 16, React 19, TypeScript, Tailwind 4 | **Implemented** |
| Merchant portal | Next.js (inferred) | Documented only |
| Admin console | Fleetbase (Ember + Laravel API) | Documented only |
| Driver app | Expo 52, React Native 0.76 | Documented only |
| Porterchain API | FastAPI (Python) | Documented only |
| Fleetbase API | Laravel (PHP) | Documented only |
| Primary DB | MySQL 8 (Fleetbase) | Documented only |
| Cache / queue | Redis 7 | Documented only |
| Routing | Valhalla (primary), OSRM (fallback) | Documented only |

---

## Standardized versions (target)

These are the **recommended pinned versions** for enterprise development across all Porterchain projects.

### Runtime & tooling

| Technology | Recommended version | Reason | Current in PCD |
|------------|---------------------|--------|----------------|
| **Node.js** | `20.18 LTS` (min `20.9.0`) | Next.js 16 requirement; stable LTS | Not pinned (no `.nvmrc`) |
| **Node.js (EAS builds)** | `22.14` | Driver app production EAS profile | Documented in CONNECTIONS.md |
| **pnpm** | `9.15.x` | Monorepo workspaces; referenced in driver docs | Not used (npm in website) |
| **Docker** | `27.x` | Container runtime | Not in repo |
| **Docker Compose** | `v2.29+` | Multi-service local dev | Not in repo |

### Frontend (website, merchant portal, admin SPA)

| Technology | Recommended version | Reason | Current in PCD |
|------------|---------------------|--------|----------------|
| **Next.js** | `16.2.9` | App Router, React 19 support, stable 16.x | `16.2.9` ✓ |
| **React** | `19.2.4` | Matches Next 16 peer | `19.2.4` ✓ |
| **react-dom** | `19.2.4` | Lock with React | `19.2.4` ✓ |
| **TypeScript** | `5.9.x` | Latest 5.x stable | `5.9.3` ✓ |
| **Tailwind CSS** | `4.3.x` | v4 PostCSS pipeline | `4.3.1` ✓ |
| **next-intl** | `4.13.x` | i18n for en/fr | `4.13.0` ✓ |
| **framer-motion** | `12.x` | Animation (website) | `12.42.0` ✓ |
| **ESLint** | `9.x` | Flat config | `9.39.4` ✓ |
| **eslint-config-next** | `16.2.9` | Match Next version | `16.2.9` ✓ |

### Mobile (driver app)

| Technology | Recommended version | Reason | Source |
|------------|---------------------|--------|--------|
| **Expo SDK** | `52` | Current driver stack | CONNECTIONS.md |
| **React Native** | `0.76` | Bundled with Expo 52 | CONNECTIONS.md |
| **react-native-maps** | Pin per Expo 52 | Google Maps tiles | CONNECTIONS.md |
| **@mapbox/polyline** | Latest 1.x | Route polyline decode | CONNECTIONS.md |
| **expo-secure-store** | Expo 52 compatible | Token storage | CONNECTIONS.md |
| **EAS CLI** | Latest | Cloud builds | CONNECTIONS.md |

### Backend (Porterchain API)

| Technology | Recommended version | Reason | Source |
|------------|---------------------|--------|--------|
| **Python** | `3.12` | FastAPI ecosystem standard | Industry default |
| **FastAPI** | `0.115+` | Async API, OpenAPI native | Documented `apps/api` |
| **Uvicorn** | `0.32+` | ASGI server | Standard pairing |
| **Pydantic** | `v2` | FastAPI v2 models | Standard pairing |
| **SQLAlchemy** | `2.0+` | ORM if Porterchain-owned Postgres | Recommended |
| **Alembic** | `1.14+` | Migrations | Recommended |

### Backend (Fleetbase)

| Technology | Recommended version | Reason | Source |
|------------|---------------------|--------|--------|
| **PHP** | `8.2+` | Laravel 10/11 requirement | Fleetbase standard |
| **Laravel** | Per Fleetbase release | Core framework | Fleetbase |
| **MySQL** | `8.0` | `DB_CONNECTION=mysql` | details.md |
| **Redis** | `7.2` | Cache + queue | details.md |

### Data stores

| Technology | Recommended version | Reason | Notes |
|------------|---------------------|--------|-------|
| **MySQL** | `8.0` | Fleetbase primary store | `fleetbase` database |
| **PostgreSQL** | `16` | **Recommended for Porterchain-owned data** if split from Fleetbase | Not currently used |
| **Redis** | `7.2` | Session cache, queues, rate limits | `REDIS_HOST=cache` |

> **Note:** Platform docs reference MySQL for Fleetbase. PostgreSQL is recommended for future Porterchain-native services (billing ledger, merchant contracts) if decoupling from Fleetbase schema.

### Routing engines

| Technology | Recommended version | Reason | Source |
|------------|---------------------|--------|--------|
| **Valhalla** | Latest stable image | `ROUTING_ENGINE=valhalla`, self-hosted `:8002` | details.md |
| **OSRM** | Public or self-hosted | Fallback `OSRM_HOST` | details.md |

### Infrastructure

| Technology | Recommended version | Reason |
|------------|---------------------|--------|
| **Nginx** | `1.27` | Reverse proxy, TLS termination |
| **Traefik** | `3.x` | Alternative to Nginx for Docker-native routing |
| **DigitalOcean** | Managed droplets / K8s | `DIGITALOCEAN_API_TOKEN` in platform config |

### Auth SDKs

| SDK | Recommended version | Used by | In PCD repo |
|-----|---------------------|---------|-------------|
| **@clerk/nextjs** | `6.x` | Merchant portal, driver web | No |
| **@supabase/supabase-js** | `2.x` | Website booking OTP | No (planned) |
| **expo-secure-store** | Expo 52 | Driver token storage | External |

### Payments

| SDK | Recommended version | Used by | In PCD repo |
|-----|---------------------|---------|-------------|
| **stripe** (Node) | `17.x` | Merchant portal | No |
| **stripe** (Python) | `11.x` | Porterchain API webhooks | No |

### Maps

| SDK | Recommended version | Used by | In PCD repo |
|-----|---------------------|---------|-------------|
| **@vis.gl/react-google-maps** | `1.8.x` | Website Places autocomplete | `1.8.3` ✓ |
| **@googlemaps/js-api-loader** | `2.x` (transitive) | Maps loader | `2.1.1` ✓ |
| **@types/google.maps** | `3.65.x` | TypeScript | `3.65.2` ✓ |
| **react-native-maps** | Expo 52 pin | Driver app | External |
| **Mapbox** | `@mapbox/polyline` 1.x | Driver polyline decode only | External |

### Communications

| SDK | Recommended version | Used by | In PCD repo |
|-----|---------------------|---------|-------------|
| **twilio** | `5.x` | SMS OTP (API) | No |
| **resend** | `4.x` | Alternative email (evaluate vs Zoho) | No |
| **firebase-admin** | `13.x` | FCM push (API) | No |

### Observability

| SDK | Recommended version | Status |
|-----|---------------------|--------|
| **@sentry/nextjs** | `8.x` | **Not installed** — recommended |
| **@sentry/react-native** | `6.x` | **Not installed** — recommended |
| **sentry-sdk** (Python) | `2.x` | **Not installed** — recommended |

### API documentation

| Tool | Recommended | Status |
|------|-------------|--------|
| **OpenAPI 3.1** | FastAPI auto-generates | Not in PCD repo |
| **Swagger UI** | `/docs` on FastAPI | Not in PCD repo |

### Code quality

| Tool | Recommended version | In PCD repo |
|------|---------------------|-------------|
| **ESLint** | `9.x` | Yes |
| **Prettier** | `3.4.x` | **No** — add |
| **Husky** | `9.x` | **No** — add |
| **lint-staged** | `15.x` | **No** — add |
| **Turbo** | `2.x` | **No** — add for monorepo |
| **Vitest** | `3.x` | **No** — add |
| **Playwright** | `1.51+` | **No** (optional peer of Next only) |

---

## Technology choices — rationale

| Choice | Why |
|--------|-----|
| **Next.js** | SSR/SSG for SEO-heavy marketing site; App Router; i18n; Vercel-compatible |
| **FastAPI** | Typed Python API; OpenAPI; async; good for driver execution + webhooks |
| **Fleetbase** | Open-source dispatch OS; routing integration; control tower |
| **Clerk** | Managed auth for merchant/driver web; JWKS verification |
| **Supabase Auth** | Quick OTP for anonymous retail booking without full account |
| **Valhalla** | Self-hosted routing; GTA-scale; no per-request billing |
| **Redis** | Queue + cache for Laravel/Fleetbase; rate limiting |
| **Stripe** | PCI-compliant payments; invoicing + retail checkout |
| **Expo** | Faster mobile delivery; EAS for App Store pipeline |

---

## Upgrade recommendations

### Immediate (website — in repo)

| Item | Action | Priority |
|------|--------|----------|
| Add `.nvmrc` → `20.18.0` | Pin Node across team | High |
| Add `packageManager: "pnpm@9.15.0"` | Prepare monorepo migration | High |
| Add Prettier + Husky | Consistent formatting | Medium |
| Evaluate `gray-matter` → `2.0.1` or replace with `contentlayer` | Fix moderate CVE via js-yaml | Medium |
| Add `@sentry/nextjs` | Production error tracking | High |
| Add Vitest + Playwright | Test foundation | Medium |

### Platform (external repos)

| Item | Action | Priority |
|------|--------|----------|
| Consolidate npm → pnpm workspaces | Single lockfile, Turbo cache | High |
| Separate API ports (8000 vs 8001) | Dev port conflict | High |
| Add OpenAPI spec export to CI | Contract testing | High |
| Evaluate Resend vs Zoho SMTP | Deliverability + DX | Low |
| Add PostgreSQL for Porterchain-native tables | Schema ownership | Medium |

---

## Deprecated / avoid

| Item | Status | Recommendation |
|------|--------|----------------|
| Legacy Google Places Autocomplete | Migrated to Places API (New) on website | Keep using `PlaceAutocompleteElement` |
| `/driver` legacy routes | Still used by driver app | Deprecate after `/driver-api/v1` parity |
| `FILESYSTEM_DRIVER=public` | Local disk storage | Migrate to S3-compatible object storage |
| Secrets in `details.md` | **Critical risk** | Remove; use secret manager |
| npm in monorepo | Single project uses npm | Standardize on pnpm |
| Firebase Auth in driver app | Not used | Do not add unless required |

---

## Future roadmap

### Phase 1 — Foundation (Q3 2026)
- Monorepo with pnpm + Turbo
- Docker Compose for full local stack
- `.env.example` per service
- CI: lint, typecheck, build, test
- Sentry across website, API, mobile

### Phase 2 — Integration (Q4 2026)
- Website booking → Porterchain API
- OpenAPI client generation for portals
- Unified design system package (`@porterchain/ui`)
- Playwright E2E for booking + merchant flows

### Phase 3 — Scale (2027)
- Kubernetes or DO App Platform
- Read replicas for MySQL
- Redis Cluster for HA
- Event bus (Redis Streams or NATS) for dispatch events
- PostgreSQL for Porterchain billing ledger

---

## Version lock file (website — evidence)

Source: `website/package-lock.json` (June 2026)

```
next:           16.2.9
react:          19.2.4
react-dom:      19.2.4
typescript:     5.9.3
tailwindcss:    4.3.1
next-intl:      4.13.0
eslint:         9.39.4
@vis.gl/react-google-maps: 1.8.3
```

---

*Versions should be pinned in `.nvmrc`, `package.json#engines`, and CI images. Re-audit quarterly.*
