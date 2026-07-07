# Porterchain Centralized Configuration

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Environment and integration boundaries for the Porterchain monorepo.

> **Canonical env reference:** [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md)

---

## Environment Templates (`env/`)

| Surface         | Template                          | Runtime file                                     |
| --------------- | --------------------------------- | ------------------------------------------------ |
| Monorepo shared | `env/.env`                        | Loaded by Next.js apps via `@porterchain/config` |
| Website         | `env/website.env.example`         | `website/.env.local`                             |
| API             | `env/api.env.example`             | `apps/api/.env`                                  |
| Worker          | `env/worker.env.example`          | `apps/worker/.env` (or shared API `.env`)        |
| Admin           | `env/admin.env.example`           | `apps/admin/.env.local`                          |
| Merchant portal | `env/merchant-portal.env.example` | `apps/merchant-portal/.env.local`                |
| Driver portal   | `env/driver-portal.env.example`   | `apps/driver-portal/.env.local`                  |
| Customer portal | `env/customer-portal.env.example` | `apps/customer/.env.local`                       |
| Mobile driver   | `env/mobile-driver.env.example`   | Expo / EAS secrets                               |
| Fleetbase       | `env/fleetbase.env.example`       | Fleetbase deployment                             |
| Docker Compose  | `env/compose.env.example`         | `infrastructure/docker/.env`                     |
| Production      | `env/production.env.example`      | Production reference                             |

See also [env/README.md](../../env/README.md).

---

## Integration Ownership

| Integration     | Config owner           | Consumed by                     |
| --------------- | ---------------------- | ------------------------------- |
| Clerk           | API + all apps         | Sole auth provider              |
| Stripe          | API only               | Billing / checkout webhooks     |
| Fleetbase       | API + worker           | Dispatch bridge (internal only) |
| Google Maps     | Web/mobile public keys | Map display                     |
| Valhalla / OSRM | API                    | Routing in maps service         |
| Firebase        | API + mobile           | Push notifications              |
| Redis           | API + worker           | Events, queues, cache           |
| PostgreSQL 16   | API                    | Porterchain-owned data          |
| MySQL           | Fleetbase              | Fleetbase-owned data (separate) |
| SMTP            | Worker                 | Email queue                     |

---

## Python Settings

```
shared/python/porterchain_shared/config/settings.py
```

`PlatformSettings` — Pydantic settings for API, worker, and service modules:

- `database_url` (PostgreSQL)
- `redis_url`
- Clerk, Stripe, Fleetbase, maps routing URLs
- Feature flags (`fleetbase_dispatch_bridge`, `stripe_mock`, `clerk_dev_bypass`)

API also uses `apps/api/src/porterchain_api/config.py` (`Settings`) for app-specific overrides.

---

## TypeScript Public Env

Next.js apps load monorepo env via `@porterchain/config/monorepo-env.mjs`:

| Helper                | Used by                                                           |
| --------------------- | ----------------------------------------------------------------- |
| `loadMonorepoEnv()`   | All Next apps — reads `env/.env` without overriding existing vars |
| `nextPublicEnv()`     | Website, merchant, driver portals                                 |
| `adminPublicEnv()`    | Admin                                                             |
| `customerPublicEnv()` | Customer portal                                                   |

Injected in each app's `next.config.ts` as `env: { ... }`.

**Rule:** Never expose secrets in `NEXT_PUBLIC_*` — client bundles only get public keys and URLs.

Per-app public env helpers also live in app `src/lib/env.ts` where needed.

---

## Related Documents

| Document                                                           | Purpose                       |
| ------------------------------------------------------------------ | ----------------------------- |
| [../../packages/config/README.md](../../packages/config/README.md) | `@porterchain/config` package |
| [../../DOCKER_SETUP.md](../../DOCKER_SETUP.md)                     | Docker env                    |
| [../../PORT_CONFIGURATION.md](../../PORT_CONFIGURATION.md)         | Ports                         |

---

## Governance

| Document                                                       | Role              |
| -------------------------------------------------------------- | ----------------- |
| [../../masterrule.md](../../masterrule.md)                     | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
