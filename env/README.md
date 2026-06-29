# Porterchain environment variables

Copy the relevant template(s) to a local `.env` file. **Never commit real secrets.**

## Quick start

| Service | Template | Copy to |
|---------|----------|---------|
| Website | `website.env.example` | `website/.env.local` |
| Porterchain API | `api.env.example` | `apps/api/.env` |
| Worker | `worker.env.example` | `apps/worker/.env` |
| Fleetbase / Docker stack | `fleetbase.env.example` | `services/fleetbase/.env` or Docker `env_file` |
| Merchant portal | `merchant-portal.env.example` | `apps/merchant-portal/.env.local` |
| Driver portal | `driver-portal.env.example` | `apps/driver-portal/.env.local` |
| Driver app | `mobile-driver.env.example` | `apps/mobile-driver/.env` |
| Full local stack | `compose.env.example` | `.env` at repo root (Docker Compose) |

```bash
# Website (only app in this repo today)
cp env/website.env.example website/.env.local
# Fill in secrets marked REQUIRED

# Docker infrastructure (MySQL, Redis, Mailhog)
cp infrastructure/docker/.env.example infrastructure/docker/.env
pnpm docker:up
```

## Variable prefixes

| Prefix | Exposed to browser? |
|--------|---------------------|
| `NEXT_PUBLIC_*` | Yes |
| `EXPO_PUBLIC_*` | Yes (inlined at mobile build) |
| Everything else | No — server only |

## Ports (local)

| Port | Service |
|------|---------|
| 3000 | Website |
| 3001 | Merchant portal |
| 3002 | Admin platform |
| 3003 | Driver web portal |
| 4200 | Fleetbase console |
| 8000 | Fleetbase API |
| 8001 | Porterchain API |
| 8002 | Valhalla |
| 5432 | PostgreSQL (Porterchain) |
| 3306 | MySQL (Fleetbase) |
| 6379 | Redis |
| 1025 / 8025 | Mailhog SMTP / UI |

Check live usage: `pnpm ports`

See [PORT_CONFIGURATION.md](../PORT_CONFIGURATION.md) and [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md).

## Required vs optional

In each `.env.example`, variables are tagged:

- **REQUIRED** — service will not work without it
- **OPTIONAL** — feature flags, overrides, dev convenience
- **PRODUCTION** — required only in prod
