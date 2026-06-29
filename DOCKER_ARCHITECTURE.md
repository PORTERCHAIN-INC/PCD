# Porterchain — Docker Architecture

**Document version:** 1.0  
**Date:** June 29, 2026  
**Status:** Target specification — **no Docker files exist in PCD repo today**

---

## Overview

Porterchain local and staging environments should run as a **Docker Compose stack** with isolated networks, named volumes, and health checks. Production may use the same images on Kubernetes or DigitalOcean App Platform.

Source references: `details.md` (service hostnames `database`, `cache`, `valhalla`), `CONNECTIONS.md`, `PORT_CONFIGURATION.md`.

---

## Target `docker-compose.yml` services

```
infrastructure/docker/docker-compose.yml
```

### Service catalog

| Service | Image | Container name | Host port | Internal port |
|---------|-------|----------------|-----------|---------------|
| `database` | `mysql:8.0` | `porterchain-mysql` | 3306 | 3306 |
| `cache` | `redis:7.2-alpine` | `porterchain-redis` | 6379 | 6379 |
| `valhalla` | `ghcr.io/gis-ops/docker-valhalla/valhalla:latest` | `porterchain-valhalla` | 8002 | 8002 |
| `fleetbase-api` | `fleetbase/api:latest` (or custom build) | `porterchain-fleetbase-api` | 8000 | 8000 |
| `fleetbase-console` | `fleetbase/console:latest` | `porterchain-console` | 4200 | 4200 |
| `porterchain-api` | Custom FastAPI Dockerfile | `porterchain-api` | 8001 | 8000 |
| `nginx` | `nginx:1.27-alpine` | `porterchain-proxy` | 80, 443 | 80 |

### Optional services

| Service | Image | Purpose |
|---------|-------|---------|
| `mailhog` | `mailhog/mailhog` | Local SMTP capture (dev) |
| `minio` | `minio/minio` | S3-compatible local storage |
| `osrm` | `osrm/osrm-backend` | Self-hosted OSRM (if not using public) |

---

## Networks

```yaml
networks:
  porterchain-internal:
    driver: bridge
    internal: false  # valhalla needs tile downloads on first run

  porterchain-data:
    driver: bridge
    internal: true   # database + redis only
```

| Network | Members |
|---------|---------|
| `porterchain-internal` | All application containers |
| `porterchain-data` | `database`, `cache` only |

**Rule:** Frontend apps (website, merchant portal) run on host via `pnpm dev` in development, not in Docker — unless using a `website` dev container.

---

## Volumes

| Volume name | Mount point | Service | Purpose |
|-------------|-------------|---------|---------|
| `mysql-data` | `/var/lib/mysql` | `database` | Persistent Fleetbase DB |
| `redis-data` | `/data` | `cache` | Redis AOF persistence |
| `valhalla-tiles` | `/custom_files` | `valhalla` | OSM tiles (large; ~GB for Ontario) |
| `fleetbase-storage` | `/fleetbase/api/storage` | `fleetbase-api` | Uploads, Firebase creds |
| `api-storage` | `/app/storage` | `porterchain-api` | Porterchain uploads |

```yaml
volumes:
  mysql-data:
  redis-data:
  valhalla-tiles:
  fleetbase-storage:
  api-storage:
```

---

## Environment injection

Each service loads from layered env files:

```
infrastructure/docker/.env              # Secrets (gitignored)
infrastructure/docker/.env.example    # Template
apps/api/.env                         # API-specific (mounted read-only)
```

Docker Compose `env_file` + `environment` overrides for hostnames:

```yaml
environment:
  DB_HOST: database
  REDIS_HOST: cache
  VALHALLA_BASE_URI: http://valhalla:8002
```

---

## Restart policies

| Service | Policy | Reason |
|---------|--------|--------|
| `database` | `unless-stopped` | Data persistence |
| `cache` | `unless-stopped` | Queue dependency |
| `valhalla` | `unless-stopped` | Routing dependency |
| `fleetbase-api` | `unless-stopped` | Core dispatch |
| `fleetbase-console` | `unless-stopped` | Admin UI |
| `porterchain-api` | `unless-stopped` | Core API |
| `nginx` | `unless-stopped` | Entry point |
| `mailhog` | `no` | Dev only |

---

## Health checks

```yaml
# database
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s

# cache
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 3s
  retries: 5

# porterchain-api
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 20s

# valhalla
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8002/status"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s  # tile build is slow on first run
```

**Dependency order:**
1. `database` + `cache` (healthy)
2. `fleetbase-api` (depends on database, cache)
3. `porterchain-api` (depends on database, cache, fleetbase-api)
4. `valhalla` (can start in parallel; routing degrades if down)
5. `fleetbase-console` (depends on fleetbase-api)
6. `nginx`

---

## Scaling (production)

| Service | Scaling strategy |
|---------|------------------|
| `porterchain-api` | Horizontal — stateless; scale on CPU/latency |
| `fleetbase-api` | Horizontal with shared MySQL + Redis |
| `fleetbase-console` | Static assets; CDN or single instance |
| `database` | Vertical + read replicas (MySQL) |
| `cache` | Redis Sentinel or managed Redis |
| `valhalla` | Single instance per region (tile-local) |
| `nginx` / Traefik | Multiple instances behind LB |

### Worker processes

Fleetbase queue workers should run as separate containers:

```yaml
fleetbase-worker:
  image: fleetbase/api:latest
  command: php artisan queue:work
  depends_on:
    cache:
      condition: service_healthy
    database:
      condition: service_healthy
  deploy:
    replicas: 2
```

---

## Dockerfile targets (to create)

| Path | Base image | Output |
|------|------------|--------|
| `apps/api/Dockerfile` | `python:3.12-slim` | Porterchain FastAPI |
| `apps/website/Dockerfile` | `node:20-alpine` | Next.js standalone |
| `apps/merchant-portal/Dockerfile` | `node:20-alpine` | Next.js standalone |
| `infrastructure/docker/fleetbase/Dockerfile` | Fleetbase upstream | Custom branding |

### Next.js standalone pattern

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Traefik alternative

For Docker-native routing without manual Nginx config:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api.rule=Host(`api.localhost`)"
  - "traefik.http.services.api.loadbalancer.server.port=8000"
```

| Host | Backend |
|------|---------|
| `localhost` | website :3000 (host) |
| `portal.localhost` | merchant :3001 |
| `console.localhost` | fleetbase-console :4200 |
| `api.localhost` | nginx → porterchain-api + fleetbase |

---

## Development workflow

```bash
# Start infrastructure only
docker compose -f infrastructure/docker/docker-compose.yml up -d database cache valhalla fleetbase-api

# Run frontends on host (hot reload)
pnpm dev:website      # :3000
pnpm dev:merchant       # :3001
pnpm dev:api            # :8001

# Full stack
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

---

## Current gap in PCD repo

| Item | Status |
|------|--------|
| `docker-compose.yml` | **Missing** |
| `Dockerfile` | **Missing** |
| `.dockerignore` | **Missing** |
| CI image build | **Missing** |

**Next step:** Create `infrastructure/docker/` per this specification when monorepo is consolidated.

---

*This is a target architecture document. No containers are defined in the PCD repository as of June 2026.*
