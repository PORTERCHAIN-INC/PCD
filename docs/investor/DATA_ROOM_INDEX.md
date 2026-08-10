# Investor data room index (§10.2.5)

**Type:** CANONICAL  
**Checklist:** §10.2.5  
**Last verified:** 2026-07-09

## Corporate & product

| Document               | Path                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------- |
| ICP                    | [docs/ICP.md](../ICP.md)                                                           |
| 3-min demo video guide | [DEMO_VIDEO.md](./DEMO_VIDEO.md) (record MP4 → `investor/demo/`)                   |
| Architecture 1-pager   | [docs/architecture/ADR-011-context-map.md](../architecture/ADR-011-context-map.md) |

## Technical diligence

| Document                 | Path                                                                              |
| ------------------------ | --------------------------------------------------------------------------------- |
| Tech diligence pack      | [TECH_DILIGENCE_PACK.md](./TECH_DILIGENCE_PACK.md)                                |
| Monthly metrics cadence  | [METRICS_CADENCE.md](./METRICS_CADENCE.md)                                        |
| TAM / vertical expansion | [TAM_VERTICAL_EXPANSION.md](./TAM_VERTICAL_EXPANSION.md)                          |
| SIG Lite (enterprise)    | [../compliance/SIG_LITE.md](../compliance/SIG_LITE.md)                            |
| Metric snapshots         | [snapshots/](./snapshots/)                                                        |
| Silicon Valley checklist | [SILICON_VALLEY_READINESS_CHECKLIST.md](../SILICON_VALLEY_READINESS_CHECKLIST.md) |
| RBAC matrix              | [RBAC_MATRIX.md](../../docs/architecture/auth-clerk-spicedb.md)                   |
| Runbook                  | [RUNBOOK.md](../../RUNBOOK.md)                                                    |

## Live metrics (API)

| Metric             | Endpoint                         |
| ------------------ | -------------------------------- |
| Investor KPIs      | `GET /v1/admin/investor-metrics` |
| Platform adoption  | `GET /v1/admin/platform-metrics` |
| Monopoly / network | `GET /v1/admin/monopoly-metrics` |

## Financial (Phase 2)

- Stripe billing exports (frozen — do not change webhook config)
- Merchant contracts in admin pricing module
