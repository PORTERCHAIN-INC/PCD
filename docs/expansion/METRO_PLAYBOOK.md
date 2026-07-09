# Metro expansion playbook (§9 · MON-G4)

**Type:** CANONICAL  
**Checklist:** MON-G4  
**Last verified:** 2026-07-09

## Sequence (after GTA ≥95% auto-dispatch)

| Metro         | Priority | Prerequisites                                         |
| ------------- | -------- | ----------------------------------------------------- |
| **Montreal**  | 1        | FR i18n complete, Valhalla tile build for QC corridor |
| **Vancouver** | 2        | PST ops window, cross-border customs doc (future)     |

## Clone checklist per metro

1. **Routing** — Valhalla tile extract + `ROUTING_ENGINE=valhalla` smoke on sample corridors
2. **Pricing** — rate card row for metro surcharge (`pricing_engine` admin)
3. **Drivers** — onboard 10+ active drivers in geo fence
4. **Merchants** — 2 pilot logos with vertical workflow (construction or medical)
5. **Marketing** — `/solutions/*` + localized homepage hero quote widget
6. **Legal** — carrier pool model unchanged; update SLA timezone footnote

## Metrics gate (approve expansion)

| Metric                 | Threshold                              |
| ---------------------- | -------------------------------------- |
| GTA auto-dispatch %    | ≥95% (`porterchain_auto_dispatch_pct`) |
| On-time delivery %     | ≥90%                                   |
| Fleetbase sync SLO     | ≥98% when bridge on                    |
| Support first response | <4h avg                                |

## Rollback

Disable metro in admin settings (`service_zones`) — quotes return `zone_unavailable` without affecting GTA.
