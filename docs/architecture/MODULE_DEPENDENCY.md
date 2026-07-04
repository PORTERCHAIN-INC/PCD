# Module Dependency

> **Source:** `package.json`, `pyproject.toml`, import graph across `apps/api`, `services/`, `packages/`

## Dependency Rules (masterrule.md)

```
UI → API routers only
Routers → *_engine services only
Services → repositories, adapters, event bus
Adapters → external HTTP only (no business rules)
```

## Python Module Graph

| Consumer | Depends On |
|----------|------------|
| `booking_engine` | `pricing_engine`, `fleetbase_engine`, `billing_engine`, `notification_engine`, `porterchain_services`, `porterchain_shared`, `porterchain_event_bus` |
| `merchant_engine` | `booking_engine` (transitions), `pricing_engine`, `fleetbase_engine` |
| `admin_engine` | All engines, `crm_models`, `porterchain_pricing` |
| `fleetbase_engine` | `fleetbase-adapter` via `services/fleetbase_integration.py` |
| `driver_engine` | `porterchain_driver`, `fleetbase_engine` bridge |
| `pricing_engine` | `services/pricing-engine/porterchain_pricing` |
| `apps/worker` | `porterchain_api.*`, `porterchain_event_bus`, `porterchain_shared` |

## TypeScript Package Graph

| App | Workspace packages |
|-----|-------------------|
| website | `@porterchain/maps`, `@porterchain/auth`, `@porterchain/types` |
| admin | `@porterchain/ui`, `@porterchain/maps`, `@porterchain/auth` |
| merchant-portal | `@porterchain/maps`, `@porterchain/auth` |
| driver-portal | `@porterchain/auth` |
| customer | `@porterchain/auth` |

## Forbidden Dependencies (verified)

- No frontend → `fleetbase-adapter` or Fleetbase `:8000`
- No router → direct Fleetbase HTTP (uses `fleetbase_engine`)
- Deprecated: `services/fleetbase/` shim — do not extend

## Diagram

```mermaid
flowchart TB
  subgraph UI["Frontends"]
    WEB[website]
    ADMIN[apps/admin]
    MERCH[apps/merchant-portal]
    DRV[apps/driver-portal]
    CUST[apps/customer]
  end

  subgraph API["apps/api/porterchain_api"]
    R[routers]
    BE[booking_engine]
    ME[merchant_engine]
    AE[admin_engine]
    FE[fleetbase_engine]
    DE[driver_engine]
    PE[pricing_engine]
    BLE[billing_engine]
    NE[notification_engine]
  end

  subgraph Libs["services/ + shared/"]
    FBA[fleetbase-adapter]
    EB[event-bus]
    PRICING[pricing-engine]
    DRVPLAT[driver-platform]
    PSVC[porterchain_services]
    SHARED[porterchain_shared]
  end

  subgraph PKGS["packages/"]
    MAPS[@porterchain/maps]
    AUTH[@porterchain/auth]
    EVENTS[@porterchain/events]
  end

  WEB & ADMIN & MERCH & CUST --> R
  DRV --> R
  R --> BE & ME & AE & DE
  BE --> PE & BLE & NE & FE
  ME --> PE & FE & BLE
  AE --> PE & BLE & NE & FE
  DE --> FE & DRVPLAT
  PE --> PRICING
  BE & AE & ME --> PSVC
  FE & DE --> FBA
  BE & ME & AE --> EB
  EB --> SHARED
  PSVC --> SHARED
  FBA --> SHARED
  WEB & ADMIN & MERCH --> MAPS
  WEB & ADMIN & MERCH --> AUTH
  WEB & ADMIN & MERCH --> EVENTS
```

## PlantUML

See [plantuml/module_dependency.puml](./plantuml/module_dependency.puml)
