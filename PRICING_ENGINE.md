# Porterchain Pricing & Contract Engine

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `porterchain-pricing` at `services/pricing-engine/`  
**Rule:** Fleetbase never calculates prices. Porterchain owns all pricing logic.

> **Package README:** [services/pricing-engine/README.md](./services/pricing-engine/README.md) · **Routing input:** [OSRM_USAGE.md](./OSRM_USAGE.md) · [VALHALLA_USAGE.md](./VALHALLA_USAGE.md)

---

## Architecture

```
Website / Merchant Portal / Customer app
         │
         ▼
   Porterchain API (:8001)
         │
         ├── services/routing.py → resolve_route_distance()  (Valhalla/OSRM)
         ├── pricing_engine/ → SqlAlchemyPricingRepository
         └── services/pricing.py → bridge to porterchain_pricing
         │
         ▼
services/pricing-engine/          ← all pricing logic
         │
         ▼
   Quote / Order amount_cents     (Porterchain PostgreSQL)
         │
         ▼
services/fleetbase-adapter/       ← execution only, no pricing
```

Distance for pricing comes from **`resolve_route_distance()`** (road network via `MapsService`, haversine fallback). Route Center simulation uses separate `MapsService` calls — not the pricing engine.

---

## Services

| Service              | Module               | Responsibility                                                 |
| -------------------- | -------------------- | -------------------------------------------------------------- |
| **PricingService**   | `pricing_service.py` | B2C + B2B facade                                               |
| **ContractService**  | `contract/`          | Merchant contracts, lanes, zones, flat rates, volume discounts |
| **PromotionService** | `promotion/`         | Promo codes, wallet/referral credits, coupons                  |
| **TaxService**       | `tax/`               | HST and tax exemptions                                         |
| **ZoneService**      | `zone/`              | GTA zone resolution and multipliers                            |
| **PricingSimulator** | `simulator.py`       | Admin preview with rule overrides                              |
| **PricingEngine**    | `engine/`            | Core calculation pipeline                                      |
| **distance**         | `distance.py`        | Haversine helpers (`haversine_meters`, `total_route_meters`)   |

---

## Individual (B2C) pricing inputs

- Pickup / dropoff (distance via routing bridge, zone)
- Vehicle type (sedan → 20ft box truck)
- Package weight and dimensions
- Declared value coverage
- Rush vs scheduled delivery
- Extra stops
- Fuel surcharge
- HST
- Minimum charge
- Promo codes and credits

---

## Merchant (B2B) pricing inputs

- Contract pricing (`merchant_contracts` + `merchants.pricing_config`)
- Zone and lane pricing
- Vehicle-specific contract rates
- Flat rates per service type
- Volume discounts
- Weekend / holiday multipliers
- Custom rules JSON
- Minimum monthly commitment / minimum charge

---

## Price breakdown

Every calculation returns:

| Field            | Description                    |
| ---------------- | ------------------------------ |
| `base_cents`     | Base / minimum delivery charge |
| `distance_cents` | Distance component             |
| `vehicle_cents`  | Vehicle class surcharge        |
| `weight_cents`   | Heavy weight surcharge         |
| `fuel_cents`     | Fuel surcharge %               |
| `tax_cents`      | HST                            |
| `discount_cents` | Promos + merchant discounts    |
| `final_cents`    | Total charged                  |

Line items in `items[]` with `code`, `label`, `amount_cents`.

---

## Admin API

Prefix: **`/v1/admin/pricing`** (in `routers/admin.py`)

| Endpoint                       | Purpose            |
| ------------------------------ | ------------------ |
| `GET/POST /pricing/tariffs`    | Tariff rules       |
| `GET/POST /pricing/promotions` | Promo codes        |
| `GET/POST /pricing/zones`      | Geographic zones   |
| `GET/POST /pricing/contracts`  | Merchant contracts |
| `POST /pricing/simulate`       | Pricing simulator  |
| `GET/PUT /pricing/tax`         | Tax configuration  |
| `GET/PUT /pricing/fuel`        | Fuel surcharge     |
| `GET /pricing/dashboard`       | Admin pricing KPIs |

Factory: `apps/api/src/porterchain_api/pricing_engine/__init__.py` → `get_pricing_service(db)`

---

## Integration points

| Flow                    | File                                                              |
| ----------------------- | ----------------------------------------------------------------- |
| Website / retail quotes | `apps/api/src/porterchain_api/booking_engine/quote_service.py`    |
| Merchant bookings       | `apps/api/src/porterchain_api/merchant_engine/booking_service.py` |
| Pricing bridge          | `apps/api/src/porterchain_api/services/pricing.py`                |
| Routing distance input  | `apps/api/src/porterchain_api/services/routing.py`                |
| DB rules loader         | `apps/api/src/porterchain_api/pricing_engine/repository.py`       |
| Website vehicle mapping | `website/src/lib/pricing/vehicle-map.ts`                          |

---

## Install

```bash
cd apps/api && pip install -e ../../services/pricing-engine
pnpm dev:api
```

---

## Related documents

| Document                                                                 | Purpose                                  |
| ------------------------------------------------------------------------ | ---------------------------------------- |
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)                     | Product scope                            |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) | Execution boundary                       |
| [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md)           | Route simulation (separate from pricing) |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
