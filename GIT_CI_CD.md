# PorterChain (PCD) — Git CI/CD Pipeline

**Author:** PorterChain coding agent
**Date:** 2026-08-09
**Basis:** Live reading of `.github/workflows/*`, `.github/dependabot.yml`, `.husky/`, `package.json` validators, `infrastructure/deploy/*`, and git remotes.
**Canonical reference:** [infrastructure/deploy/README.md](infrastructure/deploy/README.md) · [docs/SECRETS_MAP.md](docs/SECRETS_MAP.md) · [RUNBOOK.md](RUNBOOK.md)

---

## 1. Where the repo lives (git remotes)

| Remote        | URL                                        | Role                       |
| ------------- | ------------------------------------------ | -------------------------- |
| `origin`      | `https://github.com/porterchain/PCD.git`   | Primary (production)       |
| `portrxpress` | `git@github.com:portrxpress/PCD.git` (SSH) | Secondary / staging mirror |

Branches observed: `main` (default), `feature/crm` (current work branch). CI and deploy trigger on `main` / `master` only.

---

## 2. Pipeline at a glance

```
git push / PR → main
      │
      ▼
┌────────────────────────────────────────────────────────────────┐
│ 1. CI (ci.yml)         — lint · format · build · contract gates │
│ 2. Security (security.yml) — Bandit + Trivy container scans     │
│ 3. CodeQL (codeql.yml) — JS/TS + Python semantic analysis       │
└───────────────────────────────┬────────────────────────────────┘
                                │ on CI success on main
                                ▼
┌────────────────────────────────────────────────────────────────┐
│ 4. Deploy (deploy.yml)     — build 6 images → GHCR → droplet    │
│ 5. Migrations + health + smoke — Alembic, /health, quote POST   │
└────────────────────────────────────────────────────────────────┘
```

**Deploy is gated on CI success** (`workflow_run: workflows: [CI] → completed → success`). Broken code cannot ship automatically. Manual dispatch (`workflow_dispatch`) bypasses the gate intentionally.

Plus, independently:

- **Nightly E2E** (`nightly-e2e.yml`) — scheduled D3 behavioral matrix at 06:00 ET, with Postgres 18 + Redis 8.8 + a GTA Valhalla CI stub.
- **Deploy Website** (`deploy-website.yml`) — website-only hotfix path via manual dispatch.
- **Set Public Ingest Key** (`set-public-ingest-key.yml`) — one-shot ops for the CRM-lead ingestion key in Doppler.
- **Dependabot** — weekly dependency PRs with a frozen frontend list.

---

## 3. Workflow inventory

| Workflow                  | File                                          | Triggers                             | Purpose                                                           |
| ------------------------- | --------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------- |
| **CI**                    | `.github/workflows/ci.yml`                    | push / PR to `main`, `master`        | Full pre-deploy gate (2 jobs)                                     |
| **Security**              | `.github/workflows/security.yml`              | push / PR to `main`, `master`        | Bandit (Python) + Trivy (api, website images)                     |
| **CodeQL**                | `.github/workflows/codeql.yml`                | push / PR + weekly cron              | JS/TS + Python analysis (`security-and-quality`; upload disabled) |
| **Deploy**                | `.github/workflows/deploy.yml`                | CI success on `main`; manual         | Build 6 images → GHCR → droplet roll + migrate + smoke            |
| **Deploy Website**        | `.github/workflows/deploy-website.yml`        | manual only                          | Website-only image roll on droplet                                |
| **Nightly E2E**           | `.github/workflows/nightly-e2e.yml`           | cron `0 11 * * *` (06:00 ET); manual | D3 E2E matrix with full services                                  |
| **Set Public Ingest Key** | `.github/workflows/set-public-ingest-key.yml` | manual                               | Ensure `PUBLIC_INGEST_API_KEY` in Doppler + roll api/web          |

All workflows use `concurrency` groups (`ci-${{ github.workflow }}-${{ github.ref }}` etc.) so overlapping runs cancel/queue predictably — deploy groups use `cancel-in-progress: false` (deploys must serialize).

---

## 4. CI job — `ci.yml`

Two jobs on `ubuntu-24.04`:

### Job 1: `website` (monorepo static gates)

Setup: `actions/checkout@v7` → `pnpm/action-setup@v6` (pnpm 11.10.0) → `actions/setup-node@v6` (from `.nvmrc`, pnpm cache) → `pnpm install --frozen-lockfile` → Python 3.14.6 + `httpx`/`PyYAML`.

**~40 validation stages** wired to `package.json` `validate:*` scripts — this is the "CI as architecture enforcement" culture:

| Gate                                                                                                        | What it enforces                                                                    |
| ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `validate:lockfiles`                                                                                        | Lockfile freshness (DD-40)                                                          |
| `pnpm lint` / `format:check`                                                                                | ESLint + Prettier                                                                   |
| `validate:d2`                                                                                               | D2 engine/import guard (§0.3.10) — includes the Fleetbase engine import boundary    |
| `validate:d3`                                                                                               | D3 Phase 1 matrix (ENG-G3)                                                          |
| `validate:pagination`                                                                                       | List pagination everywhere (§2.5.6)                                                 |
| `validate:router-audit`                                                                                     | **Routers are thin** — no business logic in routers (§3.1.1)                        |
| `validate:architecture`                                                                                     | Boundaries, model ownership, stateless API, DB pool, Fleetbase sync SLO             |
| `validate:golden-rules`                                                                                     | Golden rules + execution metrics + engineering gates                                |
| `validate:observability`                                                                                    | Sentry/Prometheus + security headers                                                |
| `validate:notifications-billing`                                                                            | Notification & billing depth                                                        |
| `validate:enterprise-security` / `-identity`                                                                | §11 posture                                                                         |
| `validate:doc-governance` + `phase2-scaffold`                                                               | One-canonical-doc policy, Alembic head                                              |
| `validate:investor-monopoly` + `integration-adapter`                                                        | Investor/RBAC + integrations matrix                                                 |
| `validate:enterprise-narrative`                                                                             | Enterprise SIG + TAM narrative                                                      |
| `validate:pod-media` + `mobile-appendix`                                                                    | POD + mobile docs                                                                   |
| `validate:mobile-smoke` + `mobile-design`                                                                   | Maestro smoke structure, design parity                                              |
| `validate:portal-ux` / `admin-tablet` / `booking-a11y`                                                      | Empty states, tablet ops, a11y                                                      |
| `validate:tracking-maps`                                                                                    | Maps on retail surfaces                                                             |
| `validate:design`                                                                                           | Copy ban-list, i18n parity, no-false-AI-marketing                                   |
| `validate:developer-portal` / `oauth`                                                                       | Dev portal + OAuth router                                                           |
| `validate:product-vision` / `ai-governance` / `category-positioning`                                        | Vision + AI + positioning                                                           |
| `validate:construction-site-access` / `liftgate-pricing` / `vertical-onboarding` / `medical-food-verticals` | Moat verticals (§8)                                                                 |
| `validate:integration-marketplace` / `phase2-flags`                                                         | Marketplace + feature flags                                                         |
| **`pnpm build`**                                                                                            | Builds all Next.js portals (with CI-placeholder env keys, Clerk-off-safe prerender) |

### Job 2: `api-postgres` (real DB tests)

Runs `postgres:18-alpine3.24` as a GitHub service container, then:

1. Install `requirements.txt` + pytest
2. **Test-count floor**: ≥ 20 `test_*.py` files (ENG-G1)
3. **Alembic `upgrade head`** against the service Postgres
4. **pytest** with coverage (`--cov=porterchain_api`) on the full `tests/` suite
5. **Coverage floor** via `verify_service_coverage.py`
6. **Test regression guard** via `verify_test_regression.py`
7. **Module validation** `validate_postgres_modules.py`

---

## 5. Security workflows

### `security.yml`

- **Bandit** (`-ll`, `bandit.yaml`) on `apps/api/src/porterchain_api` — writes a JSON report, `|| true` so the scan always completes but the `-ll` run still fails on findings.
- **Trivy** matrix: builds `api` and `website` Docker images, scans with `trivy-action@v0.36.0`, `exit-code: 1`, `ignore-unfixed: true`, severity **CRITICAL/HIGH**, honors `.trivyignore`. Uses `ci-placeholder-key`/`ci-placeholder` build args so images build without real secrets.

### `codeql.yml`

Weekly (`0 6 * * 1`) + push/PR. Matrix: `javascript-typescript`, `python`. Queries `security-and-quality`. **`upload: false`** — findings are not uploaded because the repo lacks GitHub Advanced Security / code scanning enabled; the job is a smoke analysis only.

---

## 6. Deploy workflow — `deploy.yml`

The meat of the pipeline. Single `deploy` job on `ubuntu-24.04`.

### Flow

1. **Secret gate**: if `DEPLOY_HOST` is unset → skip with a notice (safe for forks).
2. **Resolve SHA**: uses the CI head SHA (not the deploy's own) for consistency.
3. **Build & push 6 images to GHCR** (`docker/build-push-action@v6`, GHA layer cache):
   - `pcd-api` (`apps/api/Dockerfile`)
   - `pcd-website` (`website/Dockerfile`)
   - `pcd-admin` (`apps/admin/Dockerfile`)
   - `pcd-merchant` (`apps/merchant-portal/Dockerfile`)
   - `pcd-driver` (`apps/driver-portal/Dockerfile`)
   - `pcd-customer` (`apps/customer/Dockerfile`)
   - Tagged **both** `:latest` and `:<full-sha>` (rollback anchors).
   - Each portal bakes public build args: Clerk publishable key (with legacy fallback), Google Maps key, Sentry DSN, portal URLs, Zoho SalesIQ, GA, site URL.
4. **Ship manifests** via `appleboy/scp-action` → `/opt/porterchain` (compose, Caddyfile, sync-secrets.sh, verify/recover scripts, `doppler.yaml`).
5. **Runtime secrets** come from **Doppler** (`DOPPLER_TOKEN` required; project `pcd`, config `prd`). `sync-secrets.sh` writes `/opt/porterchain/.env` with `umask 077`.
6. **Droplet roll** (`appleboy/ssh-action`):
   - `docker login ghcr.io` (GITHUB_TOKEN)
   - Export image tags as env (`WEB_IMAGE`, `API_IMAGE`, …)
   - `docker compose pull` → `bash scripts/recover-prod-stack.sh`
     - Recover data plane first (`postgres redis valhalla`, no force-recreate)
     - Then app tier `--force-recreate --pull missing --scale api=${API_REPLICAS:-1}` (`web api worker admin merchant driver customer caddy`)
   - **Alembic migrations** once inside one API replica (`repair_and_migrate.py`) — **deploy aborts if migration fails**, before traffic cutover
   - Verify `booking_drafts` table exists
   - Restart api + caddy, `docker image prune`
7. **Health + smoke gates** (fail-closed):
   - Wait loop for API `/health` (up to 90s)
   - Caddy :80 HTTP→HTTPS responds
   - API `/health`
   - **Booking smoke**: POST `/v1/booking-drafts` + POST `/v1/quotes` with a Toronto cargoVan fixture must return `quote_id`
   - Postgres `pg_isready`
8. **Prod surface smoke (D3/G1)**: hits live URLs — `api.porterchain.com/health`, `/health/ready`, `porterchain.com/en` (200), `admin/merchant/customer` portals, and a live quote POST.

### Deployment topology

```
Internet :443 → Caddy (Let's Encrypt TLS, HSTS, www→apex)
  ├─ porterchain.com       → website :3000
  ├─ api.porterchain.com   → api :8001 × API_REPLICAS (default 1 on 4GB)
  ├─ admin.porterchain.com → admin :3002
  ├─ merchant.porterchain.com → merchant :3001
  ├─ driver.porterchain.com  → driver :3003
  └─ customer.porterchain.com → customer :3004

Internal: postgres:16.10 (prod volume), redis:8.8, spicedb (v1.56.0 + datastore DB init), valhalla
```

Ports are **not published** to the host — only Caddy exposes 80/443.

---

## 7. Deploy Website — `deploy-website.yml`

Manual website-only hotfix path. Reuses the same GHCR image, but:

- Runs website-specific gates first (`validate:website-seo`, `validate:developer-portal`, website lint, Prettier check, advisory `pnpm audit --prod` — non-fatal).
- Rolls only `web` (+ pulls `api admin merchant driver customer worker caddy` for consistency) via `recover-prod-stack.sh`.
- Smoke: `porterchain.com/en` 200, `sitemap.xml` `<urlset`, GTA city page 200.

---

## 8. Nightly E2E — `nightly-e2e.yml`

Scheduled `0 11 * * *` UTC (06:00 ET), manual dispatch. Full dev-layer behavioral proof:

- Services: `postgres:18-alpine3.24` (named container so it can be restarted) + `redis:8.8.0-alpine3.23` — **pinned, no floating tags**.
- Env: `CLERK_DEV_BYPASS=true`, `STRIPE_MOCK=true`, `ROUTING_ENGINE=valhalla` with `VALHALLA_BASE_URL=http://127.0.0.1:8002`, fallback `OSRM_HOST=https://router.project-osrm.org`.
- Enables `pg_stat_statements` (ALTER SYSTEM + container restart).
- Starts **`scripts/ci_valhalla_stub.py`** — a GTA (~150 km) routing stub, so the full pipeline runs without building Valhalla tiles.
- Runs `alembic upgrade head`, seeds pricing tariffs + admin + merchant users (`seed_local_dev.py`, `seed_dev_portal_users.py`), and **fails early if no active MerchantUser** (a known `phase_3` BLOCKER).
- Preflight Redis + Valhalla, then `verify_d3_matrix.py --e2e`.

---

## 9. Set Public Ingest Key — `set-public-ingest-key.yml`

Manual ops job:

1. Install Doppler CLI → check `PUBLIC_INGEST_API_KEY` exists (generate via `openssl rand -hex 32` if missing, masked in logs).
2. SSH to droplet → `sync-secrets.sh` → verify key landed in `.env` → `docker compose up -d --force-recreate --no-deps api web` → health check.

Used by the contact/quote form path: website `/api/inquiries` → API `/v1/public/inquiries` → admin CRM leads.

---

## 10. Dependabot — `.github/dependabot.yml`

| Ecosystem        | Frequency | PR limit | Notes                                                                                                                                                                                                       |
| ---------------- | --------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `github-actions` | weekly    | 10       | Keeps action pins fresh                                                                                                                                                                                     |
| `npm`            | weekly    | 5        | **Ignores** `next`, `react`, `react-dom`, `eslint`, `typescript`, `@clerk/nextjs`, `@sentry/nextjs`, `tailwindcss` (frontend freeze ~2026-10 per `.cursor/rules/dependency-freeze.mdc`); groups minor+patch |
| `pip`            | weekly    | 10       | API Python deps                                                                                                                                                                                             |

---

## 11. Local git hooks (Husky)

- `.husky/pre-commit` → **`pnpm validate:precommit`** = `pnpm format:check && pnpm validate:d2`.
- Bootstrapped via root `"prepare": "husky"`; `pnpm install` regenerates the hooks.
- So the _local_ pre-push/push experience already enforces format + D2 contracts before CI even runs.

---

## 12. Secrets architecture (git-adjacent)

| Store                      | Owns                                                                                                                                                                             | How CI consumes                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **GitHub Actions secrets** | Deploy infra (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PORT`), public bake keys (`NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, Clerk publishable keys, Sentry DSN, Zoho, GA) | `${{ secrets.* }}` in workflows                                                        |
| **GitHub variables**       | `NEXT_PUBLIC_SITE_URL`, `API_REPLICAS` (default 1 on 4GB), `PORTERCHAIN_PUSH_ENABLED/SEND`, `DOPPLER_PROJECT/CONFIG`, Zoho toggle                                                | `${{ vars.* }}` with `                                                                 |     | ` defaults |
| **Doppler** (`pcd`/`prd`)  | **Runtime** secrets: `POSTGRES_PASSWORD`, `STRIPE_*`, `JWT_SECRET`, Clerk secret keys/JWKS, Firebase, push flags, Fleetbase                                                      | `DOPPLER_TOKEN` in GH Actions → `sync-secrets.sh` → `/opt/porterchain/.env` on droplet |
| **GHCR**                   | Container images                                                                                                                                                                 | `GITHUB_TOKEN` (built-in) — no extra secret                                            |

Legacy GitHub runtime secrets (e.g. `CLERK_SECRET_KEY`, `POSTGRES_PASSWORD`) were **removed 2026-07-07** — `DOPPLER_TOKEN` is now required.

**Fleetbase note:** the dispatch bridge is **off by default** in prod (`FLEETBASE_DISPATCH_BRIDGE=false`). When enabled, the API refuses to boot without API key + webhook secret + company UUID, and `GET /health/ready` requires `fleetbase_sync.link_pct ≥ 98%`.

**Fleetbase webhook URL:** `https://api.porterchain.com/webhooks/fleetbase` · **Stripe webhook URL:** `https://porterchain.com/webhooks/stripe` (via Caddy → API).

---

## 13. Rollback & recovery

- **Rollback:** Actions → Deploy → Run workflow uses HEAD; to roll back, SSH to droplet, pin previous image tag:
  ```bash
  cd /opt/porterchain
  export WEB_IMAGE=ghcr.io/porterchain/pcd-website:<previous-sha>
  export API_IMAGE=ghcr.io/porterchain/pcd-api:<previous-sha>
  docker compose -f docker-compose.prod.yml up -d
  ```
- **API scale:** default `API_REPLICAS=1` on the 4GB droplet; `2` when the host has ≥8 GB. `recover-prod-stack.sh` applies the scale.
- **Recovery script** `infrastructure/deploy/scripts/recover-prod-stack.sh` is idempotent: boots data plane, waits for health, then rolls the app tier. It is what `deploy.yml` invokes on the droplet.
- **Backups:** `backup-porterchain-postgres.sh` / `restore-porterchain-postgres.sh` on the droplet.
- **Manual deploy/rollback docs:** `infrastructure/deploy/README.md` § Manual Deploy / Rollback.

---

## 14. What is NOT in GitHub CI/CD

| Item               | Where it lives                                                                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Mobile apps (Expo) | Deploy via **EAS** separately (`apps/mobile-*/eas.json`) — no GitHub Actions job                                                          |
| Fleetbase stack    | Local/compose only (`apps/fleetbase/`, `infrastructure/docker/fleetbase.*`) — not part of `deploy.yml` droplet stack                      |
| Valhalla tiles     | Built locally (`prepare-valhalla-gta.sh`) or stubbed in CI (`ci_valhalla_stub.py`)                                                        |
| CodeQL upload      | Disabled (`upload: false`) — repo lacks GHAS/code scanning                                                                                |
| Branch protection  | No API-visible rules on `main` (404 from GitHub API) — CI required-checks gate is enforced by the `deploy.yml` workflow_run guard instead |

---

## 15. Key takeaways

1. **Fail-closed by design**: CI success is a hard prerequisite for auto-deploy; migrations abort deploys; health/smoke checks run against prod before the workflow reports success.
2. **Pin, don't float**: CI service containers (`postgres:18-alpine3.24`, `redis:8.8.0-alpine3.23`) and images mirror the repo's no-`:latest` policy (Trivy `ignore-unfixed`, `.trivyignore`, dependency freeze).
3. **Three secret stores, one owner each**: GitHub for deploy/bake keys, Doppler for runtime, GHCR for images — with `sync-secrets.sh` as the bridge.
4. **Architecture enforcement is CI**: ~40 `validate:*` gates (including the Fleetbase boundary and thin-router audit) run before anything can merge — that's how the "Fleetbase-first" rule is mechanically enforced, not just documented.
5. **Rollback is a first-class citizen**: every image is tagged with full-SHA + `:latest`, the compose accepts image env overrides, and recovery scripts are idempotent.

---

## 16. Related documents

| Document                                                                               | Purpose                              |
| -------------------------------------------------------------------------------------- | ------------------------------------ |
| [infrastructure/deploy/README.md](infrastructure/deploy/README.md)                     | Deployment CI/CD canonical reference |
| [docs/SECRETS_MAP.md](docs/SECRETS_MAP.md)                                             | Four-store secret matrix             |
| [infrastructure/deploy/SECRETS.md](infrastructure/deploy/SECRETS.md)                   | Secret setup details                 |
| [infrastructure/deploy/CLERK_APPS_SETUP.md](infrastructure/deploy/CLERK_APPS_SETUP.md) | Clerk app provisioning               |
| [docs/architecture/ADR-012-scaling.md](docs/architecture/ADR-012-scaling.md)           | API replicas / rolling deploy        |
| [docs/architecture/ADR-013-secrets.md](docs/architecture/ADR-013-secrets.md)           | Secrets decision record              |
| [RUNBOOK.md](RUNBOOK.md)                                                               | Ops runbook incl. prod deploys       |
| [DOCKER_SETUP.md](DOCKER_SETUP.md)                                                     | Local + Fleetbase compose            |
| [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md)                                         | Port map                             |
