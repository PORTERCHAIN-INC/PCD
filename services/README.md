# Porterchain Services


**Type:** README
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Internal Python service layer — **not** customer-facing. All external clients talk to `apps/api/` only.

> **See also:** [REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) · [EXTENSION_GUIDE.md](../EXTENSION_GUIDE.md)

---

## Layout

| Path | Package | Purpose |
| ---- | ------- | ------- |
| `fleetbase-adapter/` | `porterchain-fleetbase-adapter` | **Sole Porterchain ↔ Fleetbase boundary** |
| `pricing-engine/` | `porterchain-pricing` | Quotes, contracts, promotions, tax |
| `driver-platform/` | `porterchain-driver` | Reusable driver domain services |
| `event-bus/` | `porterchain-event-bus` | Domain events, handlers, DLQ, idempotency |
| `python/porterchain_services/` | `porterchain-services` | Composition-root service modules |

Fleetbase HTTP must go **only** through `fleetbase-adapter/` — never from apps or UI.

---

## Fleetbase Adapter

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

See [services/fleetbase-adapter/README.md](./fleetbase-adapter/README.md) · [FLEETBASE_ADAPTER_ARCHITECTURE.md](../FLEETBASE_ADAPTER_ARCHITECTURE.md).

---

## Service Modules (`porterchain_services`)

| Module | Responsibility |
| ------ | -------------- |
| `gateway` | Composition root, service registry |
| `fleetbase` | Delegates to `fleetbase-adapter` |
| `stripe` | Payments |
| `maps` | Valhalla / OSRM routing |
| `notifications` | Email, SMS, push (queued) |
| `pricing` | Tariff engine protocol |
| `merchant` | B2B lifecycle |
| `driver` | Driver execution helpers |
| `dispatch` | Assignment |
| `customer` | Retail customer |
| `visitor` | Anonymous sessions, leads, abandoned checkout |

---

## Driver Platform

Reusable driver logic consumed by `apps/api/.../driver_engine/` and `/driver-api/v1/*`:

```
driver-platform/porterchain_driver/
├── jobs.py, stops.py, navigation.py, pod.py
├── shift.py, location.py, offline.py, push.py
└── platform.py  (DriverPlatform facade)
```

See [DRIVER_PLATFORM.md](../DRIVER_PLATFORM.md).

---

## Event Bus

```
event-bus/porterchain_event_bus/
├── bus.py          consume/publish
├── handlers/       default domain handlers
├── envelope.py     event envelope
├── idempotency.py  dedupe
├── retry.py, dlq.py
```

Wired in API lifespan and `apps/worker/run.py`.

See [EVENT_BUS.md](../EVENT_BUS.md).

---

## PYTHONPATH (local dev)

Root `pnpm dev:api` and `pnpm dev:worker` include:

- `apps/api/src`
- `shared/python`
- `services/python`
- `services/fleetbase-adapter`
- `services/pricing-engine`
- `services/event-bus`
- `services/driver-platform`

---

## Usage Example

```python
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings

adapter = FleetbaseAdapter(FleetbaseSettings(api_url="http://localhost:8000", api_key="..."))
```

```python
from porterchain_pricing import PricingService, PricingRequest, GeoPoint

service = PricingService()
breakdown = service.calculate_retail(PricingRequest(
    pickup=GeoPoint(lat=43.65, lng=-79.38),
    dropoff=GeoPoint(lat=43.70, lng=-79.40),
    vehicle_class="cargoVan",
))
```

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [pricing-engine/README.md](./pricing-engine/README.md) | Pricing engine detail |
| [FLEETBASE_INTEGRATION.md](../FLEETBASE_INTEGRATION.md) | Fleetbase integration |
| [PRICING_ENGINE.md](../PRICING_ENGINE.md) | Pricing architecture |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../masterrule.md](../masterrule.md) | Architecture SSOT |
| [../REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) | Monorepo layout |

