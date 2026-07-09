# Enterprise SLA — 99.9% (§11.3.2)

**Type:** CANONICAL  
**Checklist:** §11.3.2  
**Last verified:** 2026-07-09

## Commitment (enterprise tier)

| Metric                          | Target                 | Measurement                                          |
| ------------------------------- | ---------------------- | ---------------------------------------------------- |
| Platform API availability       | **99.9%** monthly      | `/health/ready` uptime excluding planned maintenance |
| On-time delivery (merchant SLA) | Per contract           | Merchant portal SLA dashboard + `sla-history` export |
| Support first response          | **<4h** business hours | Priority tier (see PRIORITY_SUPPORT.md)              |
| Status communication            | <15 min to acknowledge | `/health/status` + incident runbook                  |

## Exclusions

- Planned maintenance (48h notice)
- Merchant-caused misconfiguration (invalid webhooks, API keys)
- Fleetbase vendor outage when bridge enabled (documented in status page)
- Force majeure

## Credits (enterprise contracts)

| Monthly uptime | Service credit                      |
| -------------- | ----------------------------------- |
| 99.0% – 99.9%  | 10% platform fee                    |
| 95.0% – 99.0%  | 25% platform fee                    |
| <95.0%         | 50% platform fee + executive review |

Credits apply to platform software fees only — not pass-through courier execution costs.

## Verification

- Ops: Better Stack / `/health/status` SLO
- Merchants: `GET /v1/merchant/reports/sla-history` · `GET /v1/merchant/reports/export/sla-history.csv`
- Admin: `GET /v1/admin/data-moat/network` network SLA benchmark

## Related

- [PRIORITY_SUPPORT.md](./PRIORITY_SUPPORT.md)
- [STATUS_PAGE.md](../STATUS_PAGE.md)
- [RUNBOOK.md](../../RUNBOOK.md)
