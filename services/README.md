# Porterchain Services

Internal service layer — **not** customer-facing. All external clients talk to `apps/api/` only.

## Layout

| Path | Purpose |
|------|---------|
| `fleetbase-adapter/` | **Fleetbase adapter** — sole Porterchain ↔ Fleetbase boundary |
| `pricing-engine/` | **Pricing & Contract Engine** — all quote/booking pricing |
| `fleetbase/` | Deprecated shim — re-exports `fleetbase-adapter` |
| `python/porterchain_services/` | Python service modules (Fleetbase, Stripe, Maps, …) |

## Fleetbase adapter

All Fleetbase HTTP communication goes through `services/fleetbase-adapter/`:

```
fleetbase-adapter/porterchain_fleetbase_adapter/
├── client/       FleetbaseClient
├── auth/         FleetbaseSsoClient
├── orders/       OrderService
├── drivers/      DriverService
├── vehicles/     VehicleService
├── dispatch/     DispatchService
├── tracking/     TrackingService
├── routes/       RouteService
├── webhooks/     WebhookService
├── events/       EventTranslator
└── pod/          PodService
```

See [FLEETBASE_ADAPTER_ARCHITECTURE.md](../FLEETBASE_ADAPTER_ARCHITECTURE.md).

## Service modules

| Module | Boundary |
|--------|----------|
| `gateway` | Composition root, service registry |
| `fleetbase` | Delegates to `fleetbase-adapter` |
| `stripe` | Payments |
| `maps` | Valhalla / OSRM routing |
| `notifications` | Email, SMS, push (queued) |
| `pricing` | Tariff engine protocol |
| `merchant` | B2B lifecycle |
| `driver` | Driver execution |
| `dispatch` | Assignment |
| `customer` | Retail customer |
| `visitor` | Anonymous sessions, leads, abandoned checkout |

## Usage

```python
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings

adapter = FleetbaseAdapter(FleetbaseSettings(api_url="http://localhost:8000", api_key="..."))
adapter.sync_order({...})
```

PYTHONPATH: `shared/python` + `services/python` + `services/fleetbase-adapter` + `services/fleetbase` (see `pnpm dev:api`).

## Documentation

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](../FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md)
- [EXTENSION_GUIDE.md](../EXTENSION_GUIDE.md)
