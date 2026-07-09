# Engineer Onboarding — Get to `/health/ready` in <30 minutes

**Type:** CANONICAL (local dev readiness)

## Goal

From a fresh clone to a working Porterchain API at `http://localhost:8001/health/ready` in under 30 minutes.

## Prerequisites

- Node.js **24.18.0** (see `.nvmrc`)
- `pnpm` **11.10** (`corepack enable && pnpm -v`)
- Python **3.14.6**
- Docker (Postgres + Redis)

## Step-by-step

### 1) Install dependencies

```bash
corepack enable
pnpm install
```

### 2) Start the local data stack

```bash
pnpm docker:up
```

This brings up Postgres on `5432` (for `apps/api/.env`) and Redis.

### 3) Set up the API virtualenv

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 4) Run DB migrations

```bash
cd ..
pnpm db:migrate
```

### 5) Start the API

```bash
pnpm dev:api
```

### 6) Verify readiness

```bash
curl -s http://localhost:8001/health/ready | python3 -m json.tool
```

You should see `status: "ok"` (or `"degraded"` if optional checks aren't configured yet).

## Notes on "degraded"

`/health/ready` always requires the database. In `local`, Redis and Clerk checks may show `"unavailable"` / `"not_configured"` without blocking the overall status.

If you want Clerk readiness to be `enterprise/ok`, run:

```bash
pnpm clerk:sync
```

## If it doesn't work

- Database errors: rerun `pnpm docker:up` and then `pnpm db:migrate`.
- Port 8001 not reachable: check `pnpm dev:api` logs for startup failures.
- JSON parsing errors: ensure you're hitting `.../health/ready` (not `/health`).

## Optional — Fleetbase dispatch stack

Dispatch sync is **not required** for `/health/ready`. Enable it when you work on orders → Fleetbase → driver execution.

```bash
pnpm docker:fleetbase:install   # first time only
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify    # health checks for adapter stack
```

See [DOCKER_SETUP.md](../DOCKER_SETUP.md) and [FLEETBASE_INSTALL.md](../FLEETBASE_INSTALL.md).

## Pre-commit checks

Before pushing, run (or rely on the Husky hook after `pnpm install`):

```bash
pnpm validate:precommit   # format:check + validate:d2
pnpm validate:p0:fast       # G1–G3 only, <2 min (ENG-G4 budget)
pnpm validate:p0            # full G1–G9 incl. E2E, <15 min on typical dev machine
```

Full `validate:p0` prints elapsed time and fails if runtime exceeds **900s (15 min)**.
