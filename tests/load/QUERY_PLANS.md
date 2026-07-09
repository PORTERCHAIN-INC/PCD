# Query plans under load (§5.4.4)

After `pnpm load:booking`, review Postgres plans for quote and order hot paths. Goal: no unexpected sequential scans on large tables at p95 load.

## Prerequisites

```bash
pnpm docker:up && pnpm db:migrate && pnpm dev:api
pnpm load:booking
```

## Automated EXPLAIN (local)

```bash
cd apps/api && source .venv/bin/activate
PYTHONPATH=src python scripts/explain_load_hot_paths.py
```

## pg_stat_statements (optional extension)

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT query, calls, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Hot paths to review

| Path                  | Table(s)                  | Expected plan                          |
| --------------------- | ------------------------- | -------------------------------------- |
| `POST /v1/quotes`     | `quotes`, pricing lookups | Index or small seq scan on dev data    |
| Order list / dispatch | `orders`                  | `merchant_id` / `created_at` index use |
| Webhook idempotency   | Redis + stripe events     | Postgres not on hot path               |

## Artifacts

Save k6 JSON under `tests/load/output/` and note any plan regressions in PR description when changing quote or order queries.

See [RUNBOOK.md](../../RUNBOOK.md) § Load testing for p95 SLO targets.
