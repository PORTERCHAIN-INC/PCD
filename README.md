# Porterchain (PCD)

Commercial logistics platform monorepo foundation.

## What's in this repo

| Path                                                                 | Description                                                       |
| -------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [`website/`](website/)                                               | Public Next.js site (port **3000**) — **only runnable app today** |
| [`env/`](env/README.md)                                              | Environment variable templates per service                        |
| [`apps/`](apps/)                                                     | Placeholders for API, merchant portal, driver app                 |
| [`services/fleetbase/`](services/fleetbase/)                         | Fleetbase stack reference                                         |
| [`infrastructure/docker/`](infrastructure/docker/docker-compose.yml) | Local MySQL, Redis, Mailhog, Valhalla                             |
| Architecture specs                                                   | See `SYSTEM_ARCHITECTURE.md` and related docs at repo root        |

## Quick start

### Prerequisites

- Node.js **20.18+** (see [`.nvmrc`](.nvmrc))
- [pnpm](https://pnpm.io) **9.15+**
- Docker (optional, for local data services)

### Website

```bash
corepack enable
pnpm install

cp env/website.env.example website/.env.local
# Add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY

pnpm dev          # http://localhost:3000
pnpm build
pnpm lint
```

### Local infrastructure (Docker)

```bash
cp infrastructure/docker/.env.example infrastructure/docker/.env
pnpm docker:up    # MySQL :3306, Redis :6379, Mailhog :8025
```

Valhalla routing (optional, large download):

```bash
pnpm docker:up:routing   # adds Valhalla :8002
```

## Monorepo scripts

| Command             | Description                               |
| ------------------- | ----------------------------------------- |
| `pnpm dev`          | Start all workspace dev servers (website) |
| `pnpm build`        | Production build                          |
| `pnpm lint`         | ESLint across workspace                   |
| `pnpm format`       | Prettier write                            |
| `pnpm format:check` | Prettier check (CI)                       |
| `pnpm docker:up`    | Core Docker services                      |
| `pnpm docker:down`  | Stop Docker services                      |

## Ports

| Port | Service                       |
| ---- | ----------------------------- |
| 3000 | Website                       |
| 3001 | Merchant portal (future)      |
| 8000 | Fleetbase API (future)        |
| 8001 | Porterchain API (recommended) |
| 8002 | Valhalla                      |
| 3306 | MySQL                         |
| 6379 | Redis                         |

See [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md).

## Architecture docs

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
- [TECH_STACK.md](TECH_STACK.md)
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
- [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md)
- [CONNECTIONS.md](CONNECTIONS.md) — driver app integrations

## Product & operations design

- [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)
- [BUSINESS_WORKFLOW.md](BUSINESS_WORKFLOW.md)
- [USER_JOURNEYS.md](USER_JOURNEYS.md)
- [ORDER_LIFECYCLE.md](ORDER_LIFECYCLE.md)
- [EXCEPTION_WORKFLOWS.md](EXCEPTION_WORKFLOWS.md)
- [ROLE_PERMISSIONS.md](ROLE_PERMISSIONS.md)
- [MODULE_BREAKDOWN.md](MODULE_BREAKDOWN.md)
- [EVENT_FLOW.md](EVENT_FLOW.md)
- [SYSTEM_SEQUENCE_DIAGRAMS.md](SYSTEM_SEQUENCE_DIAGRAMS.md)
- [ENTITY_RELATIONSHIP_MODEL.md](ENTITY_RELATIONSHIP_MODEL.md)

## Environment variables

Copy templates from [`env/`](env/README.md) — never commit secrets to git.

## CI

GitHub Actions workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
