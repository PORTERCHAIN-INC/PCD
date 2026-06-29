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
              3. ssh droplet   → docker pull + docker run -p 80:3000
              4. healthcheck   → curl http://localhost:80
```

Currently the website (`website/Dockerfile`, Next.js standalone, port 3000) is the
deployed service. It is published on the droplet at port 80.

## One-time droplet setup

On a fresh Ubuntu droplet (`68.183.103.49`):

```bash
ssh root@68.183.103.49 'bash -s' < infrastructure/deploy/bootstrap-droplet.sh
```

This installs Docker, enables it, and opens ports 22/80/443.

Then ensure the deploy user can log in with the SSH key referenced by
`DEPLOY_SSH_KEY` (add the matching public key to `~/.ssh/authorized_keys`).

## Required GitHub repository secrets

Set these under **Settings → Secrets and variables → Actions → Secrets**:

| Secret                            | Description                                         |
| --------------------------------- | --------------------------------------------------- |
| `DEPLOY_HOST`                     | Droplet IP, e.g. `68.183.103.49`                    |
| `DEPLOY_USER`                     | SSH user (e.g. `root` or a `deploy` user)           |
| `DEPLOY_SSH_KEY`                  | **Private** SSH key (PEM) authorized on the droplet |
| `DEPLOY_PORT`                     | _(optional)_ SSH port, defaults to `22`             |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Google Maps key baked into the build                |

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
- **Rollback:** SSH to the droplet and run a previous image tag:
  ```bash
  docker run -d --name pcd-website --restart unless-stopped -p 80:3000 \
    ghcr.io/<owner>/pcd-website:<previous-sha>
  ```

## Notes

- GHCR package visibility: the first push creates a **private** package. The
  droplet authenticates with the workflow token at deploy time, so private is fine.
- Only the website is containerized today. The Porterchain API (`apps/api`,
  Python/FastAPI) and portals can be added as additional build+deploy steps once
  they have Dockerfiles.
