# Deployment (CI/CD)

Porterchain uses two GitHub Actions workflows:

| Workflow   | File                           | Trigger                                | Purpose                                                |
| ---------- | ------------------------------ | -------------------------------------- | ------------------------------------------------------ |
| **CI**     | `.github/workflows/ci.yml`     | push / PR to `main`                    | Lint, format check, build (quality gate)               |
| **Deploy** | `.github/workflows/deploy.yml` | after CI succeeds on `main`, or manual | Build website image → push to GHCR → deploy to droplet |

The Deploy workflow only runs once CI passes on `main`, so broken code never ships.

## Pipeline overview

```
push to main → CI (lint / format / build)
                 │  on success
                 ▼
            Deploy workflow
              1. docker build  (website/Dockerfile)
              2. push image    → ghcr.io/<owner>/pcd-website:<sha> + :latest
              3. scp manifests → docker-compose.prod.yml + Caddyfile → /opt/porterchain
              4. ssh droplet   → docker compose pull && up -d
              5. healthcheck   → curl http://localhost:80
```

### Runtime architecture (on the droplet)

```
Internet ──443/tcp──▶ Caddy (pcd-caddy)  ──http──▶ website (pcd-website:3000)
          ──80/tcp──▶ Caddy → 308 redirect to HTTPS
```

- **Caddy** (`infrastructure/deploy/Caddyfile`) terminates TLS with automatic
  Let's Encrypt certificates for `porterchain.com` + `www.porterchain.com`,
  forces HTTP→HTTPS, redirects `www`→apex, and sets security headers
  (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`).
- The **website** container (`website/Dockerfile`, Next.js standalone) listens on
  `3000` and is **not** published to the host — only Caddy is internet-facing.
- Both run via `infrastructure/deploy/docker-compose.prod.yml` in `/opt/porterchain`.
  Caddy's certs/state persist in the `caddy-data` / `caddy-config` volumes.

## One-time droplet setup

On a fresh Ubuntu droplet (`68.183.103.49`):

```bash
# 1. Install Docker + open the firewall (22/80/443)
ssh root@68.183.103.49 'bash -s' < infrastructure/deploy/bootstrap-droplet.sh

# 2. Security hardening: fail2ban, automatic updates, key-only SSH
ssh root@68.183.103.49 'bash -s' < infrastructure/deploy/harden-droplet.sh
```

Then ensure the deploy user can log in with the SSH key referenced by
`DEPLOY_SSH_KEY` (add the matching public key to `~/.ssh/authorized_keys`).

> **DNS:** `porterchain.com` and `www.porterchain.com` must resolve to the droplet
> IP before the first deploy, otherwise Let's Encrypt cannot issue certificates.

## Required GitHub repository secrets

Set these under **Settings → Secrets and variables → Actions → Secrets**:

| Secret                            | Description                                                                              |
| --------------------------------- | ---------------------------------------------------------------------------------------- |
| `DEPLOY_HOST`                     | Droplet IP, e.g. `68.183.103.49`                                                         |
| `DEPLOY_USER`                     | SSH user (e.g. `root` or a `deploy` user)                                                |
| `DEPLOY_SSH_KEY`                  | **Private** SSH key (PEM) authorized on the droplet                                      |
| `DEPLOY_PORT`                     | _(optional)_ SSH port, defaults to `22`                                                  |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Browser Maps key baked into the build (referrer-restricted)                              |
| `GOOGLE_MAPS_SERVER_API_KEY`      | **Server-side** Maps key (no referrer restriction) for `/api/quote` geocoding at runtime |

Optional **Variables** (Settings → Variables):

| Variable               | Default                   |
| ---------------------- | ------------------------- |
| `NEXT_PUBLIC_SITE_URL` | `https://porterchain.com` |

GHCR authentication uses the built-in `GITHUB_TOKEN` (no extra secret needed).

### Quick setup with the GitHub CLI

```bash
gh secret set DEPLOY_HOST -b "68.183.103.49"
gh secret set DEPLOY_USER -b "root"
gh secret set DEPLOY_SSH_KEY < ~/.ssh/porterchain_deploy   # private key file
gh secret set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY -b "<your-key>"
```

## Manual deploy / rollback

- **Manual deploy:** Actions → _Deploy_ → _Run workflow_.
- **Rollback:** SSH to the droplet and pin a previous image tag:
  ```bash
  cd /opt/porterchain
  export WEB_IMAGE=ghcr.io/<owner>/pcd-website:<previous-sha>
  docker compose -f docker-compose.prod.yml up -d
  ```

## Security posture

- **Firewall (UFW):** default-deny inbound; only `22/80/443` open.
- **TLS:** Let's Encrypt via Caddy, auto-renewed; HSTS with `preload`.
- **SSH:** key-only (`PasswordAuthentication no`, root login key-only).
- **fail2ban:** bans IPs after repeated failed SSH logins.
- **unattended-upgrades:** automatic security patches.
- **Containers:** run with `no-new-privileges`; website not exposed to host.

Re-run `harden-droplet.sh` any time to reassert these settings (idempotent).

## Notes

- GHCR package visibility: the first push creates a **private** package. The
  droplet authenticates with the workflow token at deploy time, so private is fine.
- Only the website is containerized today. The Porterchain API (`apps/api`,
  Python/FastAPI) and portals can be added as additional build+deploy steps once
  they have Dockerfiles.
