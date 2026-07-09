# Porterchain — Technology Stack

**Type:** CANONICAL  
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)  
**Last verified:** 2026-07-08  
**Policy:** `.cursor/rules/porterchain-stack.mdc` · `.cursor/rules/dependency-freeze.mdc`

**Status:** Current stack as implemented in PCD monorepo

---

## Stack overview

| Layer           | Technology                                     | Status in PCD repo                         |
| --------------- | ---------------------------------------------- | ------------------------------------------ |
| Public website  | Next.js 16, React 19, TypeScript 6, Tailwind 4 | **Implemented** (`website/`)               |
| Merchant portal | Next.js 16, Clerk 7                            | **Implemented** (`apps/merchant-portal/`)  |
| Admin console   | Next.js 16, Clerk 7                            | **Implemented** (`apps/admin/`)            |
| Customer portal | Next.js 16, Clerk 7                            | **Implemented** (`apps/customer/`)         |
| Driver web      | Next.js 16, Clerk 7                            | **Implemented** (`apps/driver-portal/`)    |
| Driver mobile   | Expo SDK 57, React Native 0.86                 | **Shell** (`apps/mobile-driver/`)          |
| Customer mobile | Expo SDK 57, React Native 0.86                 | **Shell** (`apps/mobile-customer/`)        |
| Porterchain API | FastAPI 0.139+, Python 3.14.6, SQLAlchemy 2    | **Implemented** (`apps/api/`)              |
| Async worker    | Python 3.14.6, Redis queues, event bus         | **Implemented** (`apps/worker/`)           |
| Fleetbase API   | Laravel (PHP)                                  | Via `apps/fleetbase/` + adapter            |
| Porterchain DB  | PostgreSQL 18 (all environments)               | **Implemented** + Alembic migrations       |
| Fleetbase DB    | MySQL 8.0.46                                   | Docker (3306 core / 3307 Fleetbase stack)  |
| Cache / queue   | Redis 8.8 / Valkey 8.1 (Fleetbase override)    | **Implemented**                            |
| Dev email       | Mailpit v1.30.3                                | Ports 1025 (SMTP) / 8025 (UI)              |
| Routing         | Valhalla (primary), OSRM (fallback)            | Docker optional (`pnpm docker:up:routing`) |

---

## Runtime & tooling

| Technology         | Version in PCD                             | Notes                                 |
| ------------------ | ------------------------------------------ | ------------------------------------- |
| **Node.js**        | `24.18.0` (`.nvmrc`; engines `>=24.18.0`)  | All Next.js apps and root scripts     |
| **pnpm**           | `11.10.0` (`packageManager` in root)       | Monorepo workspaces                   |
| **Turbo**          | `2.10.4`                                   | `pnpm dev`, `pnpm build`, `pnpm lint` |
| **Prettier**       | `3.9.4`                                    | `pnpm format`, `pnpm format:check`    |
| **Python**         | `3.14.6`                                   | API + worker venv + Docker image      |
| **Docker Compose** | `infrastructure/docker/docker-compose.yml` | Profiles: core, routing, fleetbase    |

---

## Frontend (Next.js apps)

| Technology                | Version (admin) | Notes                       |
| ------------------------- | --------------- | --------------------------- |
| **Next.js**               | `16.2.10`       | App Router, `--webpack` dev |
| **React**                 | `19.2.7`        |                             |
| **TypeScript**            | `6.0.3`         |                             |
| **Tailwind CSS**          | `4.3.2`         | v4 PostCSS pipeline         |
| **@clerk/nextjs**         | `7.5.14`        | Per-portal Clerk apps       |
| **@tanstack/react-query** | `5.101.x`       | Portal data fetching        |
| **Zod**                   | `4.4.x`         | Client validation           |

---

## Mobile (Expo apps)

| Technology       | Version  | Apps                           |
| ---------------- | -------- | ------------------------------ |
| **Expo SDK**     | `57`     | mobile-driver, mobile-customer |
| **React Native** | `0.86`   | Blank shells (feature TBD)     |
| **React**        | `19.2.7` |                                |

---

## Backend (Porterchain API)

| Technology         | Version  | Notes                                |
| ------------------ | -------- | ------------------------------------ |
| **Python**         | `3.14.6` | API + worker (`apps/api/Dockerfile`) |
| **FastAPI**        | `0.139+` | Async API, OpenAPI at `/docs`        |
| **Uvicorn**        | `0.51+`  | ASGI server                          |
| **SQLAlchemy**     | `2.0+`   | ORM — PostgreSQL only                |
| **Alembic**        | `1.18+`  | Schema migrations                    |
| **Stripe**         | `15+`    | Python SDK — webhooks                |
| **firebase-admin** | `7.5+`   | FCM push (optional locally)          |

---

## Secrets & Clerk

| Store                         | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| `env/clerk.env`               | Local/test Clerk keys → `pnpm clerk:sync` |
| Doppler `pcd/prd`             | Production runtime secrets                |
| `env/clerk.env.prod-live.bak` | Live key backup (local only)              |

---

## Related

- [CONTRIBUTING_GUIDE.md](./CONTRIBUTING_GUIDE.md)
- [RUNBOOK.md](./RUNBOOK.md)
- [docs/SILICON_VALLEY_READINESS_CHECKLIST.md](./docs/SILICON_VALLEY_READINESS_CHECKLIST.md)
