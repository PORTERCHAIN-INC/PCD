# Porterchain API (FastAPI)

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-08

Logistics orchestrator — retail booking, merchant, driver, admin, notifications, and Fleetbase bridge. See [PORTERCHAIN_CHARTER.md](../../docs/PORTERCHAIN_CHARTER.md) and [ORDER_LIFECYCLE.md](../../ORDER_LIFECYCLE.md).

---

## Setup

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

From repo root:

```bash
pnpm db:migrate    # PostgreSQL 18 — Alembic head
pnpm dev:api       # http://localhost:8001
pnpm db:seed       # optional local dev data
```

Health: `GET /health`

---

## Stack

| Component  | Value                                               |
| ---------- | --------------------------------------------------- |
| Python     | 3.14.6                                              |
| Framework  | FastAPI                                             |
| Database   | PostgreSQL 18 (`postgresql+psycopg://`)             |
| Migrations | Alembic — head `n2o3p4q5r6s7`                       |
| Auth       | Clerk JWT (dev bypass when `CLERK_DEV_BYPASS=true`) |

---

## API Surfaces

| Prefix                | Consumers                                 | Purpose                                                  |
| --------------------- | ----------------------------------------- | -------------------------------------------------------- |
| `/v1/*`               | Website, customer portal, mobile-customer | Quotes, bookings, orders, customers, payments            |
| `/v1/merchant/*`      | Merchant portal                           | Merchant dashboard and operations                        |
| `/v1/merchant-api/*`  | External integrations                     | API-key gateway (`X-Api-Key`, scoped)                    |
| `/v1/admin/*`         | Admin (:3002)                             | Ops control tower, finance, support, collaboration slice |
| `/driver-api/v1/*`    | Driver portal (:3003), mobile-driver      | Driver execution, POD, GPS, offline                      |
| `/v1/notifications/*` | All apps                                  | Inbox, devices, WebSocket                                |
| `/webhooks/*`         | Stripe, Fleetbase                         | External webhooks                                        |

Fleetbase is accessed only through `fleetbase-adapter` and engine bridges — never from client apps.

## OpenAPI

Live OpenAPI is the route contract. Markdown describes why; `/docs` lists every path.

| Resource            | URL                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------ |
| Interactive (local) | [http://localhost:8001/docs](http://localhost:8001/docs)                             |
| JSON (local)        | [http://localhost:8001/openapi.json](http://localhost:8001/openapi.json)             |
| Interactive (prod)  | [https://api.porterchain.com/docs](https://api.porterchain.com/docs)                 |
| JSON (prod)         | [https://api.porterchain.com/openapi.json](https://api.porterchain.com/openapi.json) |
| Repo snapshot       | [`docs/api/openapi.json`](../../docs/api/openapi.json) — `pnpm docs:openapi`         |
| Postman collection  | [`docs/api/porterchain.postman.json`](../../docs/api/porterchain.postman.json)       |
| Partner guide       | [`docs/api/PARTNER_GUIDE.md`](../../docs/api/PARTNER_GUIDE.md)                       |
| Developer portal    | [porterchain.com/developers](https://porterchain.com/en/developers) (website)        |

Merchant API scopes and integration docs: [`gateway_engine/merchant_api.py`](./src/porterchain_api/gateway_engine/merchant_api.py) · live bundle at `GET /v1/merchant/integrations/documentation`.

---

## Dev Defaults (`.env.example`)

| Setting                     | Default                                                                   | Notes                                 |
| --------------------------- | ------------------------------------------------------------------------- | ------------------------------------- |
| `DATABASE_URL`              | `postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain` | Run `pnpm db:migrate`                 |
| `CLERK_DEV_BYPASS`          | `true`                                                                    | Bearer `dev` accepted locally         |
| `STRIPE_MOCK`               | `true`                                                                    | Use `POST /v1/bookings/mock-complete` |
| `FLEETBASE_DISPATCH_BRIDGE` | `false`                                                                   | Dispatch sync no-op until enabled     |

---

## Key Endpoints

| Method | Path                         | Purpose                              |
| ------ | ---------------------------- | ------------------------------------ |
| POST   | `/v1/quotes`                 | Anonymous instant quote              |
| GET    | `/v1/quotes/{id}`            | Fetch quote                          |
| POST   | `/v1/bookings`               | Start booking (Clerk auth)           |
| POST   | `/v1/bookings/mock-complete` | Dev payment completion               |
| POST   | `/v1/bookings/sync-checkout` | Stripe return — poll until confirmed |
| GET    | `/v1/bookings/confirmation`  | Poll booking confirmation            |
| GET    | `/v1/orders/{tracking}`      | Public tracking                      |
| GET    | `/v1/customers/me/dashboard` | Customer dashboard                   |
| POST   | `/driver-api/v1/auth/login`  | Driver Clerk → Porterchain JWT       |
| POST   | `/webhooks/stripe`           | Stripe `checkout.session.completed`  |

---

## Project Layout

```
apps/api/
├── src/porterchain_api/
│   ├── routers/           # REST surface
│   ├── *_engine/          # Domain engines (booking, driver, merchant, admin, …)
│   ├── billing_engine/
│   ├── notification_engine/
│   └── platform/          # Middleware, event bus, rate limits
├── alembic/               # Migrations — see alembic/README.md
├── tests/
└── run.py
```

PYTHONPATH includes `shared/python`, `services/*` packages at runtime (see root `pnpm dev:api`).

---

## Validation

```bash
pnpm db:test              # PostgreSQL smoke tests
pnpm db:validate          # Module validation
pnpm validate:e2e         # E2E validation suite
pnpm validate:e2e:reports # Regenerate E2E report markdown
```

---

## Related Documents

| Document                                                         | Purpose            |
| ---------------------------------------------------------------- | ------------------ |
| [alembic/README.md](./alembic/README.md)                         | Migration policy   |
| [../../ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md) | Full env reference |
| [../../AUTHENTICATION.md](../../AUTHENTICATION.md)               | Auth architecture  |
| [../../DATABASE_ARCHITECTURE.md](../../DATABASE_ARCHITECTURE.md) | Database design    |

---
