# Porterchain Worker

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-28

Async background processor for the Porterchain event bus and task queues. Shares the API Python venv and database connection.

---

## Run

```bash
# From repo root (uses apps/api/.venv)
pnpm dev:worker
```

Runs alongside `pnpm dev:api`. Requires PostgreSQL; Redis required in production (`require_redis_for_production()`).

---

## Responsibilities

Each loop iteration:

1. **Event bus** — `consume_once()` on `porterchain:events` (group `porterchain-workers`) after `ensure_handlers_registered()`
2. **Task queues** — drain Redis/in-memory queues via `process_queue_message`
3. **Fleetbase retry** — `BookingSyncService.process_retry_queue` every 60s (when `FLEETBASE_DISPATCH_BRIDGE=true`)
4. **Draft reconciliation** — expire/repair booking drafts every 300s
5. **Standing orders** — materialize due merchant standing orders every 300s

---

## Queues

| Queue      | Processor     | Purpose                            |
| ---------- | ------------- | ---------------------------------- |
| `emails`   | notifications | Transactional email                |
| `sms`      | notifications | SMS delivery                       |
| `push`     | notifications | Firebase push                      |
| `dispatch` | dispatch      | Fleetbase dispatch sync            |
| `billing`  | billing       | Stripe reconciliation              |
| `reports`  | (logged)      | Scheduled reports — processor stub |
| `webhooks` | webhooks      | Outbound merchant webhooks         |

Queue names: `shared/python/porterchain_shared/queue/names.py`

---

## Layout

```
apps/worker/
├── run.py                 # Main loop
└── processors/
    ├── notifications.py
    ├── dispatch.py
    ├── billing.py
    └── webhooks.py
```

PYTHONPATH includes API `src`, `shared/python`, and service packages (see root `pnpm dev:worker`).

---

## Environment

Uses `apps/api/.env` — same `DATABASE_URL`, Redis, Fleetbase, and Stripe settings as the API.

| Variable                    | Notes                                         |
| --------------------------- | --------------------------------------------- |
| `DATABASE_URL`              | PostgreSQL (dev 18 / prod 16)                 |
| `REDIS_URL`                 | Required in production                        |
| `WORKER_CONSUMER_NAME`      | Redis stream consumer id (default `worker-1`) |
| `FLEETBASE_DISPATCH_BRIDGE` | Enables retry drain                           |
| `APP_ENV`                   | `local` allows in-memory queue fallback       |

---

## Related Documents

| Document                                 | Purpose                |
| ---------------------------------------- | ---------------------- |
| [../../EVENT_BUS.md](../../EVENT_BUS.md) | Event bus architecture |
| [../../RUNBOOK.md](../../RUNBOOK.md)     | Ops runbook            |
| [../api/README.md](../api/README.md)     | API setup              |

---
