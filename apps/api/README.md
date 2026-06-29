# Porterchain API (FastAPI)

Retail quote → booking → payment → order API. See [PRODUCT_REQUIREMENTS.md](../../PRODUCT_REQUIREMENTS.md) and [ORDER_LIFECYCLE.md](../../ORDER_LIFECYCLE.md).

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
pnpm dev:api
```

Default port: **8001**. Health: `GET /health`.

## Dev defaults (`.env.example`)

- SQLite database (`porterchain.db`)
- `CLERK_DEV_BYPASS=true` — no real Clerk JWT required
- `STRIPE_MOCK=true` — use `POST /v1/bookings/mock-complete` instead of Stripe Checkout
- `FLEETBASE_DISPATCH_BRIDGE=false` — dispatch bridge no-op

## Key endpoints

| Method | Path                         | Purpose                             |
| ------ | ---------------------------- | ----------------------------------- |
| POST   | `/v1/quotes`                 | Anonymous instant quote             |
| GET    | `/v1/quotes/{id}`            | Fetch quote                         |
| POST   | `/v1/bookings`               | Start booking (Clerk auth)          |
| POST   | `/v1/bookings/mock-complete` | Dev payment completion              |
| GET    | `/v1/orders/{tracking}`      | Public tracking                     |
| POST   | `/webhooks/stripe`           | Stripe `checkout.session.completed` |
