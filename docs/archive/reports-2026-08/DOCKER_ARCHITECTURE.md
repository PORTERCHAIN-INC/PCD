# Porterchain — Docker Architecture

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Implemented — two independent compose stacks

---

## Overview

Porterchain local development uses **two separate Docker Compose projects**:

1. **Porterchain core** — PostgreSQL, MySQL, Redis, Mailhog, Valhalla (`infrastructure/docker/docker-compose.yml`)
2. **Fleetbase stack** — Laravel API, console, SocketCluster (`apps/fleetbase/` + Porterchain overlay)

Frontends (Next.js) and the Porterchain API/worker run on the **host** via pnpm for hot reload. Production uses GHCR images + Caddy in `infrastructure/deploy/`.

---

## Stack 1 — Porterchain core

**File:** `infrastructure/docker/docker-compose.yml`  
**Project name:** `porterchain`

| Service    | Profile         | Image                                             | Host port      | Purpose                    |
| ---------- | --------------- | ------------------------------------------------- | -------------- | -------------------------- |
| `postgres` | core            | `postgres:16-alpine`                              | 127.0.0.1:5432 | Porterchain business data  |
| `database` | core, fleetbase | `mysql:8.0`                                       | 127.0.0.1:3306 | Fleetbase MySQL (optional) |
| `cache`    | core, fleetbase | `redis:7.2-alpine`                                | 127.0.0.1:6379 | Cache + queues             |
| `mailhog`  | core            | `mailhog/mailhog:v1.0.1`                          | 1025, 8025     | Dev SMTP capture           |
| `valhalla` | routing         | `ghcr.io/gis-ops/docker-valhalla/valhalla:latest` | 127.0.0.1:8002 | Routing engine             |
| `proxy`    | proxy           | `nginx:1.27-alpine`                               | 127.0.0.1:8080 | Optional dev proxy         |

```bash
pnpm docker:up              # core profile (postgres, mysql, redis, mailhog)
pnpm docker:up:routing      # core + Valhalla on :8002
```

Fleetbase API/console services in this file are **commented out** — use the dedicated Fleetbase stack instead.

---

## Stack 2 — Fleetbase

**Files:** `apps/fleetbase/docker-compose.yml` + override + `infrastructure/docker/fleetbase.porterchain.override.yml`  
**Project name:** `porterchain-fleetbase`

See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for full service table. Key ports:

| Service  | Host port | Notes                          |
| -------- | --------- | ------------------------------ |
| httpd    | 8000      | Fleetbase API                  |
| console  | 4200      | Dispatch UI                    |
| database | 3307      | MySQL (avoids core stack 3306) |
| socket   | 38000     | SocketCluster WebSockets       |

```bash
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify
```

---

## Networks

| Network                | Stack     | Members                            |
| ---------------------- | --------- | ---------------------------------- |
| `porterchain-internal` | Core      | postgres, redis, mailhog, valhalla |
| `porterchain-data`     | Core      | postgres, mysql, redis             |
| `fleetbase-internal`   | Fleetbase | All Fleetbase containers           |

Porterchain API on the host reaches:

- PostgreSQL at `127.0.0.1:5432`
- Redis at `127.0.0.1:6379`
- Fleetbase API at `http://localhost:8000`
- Valhalla at `http://localhost:8002`

---

## Volumes (core stack)

| Volume           | Service  | Purpose           |
| ---------------- | -------- | ----------------- |
| `postgres-data`  | postgres | Porterchain DB    |
| `mysql-data`     | database | Fleetbase MySQL   |
| `redis-data`     | cache    | Redis AOF         |
| `valhalla-tiles` | valhalla | OSM routing tiles |

Fleetbase stack uses named volumes prefixed `porterchain-fleetbase-*` (see DOCKER_SETUP.md).

---

## Application Dockerfiles (production builds)

| Path                              | Base image         | Output              |
| --------------------------------- | ------------------ | ------------------- |
| `apps/api/Dockerfile`             | `python:3.13-slim` | Porterchain FastAPI |
| `website/Dockerfile`              | `node:24-alpine`   | Next.js standalone  |
| `apps/merchant-portal/Dockerfile` | `node:24-alpine`   | Next.js standalone  |
| `apps/admin/Dockerfile`           | `node:24-alpine`   | Next.js standalone  |
| `apps/driver-portal/Dockerfile`   | `node:24-alpine`   | Next.js standalone  |
| `apps/customer/Dockerfile`        | `node:24-alpine`   | Next.js standalone  |

Production deploy: `infrastructure/deploy/docker-compose.prod.yml` — Postgres, Redis, API + 5 portal images, Caddy TLS.

---

## Development workflow

```bash
# 1. Start data services
pnpm docker:up

# 2. Run migrations
pnpm db:migrate

# 3. Start API + worker on host
pnpm dev:api
pnpm dev:worker

# 4. Start frontends on host
pnpm dev:website      # :3000
pnpm dev:merchant     # :3001
pnpm dev:admin        # :3002
pnpm dev:driver       # :3003
pnpm dev:customer     # :3004

# 5. Optional: Fleetbase dispatch stack
pnpm docker:fleetbase:up

# 6. Optional: routing
pnpm docker:up:routing
```

---

## Health checks

Core stack services define health checks for postgres, mysql, redis, and valhalla. Fleetbase stack health is verified via `pnpm docker:fleetbase:verify`. See [SERVICE_STATUS.md](./SERVICE_STATUS.md) for last Fleetbase snapshot.

---

## Related documents

- [DOCKER_SETUP.md](./DOCKER_SETUP.md) — Fleetbase stack detail
- [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) — port map
- [infrastructure/deploy/README.md](./infrastructure/deploy/README.md) — production topology

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
