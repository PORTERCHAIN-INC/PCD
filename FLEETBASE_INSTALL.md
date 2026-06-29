# Fleetbase Installation — Porterchain Monorepo

**Version installed:** [Fleetbase v0.7.40](https://github.com/fleetbase/fleetbase/releases/tag/v0.7.40)  
**Location:** `apps/fleetbase/` (upstream clone — **no Porterchain modifications to Fleetbase source**)  
**Date:** June 29, 2026

---

## License verification

| Item               | Value                                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| License            | **GNU Affero General Public License v3.0 (AGPL-3.0)**                                                 |
| License file       | `apps/fleetbase/LICENSE.md`                                                                           |
| Commercial use     | Permitted for self-hosting; network copyleft applies to modifications                                 |
| Porterchain stance | Fleetbase runs as a **separate application**; Porterchain API bridges to it — no Fleetbase code forks |

Review `LICENSE.md` before production deployment. A commercial license is available from Fleetbase if AGPL obligations are not suitable.

---

## Prerequisites

| Requirement    | Version                                           |
| -------------- | ------------------------------------------------- |
| Docker Desktop | 20.10+                                            |
| Docker Compose | v2 (`docker compose`)                             |
| Git            | any recent                                        |
| RAM for Docker | ≥ 4 GB (8 GB recommended)                         |
| Disk           | ≥ 10 GB free                                      |
| Ports (host)   | `8000`, `4200`, `38000`, `3307` (MySQL host bind) |

**Port note:** Porterchain core MySQL uses `127.0.0.1:3306`. Fleetbase MySQL is bound to **`127.0.0.1:3307`** to avoid conflict.

---

## Repository layout

```
PCD/
├── apps/
│   ├── api/                 # Porterchain API (bridge to Fleetbase)
│   ├── admin/
│   ├── merchant-portal/
│   └── fleetbase/           # ← Official Fleetbase OSS clone (v0.7.40)
├── infrastructure/docker/
│   ├── fleetbase.porterchain.override.yml   # Porterchain-only overlay (ports, volumes)
│   └── scripts/
│       ├── fleetbase-install.sh
│       └── fleetbase-verify.sh
├── FLEETBASE_INSTALL.md     # this file
├── RUNBOOK.md
├── DOCKER_SETUP.md
└── SERVICE_STATUS.md
```

Porterchain **does not** embed Fleetbase UI in the website, merchant portal, or admin app. Dispatch staff use the Fleetbase Console at `http://localhost:4200`.

---

## Quick install (automated)

```bash
# From repo root — requires Docker Desktop running
pnpm docker:fleetbase:install
```

This script:

1. Clones Fleetbase `v0.7.40` into `apps/fleetbase` if missing
2. Verifies AGPL license file exists
3. Runs official `scripts/docker-install.sh --non-interactive` (creates `docker-compose.override.yml`, `api/.env`, console config)
4. Merges `infrastructure/docker/fleetbase.porterchain.override.yml`
5. Builds and starts all containers
6. Waits for MySQL health
7. Grants MySQL privileges for sandbox migrations
8. Runs `deploy.sh` (migrations, seeds, permissions)

---

## Manual install

```bash
git clone --depth 1 --branch v0.7.40 https://github.com/fleetbase/fleetbase.git apps/fleetbase
cd apps/fleetbase
bash scripts/docker-install.sh --non-interactive

cd ../..
docker compose \
  -f apps/fleetbase/docker-compose.yml \
  -f apps/fleetbase/docker-compose.override.yml \
  -f infrastructure/docker/fleetbase.porterchain.override.yml \
  up -d --build

# After MySQL is healthy:
pnpm docker:fleetbase:verify
```

---

## Post-install

| Service                        | URL                   |
| ------------------------------ | --------------------- |
| **API**                        | http://localhost:8000 |
| **Console (Dispatcher)**       | http://localhost:4200 |
| **SocketCluster (WebSockets)** | ws://localhost:38000  |
| **MySQL (host)**               | `127.0.0.1:3307`      |

1. Open **Console** → complete onboarding wizard (organization + admin user).
2. Copy organization/company UUID into Porterchain API env: `FLEETBASE_DEFAULT_COMPANY_UUID` / `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID`.
3. Set Porterchain API: `FLEETBASE_API_URL=http://localhost:8000`, `FLEETBASE_DISPATCH_BRIDGE=true`.

---

## Verify installation

```bash
pnpm docker:fleetbase:verify
```

Expected: all checks `PASS` (see `SERVICE_STATUS.md`).

---

## Upgrade (upstream)

```bash
cd apps/fleetbase
git fetch --tags
git checkout v0.7.40   # or newer stable tag after testing
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml pull
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml up -d
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -T application bash -c "./deploy.sh"
```

Always run `./deploy.sh` after upgrading per [Fleetbase docs](https://fleetbase.io/docs/platform/quickstart/running-locally).

---

## What Porterchain does NOT change

- No edits to Fleetbase PHP/Ember source
- No changes to website booking widget or retail flow
- No changes to merchant portal or admin app
- Fleetbase `docker-compose.yml` remains upstream; overlays use official `docker-compose.override.yml` + Porterchain `fleetbase.porterchain.override.yml`

---

## Troubleshooting

| Issue                        | Fix                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------- |
| Port 3306 in use             | Porterchain overlay binds Fleetbase MySQL to **3307**                        |
| Port 8000/4200/38000 in use  | Stop other Fleetbase stacks: `docker compose -p pc down` (legacy `PC/` repo) |
| `deploy.sh` sandbox DB error | Re-run install script (includes MySQL grant) or see RUNBOOK.md               |
| Docker daemon not running    | Start Docker Desktop, retry `pnpm docker:fleetbase:install`                  |

---

## Related documents

- [DOCKER_SETUP.md](./DOCKER_SETUP.md) — container reference
- [RUNBOOK.md](./RUNBOOK.md) — day-2 operations
- [SERVICE_STATUS.md](./SERVICE_STATUS.md) — verification snapshot
- [CONNECTIONS.md](./CONNECTIONS.md) — Porterchain ↔ Fleetbase bridge
