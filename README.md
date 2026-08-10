# PorterChain (PCD)

**Type:** CANONICAL  
**Last verified:** 2026-08-07

Transportation Capacity Network monorepo — website, API, portals, worker, and Fleetbase integration.

> **Charter:** [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md) · **Architecture:** [masterrule.md](masterrule.md) · **Docs index:** [docs/README.md](docs/README.md) · **Todos:** [docs/PRIORITY_TODOS.md](docs/PRIORITY_TODOS.md)

## Applications

| Path                                             | Port     | Description                                     |
| ------------------------------------------------ | -------- | ----------------------------------------------- |
| [`website/`](website/)                           | **3000** | Public Next.js site — marketing, booking, track |
| [`apps/merchant-portal/`](apps/merchant-portal/) | **3001** | B2B merchant dashboard                          |
| [`apps/admin/`](apps/admin/)                     | **3002** | Business admin / Control Tower                  |
| [`apps/driver-portal/`](apps/driver-portal/)     | **3003** | Driver web dashboard                            |
| [`apps/customer/`](apps/customer/)               | **3004** | Retail customer portal                          |
| [`apps/api/`](apps/api/)                         | **8001** | PorterChain API (FastAPI)                       |
| [`apps/worker/`](apps/worker/)                   | —        | Event bus + queue consumer                      |
| [`apps/mobile-driver/`](apps/mobile-driver/)     | Expo     | Driver mobile (Expo SDK **57**)                 |
| [`apps/mobile-customer/`](apps/mobile-customer/) | Expo     | Customer mobile (Expo SDK **57**)               |

## Quick start

### Prerequisites

- Node.js **24.18** (see [`.nvmrc`](.nvmrc))
- [pnpm](https://pnpm.io) **11.10**
- Python **3.14.6** for API/worker (see [TECH_STACK.md](TECH_STACK.md))
- Docker (Postgres **18**, Redis, **Mailpit**)

### Install

```bash
corepack enable
pnpm install
cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Environment

Copy templates from [`env/`](env/README.md) into each app. Clerk: `env/clerk.env` → `pnpm clerk:sync`.

### Run locally

```bash
pnpm docker:up          # Postgres :5432, Redis :6379, Mailpit :8025
pnpm db:migrate
pnpm dev:api            # API :8001
pnpm dev:worker
pnpm dev                # website :3000
pnpm dev:merchant       # :3001
pnpm dev:admin          # :3002
pnpm dev:driver         # :3003
pnpm dev:customer       # :3004
```

```bash
curl -s http://localhost:8001/health/ready | python3 -m json.tool
```

Onboarding walkthrough: [docs/ONBOARDING_ENGINEER.md](docs/ONBOARDING_ENGINEER.md).

## Ports

| Port      | Service                      |
| --------- | ---------------------------- |
| 3000–3004 | Website + portals            |
| 8001      | PorterChain API              |
| 8000      | Fleetbase API (when enabled) |
| 5432      | PostgreSQL                   |
| 6379      | Redis                        |
| 8025      | Mailpit UI                   |

See [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md).

## Documentation

| Document                                                   | Role                            |
| ---------------------------------------------------------- | ------------------------------- |
| [docs/README.md](docs/README.md)                           | **Full documentation index**    |
| [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md) | Company charter                 |
| [masterrule.md](masterrule.md)                             | Architecture rules              |
| [TECH_STACK.md](TECH_STACK.md)                             | Version SSOT                    |
| [docs/ops/ORDERS_MODULE.md](docs/ops/ORDERS_MODULE.md)     | Control Tower / Order 360       |
| [RUNBOOK.md](RUNBOOK.md)                                   | Operations runbook              |
| [docs/archive/](docs/archive/)                             | Historical audits (do not edit) |
