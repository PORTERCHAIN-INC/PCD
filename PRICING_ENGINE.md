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

Distance for pricing comes from **`resolve_route_distance()`** (road network via `MapsService`, haversine fallback). Dispatch simulation uses Fleetbase + MapsService — not the pricing engine.

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

## Quote math (GTA delivery rate matrix)

Retail quotes use `porterchain_pricing.gta_rate`:

1. Vehicle base covers up to **20 km** (`sedan` $45 … `box_truck` $125)
2. Extra km beyond 20 × vehicle `extra_km_rate`
3. Extra pickups (`total_pickups - 1`) × $20; extra drops (`total_drops - 1`) × $15
4. Flat location surcharges once each: downtown **$25**, Markham/North York **$15**

Example: `large_van`, 18 km, 1 pickup, 15 drops → **$285.00**

Vehicle aliases: `cargoVan`→`small_van`, `highRoof`/`sprinter_van`→`large_van`, `box16`/`box20`→`box_truck`.
Additional quote stops count as extra drops. HST only if `pricing_tax` is configured (default 0).

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

| Document                                                                 | Purpose            |
| ------------------------------------------------------------------------ | ------------------ |
| [PORTERCHAIN_CHARTER.md](./docs/PORTERCHAIN_CHARTER.md)                  | Product scope      |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) | Execution boundary |

---
