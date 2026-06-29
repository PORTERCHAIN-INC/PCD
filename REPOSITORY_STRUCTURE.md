# Repository Structure

**Document version:** 1.0  
**Date:** June 29, 2026  
**Status:** Target layout with migration notes

---

## Overview

Porterchain is a monorepo separating **customer-facing applications**, **shared packages**, **integration services**, and **upstream vendor dependencies**. Fleetbase is treated as an external logistics engine — never mixed with Porterchain business logic.

---

## Target structure

```
porterchain/
├── apps/
│   ├── website/              # Public marketing + booking (:3000)
│   ├── merchant/             # B2B merchant portal (:3001)
│   ├── customer/             # Retail customer dashboard (planned)
│   ├── admin/                # Ops control tower (:3002)
│   ├── api/                  # Porterchain FastAPI (:8001)
│   ├── driver/               # Driver mobile app (planned)
│   └── fleetbase/            # Upstream Fleetbase clone — DO NOT MODIFY
│
├── packages/
│   ├── ui/                   # Shared React components
│   ├── config/               # Shared config references
│   ├── types/                # TypeScript types
│   ├── auth/                 # Clerk + RBAC helpers
│   ├── events/               # Domain event catalog
│   └── shared/               # Python shared code pointer
│
├── services/
│   └── fleetbase-adapter/    # Sole Fleetbase integration boundary
│
├── vendor/
│   └── fleetbase/            # Logical vendor reference (docs only)
│
├── shared/
│   └── python/               # porterchain_shared Python package
│
├── infrastructure/
│   └── docker/               # Compose, Fleetbase overlays
│
├── docs/                     # Documentation index
└── env/                      # Environment templates
```

---

## Current vs target paths

| Target                        | Current canonical path        | Status                                 |
| ----------------------------- | ----------------------------- | -------------------------------------- |
| `apps/website/`               | `website/` (repo root)        | README placeholder at `apps/website/`  |
| `apps/merchant/`              | `apps/merchant-portal/`       | README placeholder at `apps/merchant/` |
| `apps/customer/`              | —                             | Planned                                |
| `apps/admin/`                 | `apps/admin/`                 | Active                                 |
| `apps/api/`                   | `apps/api/`                   | Active                                 |
| `apps/driver/`                | —                             | Planned (`apps/mobile-driver` TBD)     |
| `vendor/fleetbase/`           | `apps/fleetbase/`             | Source stays at `apps/fleetbase/`      |
| `services/fleetbase-adapter/` | `services/fleetbase-adapter/` | **Active**                             |
| `packages/shared/`            | `shared/python/`              | README pointer                         |

---

## Application boundaries

| App       | Port        | Talks to Fleetbase? | Notes                                       |
| --------- | ----------- | ------------------- | ------------------------------------------- |
| Website   | 3000        | **No**              | Booking UI → Porterchain API only           |
| Merchant  | 3001        | **No**              | B2B portal → Porterchain API                |
| Customer  | TBD         | **No**              | Retail dashboard (planned)                  |
| Admin     | 3002        | **SSO only**        | Opens Fleetbase console via Porterchain SSO |
| API       | 8001        | **Via adapter**     | Sole bridge to Fleetbase                    |
| Driver    | TBD         | **No**              | Execution API via Porterchain               |
| Fleetbase | 8000 / 4200 | N/A                 | Internal ops engine                         |

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
├── fleetbase/                  # DEPRECATED shim — re-exports adapter
└── python/                   # porterchain_services worker package
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
PYTHONPATH=src:../../shared/python:../../services/python:../../services/fleetbase-adapter:../../services/fleetbase
```

Configured in `package.json` → `dev:api`, `dev:worker`.

---

## Python editable installs

```
apps/api/requirements.txt:
  -e ../../shared/python
  -e ../../services/python
  -e ../../services/fleetbase-adapter
  -e ../../services/fleetbase          # deprecated shim
```

---

## pnpm workspace

```yaml
packages:
  - "website"
  - "apps/merchant-portal"
  - "apps/admin"
  - "packages/*"
```

---

## Where customizations belong

| Customization                     | Location                                      |
| --------------------------------- | --------------------------------------------- |
| Order → Fleetbase payload mapping | `services/fleetbase-adapter/.../mappers.py`   |
| Webhook event → Porterchain state | `services/fleetbase-adapter/.../events/`      |
| SSO bridge client                 | `services/fleetbase-adapter/.../auth/`        |
| Fleetbase bridge API routes       | Separate Fleetbase extension package (future) |
| Merchant pricing rules            | `apps/api/booking_engine/`                    |
| Public tracking UX                | `website/`                                    |
| Ops dashboard widgets             | `apps/admin/`                                 |
| Docker port overrides             | `infrastructure/docker/`                      |

---

## Documentation map

See [docs/README.md](./docs/README.md) for the full index.

---

## Related documents

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)
- [CONTRIBUTING_GUIDE.md](./CONTRIBUTING_GUIDE.md)
- [vendor/fleetbase/README.md](./vendor/fleetbase/README.md)
