# Porterchain — Technology Stack

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Current stack as implemented in PCD monorepo

---

## Stack overview

| Layer           | Technology                                   | Status in PCD repo                             |
| --------------- | -------------------------------------------- | ---------------------------------------------- |
| Public website  | Next.js 16, React 19, TypeScript, Tailwind 4 | **Implemented** (`website/`)                   |
| Merchant portal | Next.js 16, Clerk                            | **Implemented** (`apps/merchant-portal/`)      |
| Admin console   | Next.js 16, Clerk                            | **Implemented** (`apps/admin/`)                |
| Customer portal | Next.js 16, Clerk                            | **Implemented** (`apps/customer/`)             |
| Driver web      | Next.js 16, Clerk                            | **Implemented** (`apps/driver-portal/`)        |
| Driver mobile   | Expo 52, React Native 0.76                   | **Implemented** — 72% prod readiness           |
| Customer mobile | Expo 52, React Native 0.76                   | **Implemented** — 62% prod readiness           |
| Porterchain API | FastAPI, Python 3.13, SQLAlchemy 2, Alembic  | **Implemented** (`apps/api/`)                  |
| Async worker    | Python, Redis queues, event bus              | **Implemented** (`apps/worker/`)               |
| Fleetbase API   | Laravel (PHP)                                | Via `apps/fleetbase/` + adapter                |
| Porterchain DB  | PostgreSQL 16 (all environments)             | **Implemented** + Alembic migrations           |
| Fleetbase DB    | MySQL 8                                      | Docker (port 3306 core / 3307 Fleetbase stack) |
| Cache / queue   | Redis 7.2                                    | **Implemented**                                |
| Routing         | Valhalla (primary), OSRM (fallback)          | Docker optional (`pnpm docker:up:routing`)     |

---

## Runtime & tooling

| Technology         | Version in PCD                             | Notes                                 |
| ------------------ | ------------------------------------------ | ------------------------------------- |
| **Node.js**        | `24.18.0` (`.nvmrc`; engines `>=24`)       | All Next.js apps and root scripts     |
| **pnpm**           | `9.15.4` (`packageManager` in root)        | Monorepo workspaces                   |
| **Turbo**          | `2.3.3`                                    | `pnpm dev`, `pnpm build`, `pnpm lint` |
| **Prettier**       | `3.4.2`                                    | `pnpm format`, `pnpm format:check`    |
| **Docker Compose** | `infrastructure/docker/docker-compose.yml` | Profiles: core, routing, proxy        |

---

## Frontend (Next.js apps)

| Technology                    | Version (website) | Notes                     |
| ----------------------------- | ----------------- | ------------------------- |
| **Next.js**                   | `16.2.10`         | App Router                |
| **React**                     | `19.2.7`          | Matches Next 16 peer      |
| **TypeScript**                | `5.9.x`           | Shared via packages       |
| **Tailwind CSS**              | `4.3.x`           | v4 PostCSS pipeline       |
| **next-intl**                 | `4.13.x`          | i18n en/fr (website)      |
| **@clerk/nextjs**             | `7.x`             | Portals + website auth    |
| **@vis.gl/react-google-maps** | `1.8.3`           | Places autocomplete, maps |

---

## Mobile (Expo apps)

| Technology             | Version     | Apps                           |
| ---------------------- | ----------- | ------------------------------ |
| **Expo SDK**           | `52`        | mobile-driver, mobile-customer |
| **React Native**       | `0.76`      | Bundled with Expo 52           |
| **@clerk/clerk-expo**  | `7.x`       | Auth                           |
| **react-native-maps**  | Expo 52 pin | Map display                    |
| **MMKV**               | Latest      | Offline queue storage          |
| **Firebase messaging** | Optional    | Push (requires prod creds)     |

---

## Backend (Porterchain API)

| Technology         | Version  | Notes                                |
| ------------------ | -------- | ------------------------------------ |
| **Python**         | `3.13`   | API + worker (`apps/api/Dockerfile`) |
| **FastAPI**        | `0.115+` | Async API, OpenAPI at `/docs`        |
| **SQLAlchemy**     | `2.0+`   | ORM — PostgreSQL only                |
| **Alembic**        | `1.14+`  | Schema migrations                    |
| **Stripe**         | `11+`    | Python SDK — webhooks                |
| **firebase-admin** | `13+`    | FCM push (optional locally)          |

---

## Backend (Fleetbase)

| Technology | Version | Notes                   |
| ---------- | ------- | ----------------------- |
| **PHP**    | `8.2+`  | Laravel                 |
| **MySQL**  | `8.0`   | Fleetbase primary store |
| **Redis**  | `7.2`   | Cache + queue           |

Fleetbase runs as a **separate Docker stack** (`pnpm docker:fleetbase:up`), not inside the Porterchain core compose.

---

## Data stores

| Technology     | Port | Owner                                   | Purpose                     |
| -------------- | ---- | --------------------------------------- | --------------------------- |
| **PostgreSQL** | 5432 | Porterchain                             | All business data (Alembic) |
| **MySQL**      | 3306 | Porterchain core / 3307 Fleetbase stack | Fleetbase only              |
| **Redis**      | 6379 | Shared                                  | Cache, queues, rate limits  |

SQLite has been **removed** from Porterchain runtime code. See [docs/archive/SQLITE_AUDIT.md](./docs/archive/SQLITE_AUDIT.md) for migration history.

---

## Routing engines

| Engine       | Default endpoint                           | Start command            |
| ------------ | ------------------------------------------ | ------------------------ |
| **Valhalla** | `http://localhost:8002`                    | `pnpm docker:up:routing` |
| **OSRM**     | `https://router.project-osrm.org` (public) | Fleetbase env / fallback |

---

## Infrastructure

| Component          | Local                       | Production                       |
| ------------------ | --------------------------- | -------------------------------- |
| **Docker Compose** | `infrastructure/docker/`    | `infrastructure/deploy/` (Caddy) |
| **CI/CD**          | `.github/workflows/ci.yml`  | GHCR images → droplet deploy     |
| **Mailhog**        | `:8025` (dev email capture) | Real SMTP in prod                |

Portal Dockerfiles exist: `website/`, `apps/admin/`, `apps/merchant-portal/`, `apps/driver-portal/`, `apps/customer/`, `apps/api/`.

---

## Auth

| Method              | Used by                                      |
| ------------------- | -------------------------------------------- |
| **Clerk**           | Website, merchant, admin, driver web, mobile |
| **Porterchain JWT** | Driver mobile API (`/driver-api/v1/*`)       |
| **Fleetbase SSO**   | Admin → Fleetbase console (via adapter)      |
| **Stripe webhooks** | Retail checkout confirmation                 |

Legacy Supabase OTP paths are removed. See [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md).

---

## Observability (gaps)

| Tool                    | Status             |
| ----------------------- | ------------------ |
| **@sentry/nextjs**      | Not installed      |
| **sentry-sdk** (Python) | Not installed      |
| Structured logging      | Partial (API logs) |

---

## Open gaps (not stack blockers)

| Item                     | Status                                       |
| ------------------------ | -------------------------------------------- |
| Global API rate limiting | Partial — needs Redis sliding window in prod |
| FCM push in production   | Requires Firebase credentials                |
| Sentry                   | Recommended, not yet wired                   |
| Husky / lint-staged      | Not configured at root                       |

Platform go/no-go: [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md).

---

## Related documents

- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) — monorepo layout
- [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) — local ports
- [DOCKER_SETUP.md](./DOCKER_SETUP.md) — Fleetbase Docker stack
- [DOCKER_ARCHITECTURE.md](./DOCKER_ARCHITECTURE.md) — compose architecture

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
