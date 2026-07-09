# Grafana dashboards — Prometheus scrape (Appendix B.4)

**Type:** CANONICAL  
**Checklist:** B.4  
**Last verified:** 2026-07-09  
**Status:** Dev documented — prod Grafana instance deferred to ops layer

## Metrics source

Scrape `GET https://api.porterchain.com/metrics` (or `localhost:8001/metrics` in dev).

Key series:

| Metric                                              | Use                  |
| --------------------------------------------------- | -------------------- |
| `porterchain_queue_depth{queue}`                    | Worker backlog (B.5) |
| `porterchain_orders_last_7d`                        | Volume trend         |
| `porterchain_merchant_webhook_delivery_success_pct` | Partner webhook SLO  |
| `porterchain_auto_dispatch_pct`                     | Dispatch health      |
| `porterchain_on_time_delivery_pct`                  | SLA dashboard        |

## Recommended panels

1. **API health** — `porterchain_up`, `/health/ready` synthetic check
2. **Queues** — stacked `porterchain_queue_depth` by queue name; alert if any > 100 for 15m
3. **Webhooks** — merchant delivery success % + Stripe/Fleetbase ingress 5xx (from logs)
4. **Business** — orders_last_7d, auto_dispatch_pct, on_time_delivery_pct

## Prod setup (deferred)

1. Deploy Grafana on droplet or managed Grafana Cloud
2. Add Prometheus scrape job → `api:8001/metrics` on Docker network
3. Import dashboard JSON from `infrastructure/observability/` when added

## Dev verification

```bash
curl -s localhost:8001/metrics | grep porterchain_queue_depth
pnpm validate:observability
```
