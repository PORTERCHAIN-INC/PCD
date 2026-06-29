# Porterchain + Fleetbase — Docker Setup

**Compose project name:** `porterchain-fleetbase`  
**Upstream compose:** `apps/fleetbase/docker-compose.yml` (Fleetbase v0.7.40)  
**Porterchain overlay:** `infrastructure/docker/fleetbase.porterchain.override.yml`

---

## Compose file merge order

Docker Compose merges files left-to-right (later wins):

```bash
docker compose \
  -f apps/fleetbase/docker-compose.yml \
  -f apps/fleetbase/docker-compose.override.yml \
  -f infrastructure/docker/fleetbase.porterchain.override.yml \
  <command>
```

| File                                 | Owner               | Purpose                                                        |
| ------------------------------------ | ------------------- | -------------------------------------------------------------- |
| `docker-compose.yml`                 | Fleetbase upstream  | Base services                                                  |
| `docker-compose.override.yml`        | Fleetbase installer | Secrets, APP_KEY, DB creds, SocketCluster origins              |
| `fleetbase.porterchain.override.yml` | Porterchain         | Host port 3307, named volumes, container names, bridge network |

---

## Services

| Service         | Container name                        | Image / build                         | Host ports            | Restart          | Health check               |
| --------------- | ------------------------------------- | ------------------------------------- | --------------------- | ---------------- | -------------------------- |
| **database**    | `porterchain-fleetbase-mysql`         | `mysql:8.0-oracle`                    | `127.0.0.1:3307→3306` | `unless-stopped` | `mysqladmin ping`          |
| **cache**       | `porterchain-fleetbase-redis`         | `redis:4-alpine`                      | internal only         | `unless-stopped` | `redis-cli ping`           |
| **socket**      | `porterchain-fleetbase-socketcluster` | `socketcluster/socketcluster:v17.4.0` | `38000→8000`          | `unless-stopped` | —                          |
| **queue**       | `porterchain-fleetbase-queue`         | `fleetbase/fleetbase-api:latest`      | internal              | `unless-stopped` | `php artisan queue:status` |
| **scheduler**   | `porterchain-fleetbase-scheduler`     | `fleetbase/fleetbase-api:latest`      | internal              | `unless-stopped` | —                          |
| **application** | `porterchain-fleetbase-application`   | `fleetbase/fleetbase-api:latest`      | internal              | `unless-stopped` | image default              |
| **httpd**       | `porterchain-fleetbase-httpd`         | build `docker/httpd/Dockerfile`       | `8000→80`             | `unless-stopped` | —                          |
| **console**     | `porterchain-fleetbase-console`       | build `console/Dockerfile`            | `4200→4200`           | `unless-stopped` | —                          |

### Service roles

| Service         | Role                                              |
| --------------- | ------------------------------------------------- |
| **database**    | MySQL 8 — primary + sandbox schemas               |
| **cache**       | Redis — cache, sessions, queue backend            |
| **socket**      | SocketCluster — real-time WebSockets / broadcasts |
| **queue**       | Laravel `queue:work` — async jobs                 |
| **scheduler**   | `go-crond` — cron / scheduled tasks               |
| **application** | Laravel API (Fleetbase)                           |
| **httpd**       | Nginx reverse proxy → API                         |
| **console**     | Ember.js dispatcher / ops UI                      |

---

## Networks

| Network                                    | Type                | Purpose                       |
| ------------------------------------------ | ------------------- | ----------------------------- |
| `porterchain-fleetbase_fleetbase-internal` | bridge              | All Fleetbase containers      |
| `porterchain_porterchain-internal`         | external (optional) | Future cross-stack API bridge |

Fleetbase containers communicate on `fleetbase-internal`. Porterchain API on the host reaches Fleetbase via `http://localhost:8000`.

---

## Volumes (named)

| Volume                              | Mount                           | Purpose                                   |
| ----------------------------------- | ------------------------------- | ----------------------------------------- |
| `porterchain-fleetbase-mysql-data`  | `/var/lib/mysql`                | MySQL data (persistent)                   |
| `porterchain-fleetbase-redis-data`  | `/data`                         | Redis AOF                                 |
| `porterchain-fleetbase-api-storage` | `/fleetbase/api/storage/app`    | Uploaded files                            |
| bind                                | `apps/fleetbase/api/.env`       | Laravel environment (installer-generated) |
| bind                                | `console/fleetbase.config.json` | Console API/WS config                     |

---

## Porterchain core stack (separate compose)

File: `infrastructure/docker/docker-compose.yml`  
Project: `porterchain`

| Service  | Profile         | Ports      |
| -------- | --------------- | ---------- |
| postgres | core            | 5432       |
| mysql    | core, fleetbase | 3306       |
| redis    | core, fleetbase | 6379       |
| mailhog  | core            | 1025, 8025 |
| valhalla | routing         | 8002       |
| proxy    | proxy           | 8080       |

Run Porterchain data services:

```bash
pnpm docker:up              # core (postgres, mysql, redis, mailhog)
pnpm docker:up:routing      # + Valhalla on :8002
```

Fleetbase and Porterchain stacks are **independent** compose projects.

---

## Routing engines

| Engine       | Config                         | Default                                                                   |
| ------------ | ------------------------------ | ------------------------------------------------------------------------- |
| **OSRM**     | `OSRM_HOST` in application env | `https://router.project-osrm.org` (public)                                |
| **Valhalla** | `VALHALLA_BASE_URL`            | `http://host.docker.internal:8002` when Porterchain routing profile is up |

Verify:

```bash
# OSRM
curl -s "https://router.project-osrm.org/route/v1/driving/-79.38,43.65;-79.40,43.66?overview=false" | head -c 80

# Valhalla (requires pnpm docker:up:routing)
curl -s http://127.0.0.1:8002/status
```

---

## Environment files

| File                                         | Purpose                                                      |
| -------------------------------------------- | ------------------------------------------------------------ |
| `apps/fleetbase/docker-compose.override.yml` | Auto-generated by Fleetbase installer — **contains secrets** |
| `apps/fleetbase/api/.env`                    | Laravel app config (mounted into application container)      |
| `env/fleetbase.env.example`                  | Porterchain reference template for bridge variables          |
| `infrastructure/docker/.env`                 | Porterchain core Docker secrets (gitignored)                 |

**Never commit** `docker-compose.override.yml` or `api/.env` with production secrets.

---

## Commands reference

```bash
pnpm docker:fleetbase:install   # Full install + deploy
pnpm docker:fleetbase:up        # Start stack
pnpm docker:fleetbase:down      # Stop stack
pnpm docker:fleetbase:logs      # Follow logs
pnpm docker:fleetbase:verify    # Health checks

# Deploy after config change
cd apps/fleetbase && docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -T application bash -c "./deploy.sh"
```

---

## Authentication

| Surface              | Method                                                             |
| -------------------- | ------------------------------------------------------------------ |
| Fleetbase Console    | Fleetbase onboarding wizard → org admin account                    |
| Fleetbase API        | Sanctum / session tokens (internal)                                |
| Porterchain bridge   | `PORTERCHAIN_DISPATCHER_API_KEY` (see `env/fleetbase.env.example`) |
| Porterchain web apps | Clerk (separate — not Fleetbase)                                   |

Driver mobile app authenticates via Porterchain JWT, not Fleetbase console.

---

## Storage

Default install uses **local disk** (`FILESYSTEM_DRIVER=public`) suitable for development. Production: configure S3/GCS via `docker-compose.override.yml` per [Fleetbase docs](https://fleetbase.io/docs).

---

## Health checks summary

All containers should be `running`. MySQL, Redis, queue report `healthy` when probed. Run:

```bash
pnpm docker:fleetbase:verify
```

See [SERVICE_STATUS.md](./SERVICE_STATUS.md) for last verified snapshot.
