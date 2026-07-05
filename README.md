# Porterchain (PCD)

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Commercial logistics platform monorepo — website, API, portals, worker, and Fleetbase integration.

> **Architecture:** [masterrule.md](./masterrule.md) · **Doc rollout:** [Appendix C](./masterrule.md#appendix-c--documentation-simplification-program) · **Audit:** [CTO_AUDIT_REPORT.md](./CTO_AUDIT_REPORT.md)

## Applications

| Path                                             | Port     | Description                                                                          |
| ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------ |
| [`website/`](website/)                           | **3000** | Public Next.js site — marketing, booking, track (link to customer app for dashboard) |
| [`apps/merchant-portal/`](apps/merchant-portal/) | **3001** | B2B merchant dashboard (Clerk)                                                       |
| [`apps/admin/`](apps/admin/)                     | **3002** | Business admin / ops (Clerk)                                                         |
| [`apps/driver-portal/`](apps/driver-portal/)     | **3003** | Driver web dashboard                                                                 |
| [`apps/customer/`](apps/customer/)               | **3004** | Retail customer portal                                                               |
| [`apps/api/`](apps/api/)                         | **8001** | Porterchain API (FastAPI) — all business logic                                       |
| [`apps/worker/`](apps/worker/)                   | —        | Event bus + queue consumer                                                           |
| [`apps/mobile-driver/`](apps/mobile-driver/)     | Expo     | Driver mobile app (Expo SDK 52)                                                      |
| [`apps/mobile-customer/`](apps/mobile-customer/) | Expo     | Retail customer mobile app (Expo SDK 52)                                             |

Path aliases: `website/` = public site (target `apps/website/`); `apps/merchant-portal/` = merchant portal (target `apps/merchant/`).

## Quick start

### Prerequisites

- Node.js **24.18.0** (see [`.nvmrc`](.nvmrc); engines `>=24`)
- [pnpm](https://pnpm.io) **9.15+**
- Python **3.13** for API/worker (see [TECH_STACK.md](TECH_STACK.md))
- Docker (Postgres, Redis, Mailhog)

### Install

```bash
corepack enable
pnpm install
cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Environment

Copy templates from [`env/`](env/README.md) to each app (e.g. `apps/api/.env`, `website/.env.local`).

### Run locally

```bash
pnpm docker:up          # Postgres :5432, Redis :6379, Mailhog :8025
pnpm dev:api            # API :8001
pnpm dev:worker         # async worker
pnpm dev                # website :3000
pnpm dev:merchant       # :3001
pnpm dev:admin          # :3002
pnpm dev:driver         # :3003
pnpm dev:customer       # :3004
```

Mobile apps: `pnpm dev:mobile-driver` or `pnpm dev:mobile-customer`

### Database migrations

```bash
pnpm db:migrate         # alembic upgrade head (PostgreSQL production)
pnpm db:revision -- -m "describe change"
```

PostgreSQL uses Alembic migrations — see [`apps/api/alembic/README.md`](apps/api/alembic/README.md). Run `pnpm db:migrate` before starting the API.

## Monorepo scripts

| Command           | Description                           |
| ----------------- | ------------------------------------- |
| `pnpm dev`        | Turbo dev (website + configured apps) |
| `pnpm dev:api`    | Porterchain API                       |
| `pnpm dev:worker` | Queue + event bus worker              |
| `pnpm build`      | Production build                      |
| `pnpm docker:up`  | Core Docker services                  |

## Ports

| Port | Service                             |
| ---- | ----------------------------------- |
| 3000 | Website                             |
| 3001 | Merchant portal                     |
| 3002 | Admin                               |
| 3003 | Driver portal                       |
| 3004 | Customer portal                     |
| 8001 | Porterchain API                     |
| 8000 | Fleetbase API (when enabled)        |
| 5432 | PostgreSQL (Porterchain-owned data) |
| 6379 | Redis                               |

See [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md).

## Architecture

- [masterrule.md](masterrule.md) — locked rules and layer boundaries
- [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) — platform topology (code-derived)
- [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) — go/no-go status (July 2026)
- [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) — monorepo layout
- [TECH_STACK.md](TECH_STACK.md)
- [docs/README.md](docs/README.md) — full documentation index

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
