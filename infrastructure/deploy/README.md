# PorterChain production deploy

SSOT for droplet CD. Secrets stores: [`docs/SECRETS_MAP.md`](../../docs/SECRETS_MAP.md) · upload helpers: [`SECRETS.md`](./SECRETS.md). Ops posture: [`RUNBOOK.md`](../../RUNBOOK.md).

## Local gate (required)

Do not run this pipeline on a change that has not been tested and built on the laptop. Order: test, then the same `next build` the image Dockerfiles run, then push, then CI, then Deploy. CI and Deploy build the pushed commit, not uncommitted files. Rule: [`.cursor/rules/local-before-production.mdc`](../../.cursor/rules/local-before-production.mdc).

## Pipeline

```
PR / push → main
  CI (+ Security + CodeQL)
       │ success on main
       ▼
  Deploy (plan → parallel builds → scoped rollout) → GHCR → droplet
```

| Workflow                | When                                | What                                                           |
| ----------------------- | ----------------------------------- | -------------------------------------------------------------- |
| `CI`                    | PR + push to `main`                 | Static gates, Admin Vitest, API Postgres tests                 |
| `Deploy`                | After green CI on `main`, or manual | Plan from `deploy-rules.json` → parallel GHCR builds → droplet |
| `Nightly E2E`           | Cron 11:00 UTC + manual             | D3 behavioral matrix (Postgres + Redis + Valhalla stub)        |
| `Security`              | PR + push to `main`                 | Bandit + Trivy                                                 |
| `CodeQL`                | PR + push + weekly                  | CodeQL analyze                                                 |
| `Set Public Ingest Key` | Manual                              | Ensure `PUBLIC_INGEST_API_KEY` in Doppler; roll `api` + `web`  |

Website-only: **Actions → Deploy → Run workflow → scope=`website`**. Do not use a separate workflow.

Git push from a laptop uses the deploy key documented in [`docs/GITHUB_SSH_KEYS.md`](../../docs/GITHUB_SSH_KEYS.md) — not Actions sync jobs.

## GitHub secrets / vars

| Name                                 | Required   | Role                                                                                                                                                                |
| ------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DEPLOY_HOST`                        | yes        | Droplet IP/hostname                                                                                                                                                 |
| `DEPLOY_USER`                        | yes        | SSH user                                                                                                                                                            |
| `DEPLOY_SSH_KEY`                     | yes        | Private key                                                                                                                                                         |
| `DEPLOY_PORT`                        | no         | Default `22`                                                                                                                                                        |
| `DOPPLER_TOKEN`                      | yes        | Service token for `pcd` / `prd` — used only on the **Actions runner** via [`.github/actions/stage-doppler-env`](../../.github/actions/stage-doppler-env/action.yml) |
| `CLERK_*` / `NEXT_PUBLIC_*`          | build-time | Portal/website image build-args                                                                                                                                     |
| `DOPPLER_PROJECT` / `DOPPLER_CONFIG` | vars       | Default `pcd` / `prd`                                                                                                                                               |
| `API_REPLICAS`                       | var        | Passed into recover script                                                                                                                                          |

Runtime secrets live in **Doppler**, not GitHub. `stage-doppler-env` downloads once, validates keys, then SCPs `doppler.env`. Never forward `DOPPLER_TOKEN` through appleboy SSH env.

## Images (GHCR)

| Image          | Dockerfile                        |
| -------------- | --------------------------------- |
| `pcd-api`      | `apps/api/Dockerfile`             |
| `pcd-website`  | `website/Dockerfile`              |
| `pcd-admin`    | `apps/admin/Dockerfile`           |
| `pcd-merchant` | `apps/merchant-portal/Dockerfile` |
| `pcd-driver`   | `apps/driver-portal/Dockerfile`   |
| `pcd-customer` | `apps/customer/Dockerfile`        |

Tags: `:latest`, `:<git-sha>`, and `:cid-<16>` (content digest of that image's inputs). If `cid-*` already exists in GHCR, Deploy retags it instead of rebuilding.

Org stays on **GitHub Free** (no Team). CI/Deploy/Packages work without Team; private branch protection does not.

## Droplet layout

Host path: `/opt/porterchain`

- `docker-compose.prod.yml`, `Caddyfile`, SSO HTML, Valhalla helpers
- `doppler.yaml` + staged `doppler.env` → `sync-secrets.sh` → `.env`
- Compose services: `api`, `web`, portals, `worker`, `caddy`, Postgres, Redis, Valhalla, …

Bootstrap / harden: `bootstrap-droplet.sh`, `harden-droplet.sh`.

## Deploy scopes

**SSOT:** [`deploy-rules.json`](./deploy-rules.json). Resolver: `python3 scripts/resolve_deploy_plan.py`. Guard: `pnpm validate:deploy-plan`. Cursor rule: [`.cursor/rules/deploy-scopes.mdc`](../../.cursor/rules/deploy-scopes.mdc). Do not add images or globs only in `deploy.yml`.

| Scope                           | Builds                                               | Droplet action                     | Smoke                               |
| ------------------------------- | ---------------------------------------------------- | ---------------------------------- | ----------------------------------- |
| `auto` (CI default)             | Union of images whose `input_globs` match the commit | Same as resolved scope             | Same as resolved scope              |
| `full`                          | All six images                                       | Pull all, migrate, recover stack   | API + portals + quotes              |
| `portals`                       | admin + merchant + driver + customer                 | Recreate those four                | Admin + merchant sign-in            |
| `website`                       | Website only                                         | Recreate `web`                     | Site + sitemap                      |
| `api`                           | API image                                            | Recreate `api` + `worker`, migrate | `/health`                           |
| `merchant`                      | Merchant portal                                      | Recreate `merchant`                | `/sign-in` + `/shopify?connected=1` |
| `admin` / `driver` / `customer` | That portal only                                     | Recreate that service              | —                                   |
| `selected` (auto only)          | Mixed set, e.g. api + merchant                       | Recreate those services            | Per pinned image                    |
| `none`                          | Nothing                                              | Skip                               | —                                   |

**Auto rules:** one app path → that image; two+ portals → `portals`; mixed flavors (api + merchant) → `selected` (not full); `packages/*` / deploy infra / lockfile / unknown paths → `full`; docs-only → `none`.

Manual: **Actions → Deploy → Run workflow → scope**. Use `merchant` for Shopify UI-only fixes (~one image).

## Rolling deploy / rollback

1. Find last good SHA in GHCR or Actions run.
2. On droplet: set image env vars to the prior SHA tags (e.g. `API_IMAGE=ghcr.io/<owner>/pcd-api:<sha>`), then:

```bash
cd /opt/porterchain
docker compose -f docker-compose.prod.yml pull
bash scripts/recover-prod-stack.sh
```

3. Or re-run **Deploy** on that commit (`workflow_dispatch`).

Migrations: full deploy runs `repair_and_migrate.py` inside `api` before smoke. Website-only skips migrations.

## Local / break-glass

```bash
# Dry-run secrets sync (needs DOPPLER_TOKEN)
DOPPLER_TOKEN=… bash infrastructure/deploy/sync-secrets.sh /tmp/porterchain-test

# Upload helpers — see SECRETS.md
bash infrastructure/deploy/scripts/upload-ingest-to-doppler.sh
```
