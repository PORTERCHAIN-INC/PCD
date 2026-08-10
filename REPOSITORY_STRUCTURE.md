# Repository Structure

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Current monorepo layout

---

## Overview

Porterchain is a monorepo separating **customer-facing applications**, **shared packages**, **integration services**, and **upstream vendor dependencies**. Fleetbase is treated as an external logistics engine — never mixed with Porterchain business logic.

---

## Current structure

```
porterchain/
├── website/                    # Public marketing + booking (:3000)
├── apps/
│   ├── merchant-portal/        # B2B merchant portal (:3001)
│   ├── admin/                  # Ops control tower (:3002)
│   ├── driver-portal/          # Driver web dashboard (:3003)
│   ├── customer/               # Retail customer portal (:3004)
│   ├── api/                    # Porterchain FastAPI (:8001)
│   ├── worker/                 # Event bus + queue consumer
│   ├── mobile-driver/          # Driver mobile app (Expo SDK 57)
│   ├── mobile-customer/        # Customer mobile app (Expo SDK 57)
│   ├── fleetbase/              # Upstream Fleetbase clone — DO NOT MODIFY
│   ├── website/                # README placeholder → canonical `website/`
│   ├── merchant/               # README placeholder → `apps/merchant-portal/`
│   └── driver/                 # README placeholder → driver-portal + mobile-driver
│
├── packages/
│   ├── ui/                     # Shared React components
│   ├── config/                 # Shared config references
│   ├── types/                  # TypeScript types
│   ├── auth/                   # Clerk + RBAC helpers
│   ├── events/                 # Domain event catalog
│   └── queue/                  # Queue name constants
│
├── services/
│   ├── fleetbase-adapter/      # Sole Fleetbase integration boundary
│   ├── pricing-engine/         # porterchain_pricing library
│   ├── event-bus/              # porterchain_event_bus
│   ├── driver-platform/        # Driver domain library
│   ├── python/                 # porterchain_services (Stripe, maps, …)
│   └── fleetbase/              # DEPRECATED shim — re-exports adapter
│
├── shared/
│   ├── python/                 # porterchain_shared
│   ├── api/, theme/, maps/, …  # Shared TS packages (pnpm workspace)
│   └── mobile-*                # Mobile UI, security, offline packages
│
├── vendor/
│   └── fleetbase/              # Logical vendor reference (docs only)
│
├── infrastructure/
│   ├── docker/                 # Compose, Fleetbase overlays
│   └── deploy/                 # Production Caddy + GHCR deploy
│
├── docs/                       # Documentation index
└── env/                        # Environment templates
```

---

## Path aliases (canonical vs placeholder)

| Canonical path                | Placeholder / alias             | Status |
| ----------------------------- | ------------------------------- | ------ |
| `website/` (repo root)        | `apps/website/`                 | Active |
| `apps/merchant-portal/`       | `apps/merchant/`                | Active |
| `apps/customer/`              | —                               | Active |
| `apps/driver-portal/`         | `apps/driver/` (README pointer) | Active |
| `apps/mobile-driver/`         | —                               | Active |
| `apps/mobile-customer/`       | —                               | Active |
| `apps/admin/`                 | —                               | Active |
| `apps/api/`                   | —                               | Active |
| `apps/worker/`                | —                               | Active |
| `apps/fleetbase/`             | `vendor/fleetbase/` (docs only) | Active |
| `services/fleetbase-adapter/` | —                               | Active |

---

## Application boundaries

| App             | Port        | Talks to Fleetbase? | Notes                                       |
| --------------- | ----------- | ------------------- | ------------------------------------------- |
| Website         | 3000        | **No**              | Booking UI → Porterchain API only           |
| Merchant portal | 3001        | **No**              | B2B portal → Porterchain API                |
| Admin           | 3002        | **SSO only**        | Opens Fleetbase console via Porterchain SSO |
| Driver portal   | 3003        | **No**              | Driver web → Porterchain API                |
| Customer portal | 3004        | **No**              | Retail dashboard → Porterchain API          |
| Mobile driver   | Expo        | **No**              | Field execution → `/driver-api/v1/*`        |
| Mobile customer | Expo        | **No**              | Retail mobile → `/v1/*`                     |
| Porterchain API | 8001        | **Via adapter**     | Sole bridge to Fleetbase                    |
| Worker          | —           | **Via adapter**     | Event bus + queue consumer                  |
| Fleetbase       | 8000 / 4200 | N/A                 | Internal ops engine                         |

---

## Services layer

```
services/
├── fleetbase-adapter/          # porterchain_fleetbase_adapter — USE THIS
│   ├── client/
│   ├── auth/
│   ├── orders/
│   ├── dispatch/
│   ├── drivers/
│   ├── vehicles/
│   ├── tracking/
│   ├── routes/
│   ├── webhooks/
│   ├── events/
│   └── pod/
├── pricing-engine/             # porterchain_pricing
├── event-bus/                  # porterchain_event_bus
├── driver-platform/            # porterchain_driver
├── python/                     # porterchain_services
└── fleetbase/                  # DEPRECATED shim — re-exports adapter
```

**Rule:** All Fleetbase HTTP calls originate in `fleetbase-adapter/`.

---

## Packages layer

| Package           | Language   | Purpose                       |
| ----------------- | ---------- | ----------------------------- |
| `packages/ui`     | TypeScript | Shared UI primitives          |
| `packages/types`  | TypeScript | Shared types                  |
| `packages/auth`   | TypeScript | Clerk client helpers          |
| `packages/events` | TypeScript | Event envelope types          |
| `packages/queue`  | TypeScript | Queue name constants          |
| `shared/python`   | Python     | Settings, events, queue names |
| `shared/mobile-*` | TypeScript | Mobile UI, offline, security  |

---

## Vendor: Fleetbase

| Path                | Role                                             |
| ------------------- | ------------------------------------------------ |
| `apps/fleetbase/`   | **Actual upstream clone** — Docker, console, API |
| `vendor/fleetbase/` | Documentation anchor only                        |

### Never modify

```
apps/fleetbase/api/           # Laravel shell
apps/fleetbase/console/       # Ember console
apps/fleetbase/packages/      # Upstream submodules
apps/fleetbase/docker/        # Upstream Dockerfiles
apps/fleetbase/infra/         # Upstream Helm
```

### Safe Porterchain touchpoints

```
infrastructure/docker/fleetbase.porterchain.override.yml
env/fleetbase.env.example
services/fleetbase-adapter/                    # All integration logic
```

---

## PYTHONPATH (development)

```bash
PYTHONPATH=src:../../shared/python:../../services/python:../../services/fleetbase-adapter:../../services/pricing-engine:../../services/event-bus:../../services/driver-platform
```

Configured in `package.json` → `dev:api`, `dev:worker`.

---

## Python editable installs

```
apps/api/requirements.txt:
  -e ../../shared/python
  -e ../../services/python
  -e ../../services/fleetbase-adapter
  -e ../../services/pricing-engine
  -e ../../services/event-bus
  -e ../../services/driver-platform
  -e ../../services/fleetbase          # deprecated shim
```

---

## pnpm workspace

```yaml
packages:
  - "website"
  - "apps/merchant-portal"
  - "apps/driver-portal"
  - "apps/customer"
  - "apps/admin"
  - "apps/mobile-driver"
  - "apps/mobile-customer"
  - "packages/*"
  - "shared/*"
```

---

## Where customizations belong

| Customization                     | Location                                      |
| --------------------------------- | --------------------------------------------- |
| Order → Fleetbase payload mapping | `services/fleetbase-adapter/.../mappers.py`   |
| Webhook event → Porterchain state | `services/fleetbase-adapter/.../events/`      |
| SSO bridge client                 | `services/fleetbase-adapter/.../auth/`        |
| Fleetbase bridge API routes       | Separate Fleetbase extension package (future) |
| Merchant pricing rules            | `apps/api/merchant_engine/`                   |
| Public tracking UX                | `website/`                                    |
| Ops dashboard widgets             | `apps/admin/`                                 |
| Docker port overrides             | `infrastructure/docker/`                      |

---

## Documentation map

See [docs/README.md](./docs/README.md) for the full index.

---

## Related documents

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- [CONTRIBUTING_GUIDE.md](./CONTRIBUTING_GUIDE.md)
- [vendor/fleetbase/README.md](./vendor/fleetbase/README.md)

---
