# Porterchain Worker

Async job processor for platform queues.

## Queues

| Queue      | Purpose                      |
| ---------- | ---------------------------- |
| `emails`   | Transactional email delivery |
| `sms`      | SMS notifications            |
| `push`     | Firebase push notifications  |
| `dispatch` | Fleetbase dispatch sync      |
| `billing`  | Stripe reconciliation        |
| `reports`  | Scheduled report generation  |
| `webhooks` | Outbound merchant webhooks   |

## Run

```bash
# From repo root (shares API venv)
pnpm dev:worker
```

Requires Redis for production (`REDIS_URL` in `.env`). Falls back to in-memory queues in local dev.
