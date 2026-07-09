# Status page & incident comms (§11.3.5)

**Type:** CANONICAL  
**Checklist:** §11.3.5  
**Last verified:** 2026-07-09

## Public status API

```http
GET https://api.porterchain.com/health/status
```

Returns aggregate component health (no auth, minimal detail):

```json
{
  "status": "ok",
  "service": "porterchain",
  "components": {
    "api": "operational",
    "database": "operational",
    "redis": "operational",
    "payments": "operational",
    "dispatch": "operational"
  },
  "updated_at": "2026-07-09T16:00:00+00:00"
}
```

Deep probe for ops: `GET /health/ready` (includes Clerk, queues, Fleetbase sync).

## Production status page (Phase 2)

Host a public page at `status.porterchain.com` polling `/health/status` every 60s. Options:

- Better Stack / Statuspage.io
- Static site + cron from `website/` subdomain

## Incident comms template

1. **Investigating** — component degraded in `/health/status`
2. **Identified** — root cause known, mitigation in progress
3. **Monitoring** — fix deployed, watching metrics
4. **Resolved** — all components operational

Post to merchant email list + admin banner when `status != ok` for >5 minutes.

## Runbook

See [RUNBOOK.md](../../RUNBOOK.md) for escalation paths and Fleetbase bridge failures.
