# Deployment (CI/CD)

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Porterchain production deployment uses GitHub Actions → GHCR → DigitalOcean droplet with Caddy TLS termination.

> **See also:** [DOCKER_SETUP.md](../../DOCKER_SETUP.md) · [PORT_CONFIGURATION.md](../../PORT_CONFIGURATION.md)

---

## Workflows

| Workflow   | File                           | Trigger                         | Purpose                              |
| ---------- | ------------------------------ | ------------------------------- | ------------------------------------ |
| **CI**     | `.github/workflows/ci.yml`     | push / PR to `main`             | Lint, format check, build            |
| **Deploy** | `.github/workflows/deploy.yml` | CI success on `main`, or manual | Build images → GHCR → droplet deploy |

Deploy runs only after CI passes on `main`, so broken code does not ship automatically.

---

## Pipeline Overview

```
push to main → CI (lint / format / build)
                 │  on success
                 ▼
            Deploy workflow
              1. docker build  (website, api, admin, merchant, driver, customer)
              2. push images   → ghcr.io/<owner>/pcd-*:<sha> + :latest
              3. scp manifests → docker-compose.prod.yml + Caddyfile → /opt/porterchain
              4. ssh droplet   → docker compose pull && up -d
              5. migrate       → repair_and_migrate.py inside pcd-api
              6. healthcheck   → API /health + Caddy :80 + smoke quotes
```

### Images Built

| Image          | Dockerfile                        | Service              |
| -------------- | --------------------------------- | -------------------- |
| `pcd-website`  | `website/Dockerfile`              | Marketing + booking  |
| `pcd-api`      | `apps/api/Dockerfile`             | FastAPI orchestrator |
| `pcd-admin`    | `apps/admin/Dockerfile`           | Admin portal         |
| `pcd-merchant` | `apps/merchant-portal/Dockerfile` | Merchant portal      |
| `pcd-driver`   | `apps/driver-portal/Dockerfile`   | Driver portal        |
| `pcd-customer` | `apps/customer/Dockerfile`        | Customer portal      |

**Not in prod compose (July 2026):** `apps/worker` — run worker separately or add to compose when background jobs are required in production.

---

## Runtime Architecture (Droplet)

```
Internet ──443──▶ Caddy (pcd-caddy)
                    ├─ porterchain.com         → website :3000
                    ├─ api.porterchain.com     → api :8001
                    ├─ admin.porterchain.com   → admin :3002
                    ├─ merchant.porterchain.com → merchant :3001
                    ├─ driver.porterchain.com → driver :3003
                    └─ customer.porterchain.com → customer :3004

Internal: postgres:16, redis:7.2 (Docker network `edge`)
```

- **Caddy** (`infrastructure/deploy/Caddyfile`) — TLS (Let's Encrypt), HTTP→HTTPS, `www`→apex, security headers.
- Portal/API containers are **not** published to the host — only Caddy exposes 80/443.
- Stack: `infrastructure/deploy/docker-compose.prod.yml` in `/opt/porterchain`.
- **PostgreSQL 16** and **Redis** run in-compose with persistent volumes.

---

## One-Time Droplet Setup

On a fresh Ubuntu droplet:

```bash
# 1. Install Docker + open firewall (22/80/443)
ssh root@<DROPLET_IP> 'bash -s' < infrastructure/deploy/bootstrap-droplet.sh

# 2. Security hardening: fail2ban, automatic updates, key-only SSH
ssh root@<DROPLET_IP> 'bash -s' < infrastructure/deploy/harden-droplet.sh
```

Ensure the deploy user can log in with the SSH key referenced by `DEPLOY_SSH_KEY`.

**DNS (required before first deploy):** `porterchain.com`, `www.porterchain.com`, `api.porterchain.com`, `admin.porterchain.com`, `merchant.porterchain.com`, `driver.porterchain.com`, `customer.porterchain.com` → droplet IP.

---

## Required GitHub Secrets

Settings → Secrets and variables → Actions → Secrets:

| Secret                            | Description                                 |
| --------------------------------- | ------------------------------------------- |
| `DEPLOY_HOST`                     | Droplet IP                                  |
| `DEPLOY_USER`                     | SSH user (`root` or `deploy`)               |
| `DEPLOY_SSH_KEY`                  | Private SSH key (PEM) authorized on droplet |
| `DEPLOY_PORT`                     | _(optional)_ SSH port, default `22`         |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Browser Maps key (build-time)               |
| `GOOGLE_MAPS_SERVER_API_KEY`      | Server-side Maps key for geocoding          |
| `POSTGRES_PASSWORD`               | PostgreSQL password for `porterchain` DB    |
| `CLERK_PUBLISHABLE_KEY`           | Clerk publishable key (`pk_live_…` in prod) |
| `CLERK_SECRET_KEY`                | Clerk secret key                            |
| `CLERK_JWKS_URL`                  | Clerk JWKS endpoint                         |
| `STRIPE_SECRET`                   | Stripe secret key                           |
| `STRIPE_WEBHOOK_SECRET`           | Stripe webhook signing secret               |
| `JWT_SECRET`                      | SSO token secret (`openssl rand -hex 32`)   |
| `FIREBASE_PROJECT_ID`             | _(optional)_ GCP Firebase project           |
| `FIREBASE_CREDENTIALS_JSON`       | _(optional)_ Service account JSON inline    |
| `FIREBASE_WEB_VAPID_KEY`          | _(optional)_ Web push VAPID key             |

**Repository variable:** `PORTERCHAIN_PUSH_ENABLED` — default `false` until Firebase secrets are set.

**Stripe webhook URL:** `https://porterchain.com/webhooks/stripe` (via Caddy → API)

**Clerk allowed origins:** all production portal hosts.

GHCR uses built-in `GITHUB_TOKEN` (no extra secret).

### Quick Setup (gh CLI)

```bash
gh secret set DEPLOY_HOST -b "<droplet-ip>"
gh secret set DEPLOY_USER -b "root"
gh secret set DEPLOY_SSH_KEY < ~/.ssh/porterchain_deploy
gh secret set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY -b "<your-key>"
gh secret set CLERK_PUBLISHABLE_KEY -b "pk_live_…"
gh secret set CLERK_SECRET_KEY -b "sk_live_…"
gh secret set CLERK_JWKS_URL -b "https://…/.well-known/jwks.json"
```

---

## Deploy-Time Migrations

After `docker compose up`, the workflow runs Alembic inside `pcd-api`:

```bash
docker exec -w /app/apps/api pcd-api python scripts/repair_and_migrate.py
```

Head revision: `n2o3p4q5r6s7` (13 revisions). See [apps/api/alembic/README.md](../../apps/api/alembic/README.md).

---

## Manual Deploy / Rollback

- **Manual deploy:** Actions → _Deploy_ → _Run workflow_
- **Rollback:** SSH to droplet and pin a previous image tag:

```bash
cd /opt/porterchain
export WEB_IMAGE=ghcr.io/<owner>/pcd-website:<previous-sha>
export API_IMAGE=ghcr.io/<owner>/pcd-api:<previous-sha>
# … other images …
docker compose -f docker-compose.prod.yml up -d
```

---

## Security Posture

| Control        | Status                                           |
| -------------- | ------------------------------------------------ |
| Firewall (UFW) | Default-deny; 22/80/443 only                     |
| TLS            | Let's Encrypt via Caddy; HSTS                    |
| Database       | PostgreSQL 16 in Docker (`postgres-data` volume) |
| Redis          | In-compose; not exposed to host                  |
| Payments       | `STRIPE_MOCK=false`; real Stripe Checkout        |
| Auth           | `CLERK_DEV_BYPASS=false`; Clerk JWT verification |
| SSH            | Key-only; fail2ban; unattended-upgrades          |
| Containers     | `no-new-privileges`; internal network only       |

Re-run `harden-droplet.sh` any time (idempotent).

---

## Notes

- GHCR packages are **private** by default; droplet authenticates at deploy time.
- Fleetbase is **not** in prod compose by default (`FLEETBASE_DISPATCH_BRIDGE=false`).
- Mobile apps (Expo) deploy via EAS separately — not part of this droplet stack.

---

## Governance

| Document                                         | Role              |
| ------------------------------------------------ | ----------------- |
| [masterrule.md](../../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
