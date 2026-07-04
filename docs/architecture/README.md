# Porterchain Architecture Documentation

> Reverse-engineered from source code. Reference: [masterrule.md](../../masterrule.md) v3.1

## Documents

| #   | Document                                               | Description                                 |
| --- | ------------------------------------------------------ | ------------------------------------------- |
| 1   | [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)     | Complete system topology                    |
| 2   | [APPLICATION_FLOW.md](./APPLICATION_FLOW.md)           | Request flow: UI → API → Services → Adapter |
| 3   | [BOOKING_FLOW.md](./BOOKING_FLOW.md)                   | Retail visitor → delivery lifecycle         |
| 4   | [MERCHANT_FLOW.md](./MERCHANT_FLOW.md)                 | B2B merchant → billing path                 |
| 5   | [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)             | Order state machine                         |
| 6   | [DISPATCH_FLOW.md](./DISPATCH_FLOW.md)                 | Operations → driver → tracking → POD        |
| 7   | [PAYMENT_FLOW.md](./PAYMENT_FLOW.md)                   | Stripe → webhook → billing                  |
| 8   | [EVENT_BUS_FLOW.md](./EVENT_BUS_FLOW.md)               | Domain events and handlers                  |
| 9   | [MODULE_DEPENDENCY.md](./MODULE_DEPENDENCY.md)         | Package dependency graph                    |
| 10  | [API_DEPENDENCY.md](./API_DEPENDENCY.md)               | Client ↔ API ↔ external systems             |
| 11  | [DATABASE_RELATIONSHIP.md](./DATABASE_RELATIONSHIP.md) | Entity relationships                        |
| 12  | [GOOGLE_MAPS_FLOW.md](./GOOGLE_MAPS_FLOW.md)           | Google Maps usage (viz/autocomplete)        |
| 13  | [OSRM_FLOW.md](./OSRM_FLOW.md)                         | OSRM distance calculations                  |
| 14  | [VALHALLA_FLOW.md](./VALHALLA_FLOW.md)                 | Valhalla route optimization path            |
| 15  | [FLEETBASE_FLOW.md](./FLEETBASE_FLOW.md)               | Fleetbase adapter responsibilities          |
| 16  | [NOTIFICATION_FLOW.md](./NOTIFICATION_FLOW.md)         | Notification engine pipeline                |
| 17  | [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md)     | Clerk + driver JWT auth                     |
| 18  | [REALTIME_FLOW.md](./REALTIME_FLOW.md)                 | WebSocket live map                          |
| 19  | [REPORTING_FLOW.md](./REPORTING_FLOW.md)               | Admin/merchant reporting                    |
| 20  | [ADMIN_CONTROL_TOWER.md](./ADMIN_CONTROL_TOWER.md)     | Admin module communication                  |

## Validation

[ARCHITECTURE_VALIDATION_REPORT.md](./ARCHITECTURE_VALIDATION_REPORT.md) — compliance scores and gap analysis vs masterrule.md.

## Diagram Sources

- Mermaid: [mermaid/](./mermaid/)
- PlantUML: [plantuml/](./plantuml/)

## Ports (Local Dev)

| Service         | Port |
| --------------- | ---- |
| Website         | 3000 |
| Merchant Portal | 3001 |
| Admin Portal    | 3002 |
| Driver Portal   | 3003 |
| Customer Portal | 3004 |
| Porterchain API | 8001 |
| Fleetbase API   | 8000 |
| Valhalla        | 8002 |
