# Load tests (DD-17)

k6 scenarios for quote/booking and Stripe webhook ingress. Run against local API (`pnpm dev:api` + `pnpm docker:up`) or staging/prod with care.

## Prerequisites

```bash
brew install k6
pnpm docker:up
pnpm db:migrate
pnpm dev:api   # separate terminal — needs Redis for webhook idempotency
```

## Scenarios

| Script        | Endpoints                        | SLO (p95)  |
| ------------- | -------------------------------- | ---------- |
| `booking.js`  | `GET /health`, `POST /v1/quotes` | quote < 3s |
| `webhooks.js` | `POST /webhooks/stripe` (signed) | < 1s       |

## Run

```bash
# Quote + booking path (default localhost:8001)
pnpm load:booking

# Stripe webhook ingress — must match apps/api/.env STRIPE_WEBHOOK_SECRET
STRIPE_WEBHOOK_SECRET=whsec_... pnpm load:webhooks

# Against another host
API_URL=https://api.porterchain.com pnpm load:booking
```

Webhook load against **production** creates `webhook.received` domain events — use low rate or a dedicated staging API only.

## Output

k6 prints p50/p95/p99 at the end. Thresholds fail the run when SLOs are breached. Save JSON for query-plan review:

```bash
k6 run --out json=tests/load/output/booking-$(date +%Y%m%d).json tests/load/booking.js
```

See [RUNBOOK.md](../../RUNBOOK.md) § Load testing for published SLOs.
