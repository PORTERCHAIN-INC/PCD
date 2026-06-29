# Porterchain centralized configuration

All environment variables are documented in [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md).

## Templates

| Surface | Template | Runtime file |
|---------|----------|--------------|
| Website | `env/website.env.example` | `website/.env.local` |
| API | `env/api.env.example` | `apps/api/.env` |
| Worker | `env/worker.env.example` | `apps/worker/.env` |
| Docker Compose | `infrastructure/docker/.env.example` | `infrastructure/docker/.env` |
| Fleetbase | `env/fleetbase.env.example` | Fleetbase deployment |

## Integration ownership

| Integration | Config owner | Consumed by |
|-------------|--------------|-------------|
| Clerk | API + all web apps | Auth (sole provider) |
| Stripe | API only | Billing service |
| Fleetbase | API + worker | Dispatch bridge (internal only) |
| Google Maps | Website (public key) | Maps client |
| Valhalla / OSRM | API | Maps service |
| Firebase | API + worker | Push notifications |
| Redis | API + worker | Events, queues, cache |
| PostgreSQL | API | Porterchain-owned data |
| MySQL | Fleetbase | Fleetbase-owned data |
| SMTP | Worker | Email queue |

## Python settings

`shared/python/porterchain_shared/config/settings.py` — `PlatformSettings`

## TypeScript public env

`website/src/lib/env.ts` — public keys only (never secrets)
