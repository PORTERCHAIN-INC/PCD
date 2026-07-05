# Porterchain environment variables

**Type:** CANONICAL
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Copy the relevant template(s) to a local `.env` file. **Never commit real secrets.**

## Quick start

| Service                  | Template                            | Copy to                                        |
| ------------------------ | ----------------------------------- | ---------------------------------------------- |
| Website                  | `website.env.example`               | `website/.env.local`                           |
| Porterchain API          | `api.env.example`                   | `apps/api/.env`                                |
| Worker                   | `worker.env.example`                | `apps/worker/.env`                             |
| Admin portal             | `admin.env.example`                 | `apps/admin/.env.local`                        |
| Merchant portal          | `merchant-portal.env.example`       | `apps/merchant-portal/.env.local`              |
| Customer portal          | `customer-portal.env.example`       | `apps/customer/.env.local`                     |
| Driver portal            | `driver-portal.env.example`         | `apps/driver-portal/.env.local`                |
| Driver mobile app        | `mobile-driver.env.example`         | `apps/mobile-driver/.env`                      |
| Customer mobile app      | `apps/mobile-customer/.env.example` | `apps/mobile-customer/.env`                    |
| Fleetbase / Docker stack | `fleetbase.env.example`             | `apps/fleetbase/api/.env` or Docker `env_file` |
| Full local stack         | `compose.env.example`               | `.env` at repo root (Docker Compose)           |
| Production (droplet)     | `production.env.example`            | `/opt/porterchain/.env` on server              |

```bash
# Minimum local setup
cp env/website.env.example website/.env.local
cp env/api.env.example apps/api/.env
cp infrastructure/docker/.env.example infrastructure/docker/.env
pnpm docker:up
pnpm db:migrate
pnpm dev:api
```

See [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) for the full catalog.

## Variable prefixes

| Prefix          | Exposed to browser?           |
| --------------- | ----------------------------- |
| `NEXT_PUBLIC_*` | Yes                           |
| `EXPO_PUBLIC_*` | Yes (inlined at mobile build) |
| Everything else | No — server only              |

## Ports (local) → production subdomain

| Port        | Local service     | Production host          |
| ----------- | ----------------- | ------------------------ |
| 3000        | Website           | porterchain.com          |
| 3001        | Merchant portal   | merchant.porterchain.com |
| 3002        | Admin platform    | admin.porterchain.com    |
| 3003        | Driver web portal | driver.porterchain.com   |
| 3004        | Customer portal   | customer.porterchain.com |
| 8001        | Porterchain API   | api.porterchain.com      |
| 4200        | Fleetbase console | (optional)               |
| 8000        | Fleetbase API     | (optional)               |
| 8002        | Valhalla          | (optional)               |
| 5432        | PostgreSQL        | internal only            |
| 3306 / 3307 | MySQL             | internal only            |
| 6379        | Redis             | internal only            |
| 1025 / 8025 | Mailhog SMTP / UI | dev only                 |

Check live usage: `pnpm ports`

See [PORT_CONFIGURATION.md](../PORT_CONFIGURATION.md).

## Required vs optional

In each `.env.example`, variables are tagged:

- **REQUIRED** — service will not work without it
- **OPTIONAL** — feature flags, overrides, dev convenience
- **PRODUCTION** — required only in prod

---

## Governance

| Document                                      | Role              |
| --------------------------------------------- | ----------------- |
| [masterrule.md](../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md) | Doc vs code audit |
