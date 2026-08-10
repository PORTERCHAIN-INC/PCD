# Execution metrics (§5.3)

**Type:** CANONICAL  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-08

Operational and business metrics for the Porterchain loop. Engineering SLOs are enforced in CI via `pnpm validate:golden-rules`.

## API surfaces

| Surface           | Path                                            | Audience      |
| ----------------- | ----------------------------------------------- | ------------- |
| Admin dashboard   | `GET /v1/diagnostics/execution-metrics`         | Admin portal  |
| Fleetbase sync    | `GET /v1/diagnostics/fleetbase-sync`            | Admin portal  |
| Merchant webhooks | `GET /v1/diagnostics/merchant-webhook-delivery` | Admin portal  |
| Prometheus        | `GET /metrics`                                  | Grafana / ops |
| Readiness         | `GET /health/ready`                             | Deploy probes |

## §5.3 targets

| ID    | Metric                    | Target  | Notes                                                                                                  |
| ----- | ------------------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| 5.3.1 | Orders/week (prod)        | ≥50     | `porterchain_orders_last_7d` on `/metrics`; dev counts informational                                   |
| 5.3.5 | Deploy frequency          | ≥2/week | `target_per_week: 2`; CI success on `main` triggers [Deploy workflow](../.github/workflows/deploy.yml) |
| 5.3.6 | Fleetbase sync            | ≥98%    | `fleetbase_sync.meets_slo` on `/health/ready` when bridge on                                           |
| 5.3.7 | Merchant webhook delivery | ≥99%    | `merchant_webhook_delivery` on `/health/ready`                                                         |
| 5.3.2 | Auto-dispatch %           | ≥90%    | `porterchain_auto_dispatch_pct` on `/metrics`                                                          |
| 5.3.3 | On-time delivery %        | ≥95%    | `porterchain_on_time_delivery_pct` (scheduled_at + grace)                                              |
| 5.3.4 | Support first response    | <4h avg | `porterchain_support_first_response_avg_hours`                                                         |

## Deploy frequency (§5.3.5)

1. Every green **CI** run on `main` can trigger **Deploy** (`workflow_run`).
2. Manual hotfix: Actions → Deploy → **Run workflow** (`workflow_dispatch`).
3. Measure: GitHub → Actions → Deploy → filter **last 7 days** — expect **≥2** successful runs during active development.

Rollback stays under **15 minutes**: pin previous GHCR image tag and `docker compose up` (see [infrastructure/deploy/README.md](../infrastructure/deploy/README.md)).

## Local verification

```bash
pnpm validate:golden-rules
curl -s http://localhost:8001/metrics | grep porterchain_orders
curl -s http://localhost:8001/health/ready | jq '.merchant_webhook_delivery'
```

## Ops runbooks

| Topic                   | Doc                                      |
| ----------------------- | ---------------------------------------- |
| Backup / restore drill  | [BACKUP_RESTORE.md](./BACKUP_RESTORE.md) |
| Uptime + incident drill | [RUNBOOK.md](../RUNBOOK.md)              |
