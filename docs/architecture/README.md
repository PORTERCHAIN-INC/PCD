# Porterchain Architecture Documentation

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** [masterrule.md](../../masterrule.md) v3.1

Code-derived flow diagrams and topology. **Canonical topology:** [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md).

---

## Documents

| #   | Document                                               | Description                                 |
| --- | ------------------------------------------------------ | ------------------------------------------- |
| 1   | [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)     | Complete system topology                    |
| 2   | [APPLICATION_FLOW.md](./APPLICATION_FLOW.md)           | Request flow: UI → API → Services → Adapter |
| 3   | [BOOKING_FLOW.md](./BOOKING_FLOW.md)                   | Retail visitor → delivery lifecycle         |
| 4   | [MERCHANT_FLOW.md](./MERCHANT_FLOW.md)                 | B2B merchant → billing path                 |
| 5   | [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)             | Order state machine (diagram)               |
| 6   | [DISPATCH_FLOW.md](./DISPATCH_FLOW.md)                 | Operations → driver → tracking → POD        |
| 7   | [PAYMENT_FLOW.md](./PAYMENT_FLOW.md)                   | Stripe → webhook → billing                  |
| 8   | [EVENT_BUS_FLOW.md](./EVENT_BUS_FLOW.md)               | Domain events and handlers                  |
| 9   | [MODULE_DEPENDENCY.md](./MODULE_DEPENDENCY.md)         | Package dependency graph                    |
| 10  | [API_DEPENDENCY.md](./API_DEPENDENCY.md)               | Client ↔ API ↔ external systems             |
| 11  | [DATABASE_RELATIONSHIP.md](./DATABASE_RELATIONSHIP.md) | Entity relationships                        |
| 12  | [GOOGLE_MAPS_FLOW.md](./GOOGLE_MAPS_FLOW.md)           | Google Maps (viz/autocomplete)              |
| 13  | [OSRM_FLOW.md](./OSRM_FLOW.md)                         | OSRM distance/ETA                           |
| 14  | [VALHALLA_FLOW.md](./VALHALLA_FLOW.md)                 | Valhalla route optimization                 |
| 15  | [FLEETBASE_FLOW.md](./FLEETBASE_FLOW.md)               | Fleetbase adapter boundary                  |
| 16  | [NOTIFICATION_FLOW.md](./NOTIFICATION_FLOW.md)         | Notification pipeline                       |
| 17  | [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md)     | Clerk + driver JWT                          |
| 18  | [REALTIME_FLOW.md](./REALTIME_FLOW.md)                 | WebSocket live map                          |
| 19  | [REPORTING_FLOW.md](./REPORTING_FLOW.md)               | Admin/merchant reporting                    |
| 20  | [ADMIN_CONTROL_TOWER.md](./ADMIN_CONTROL_TOWER.md)     | Admin ops communication                     |
| 21  | [ADR-012-scaling.md](./ADR-012-scaling.md)             | Horizontal scale path (DD-03)               |
| 22  | [ADR-013-secrets.md](./ADR-013-secrets.md)             | Secret manager (DD-14)                      |

---

## Validation

[ARCHITECTURE_VALIDATION_REPORT.md](./ARCHITECTURE_VALIDATION_REPORT.md) — compliance vs masterrule.md.

---

## Diagram sources

| Format   | Path                     |
| -------- | ------------------------ |
| Mermaid  | [mermaid/](./mermaid/)   |
| PlantUML | [plantuml/](./plantuml/) |

Diagrams use **PostgreSQL 16** for Porterchain data (SQLite removed July 2026).

---

## Ports (local dev)

| Service         | Port |
| --------------- | ---- |
| Website         | 3000 |
| Merchant portal | 3001 |
| Admin portal    | 3002 |
| Driver portal   | 3003 |
| Customer portal | 3004 |
| Porterchain API | 8001 |
| Fleetbase API   | 8000 |
| Valhalla        | 8002 |

See [PORT_CONFIGURATION.md](../../PORT_CONFIGURATION.md).

---

## Related (root)

| Document                                 | Purpose                  |
| ---------------------------------------- | ------------------------ |
| [docs/README.md](../README.md)           | Full documentation index |
| [DOMAIN_MODEL.md](../../DOMAIN_MODEL.md) | Domain specification     |

---

## Governance

| Document                                                       | Role              |
| -------------------------------------------------------------- | ----------------- |
| [../../masterrule.md](../../masterrule.md)                     | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
