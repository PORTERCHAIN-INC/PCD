# Porterchain — Agent Instructions

See [`README.md`](./README.md), [`TECH_STACK.md`](./TECH_STACK.md), and [`env/README.md`](./env/README.md) for the canonical setup and run instructions. App-specific rules live in per-app files such as [`website/AGENTS.md`](./website/AGENTS.md).

## Cursor Cloud specific instructions

The startup update script already runs `pnpm install` and rebuilds the API Python venv, so dependencies are ready. The notes below cover only non-obvious runtime/startup caveats for this environment.

### Toolchain / PATH

- **Node 24 is required** (`.nvmrc` = 24.18.0) but the VM's default `PATH` resolves `node` to a v22 shim at `/exec-daemon`. Node 24 is installed via nvm and prepended to `PATH` in `~/.bashrc`, so **login/interactive shells (and tmux login shells) get v24 automatically**. In a bare non-login shell, first run `. "$HOME/.nvm/nvm.sh" && nvm use 24.18.0`.
- **pnpm run-scripts require bash**: many root scripts (`dev:api`, `db:migrate`, etc.) use `source`, which fails under `sh`. pnpm's `script-shell` is configured to `/bin/bash` for this reason. If you invoke the underlying commands manually, use `bash`, not `sh`.

### Services & data stores

- **Postgres 16 and Redis 7 run natively** (installed via apt), not via Docker (`pnpm docker:up` is not used here — Docker is not installed). Start them if not running:
  - Postgres: `sudo pg_ctlcluster 16 main start` (role/db `porterchain`/`porterchain`, DB `porterchain` on `:5432`).
  - Redis: `sudo redis-server /etc/redis/redis.conf --daemonize yes` (`:6379`). Always start Redis with its config file so it writes `dump.rdb` to `/var/lib/redis`; running bare `redis-server` from the repo root litters an untracked `dump.rdb` in `/workspace`.
- Redis is **optional locally** — the API/worker fall back to an in-memory event bus/queue when it is down (only required when `APP_ENV != local`).

### Running the stack

- Migrations must be applied before the API serves data: `pnpm db:migrate` (Alembic upgrade head).
- API: `pnpm dev:api` → `http://localhost:8001` (health at `/health`, Swagger at `/docs`). Needs `apps/api/.env` (copy from `env/api.env.example`).
- Website: `pnpm dev:website` → `http://localhost:3000`. Needs `website/.env.local` (copy from `env/website.env.example`).
- Run long-lived dev servers under tmux login shells so they pick up Node 24.

### Auth / Clerk caveat (important)

- The **website and all four portals (`apps/{admin,merchant-portal,driver-portal,customer}`) require a real Clerk publishable key**. With `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` unset, `AppClerkProvider` does not mount `ClerkProvider` while `SiteNavbarAuth` still calls `useAuth()`, so every `[locale]` page returns **HTTP 500**. A malformed/placeholder key does not work — Clerk validates the key against a real instance. Set real Clerk keys (`env/clerk.env` + `pnpm clerk:sync`) to run the frontends.
- The **API does not need Clerk keys locally**: with `APP_ENV=local` and `CLERK_DEV_BYPASS=true` in `apps/api/.env`, authenticated endpoints accept `Authorization: Bearer dev`. Stripe also runs in mock mode (`stripe_mock` default), so the full booking → checkout → order flow works without external credentials.

### Tests

- API tests: from `apps/api`, `pytest` (uses `PYTHONPATH=src:../../shared/python:../../services/python:...`). `pytest`/`pytest-asyncio` are the API's `dev` extras (installed by the update script).
- `tests/test_config_production.py::test_fleetbase_bridge_allowed_with_secrets_in_production` **requires Clerk credentials in the process env** (`CLERK_SECRET_KEY` + `CLERK_JWKS_URL`, or the four enterprise keys). Without them this one test fails with a Clerk-in-production validation error; the other ~504 tests pass. CI supplies these via secrets.
- Lint: `pnpm lint` (mobile apps excluded).
