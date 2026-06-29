# Porterchain Pricing & Contract Engine

**Package:** `porterchain-pricing` at `services/pricing-engine/`  
**Rule:** Fleetbase never calculates prices. Porterchain owns all pricing logic.

---

## Architecture

```
Website / Merchant Portal
         │
         ▼
   Porterchain API (:8001)
         │
         ▼
services/pricing-engine/          ← all pricing logic
         │
         ▼
   Quote / Order amount_cents     (stored in Porterchain DB)
         │
         ▼
services/fleetbase-adapter/       ← execution only, no pricing
```

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

---

## Individual (B2C) pricing inputs

- Pickup / dropoff (distance, zone)
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

- Contract pricing (`merchant_contracts` table + `merchants.pricing_config`)
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

Line items are in `items[]` with `code`, `label`, `amount_cents`.

---

## Admin API

| Endpoint                                | Purpose                      |
| --------------------------------------- | ---------------------------- |
| `GET/POST /v1/admin/pricing/tariffs`    | Tariff rules                 |
| `GET/POST /v1/admin/pricing/promotions` | Promo codes                  |
| `GET/POST /v1/admin/pricing/zones`      | Geographic zones             |
| `GET/POST /v1/admin/pricing/contracts`  | Merchant contracts           |
| `POST /v1/admin/pricing/simulate`       | Pricing simulator            |
| `GET/PUT /v1/admin/pricing/tax`         | Tax configuration            |
| `GET/PUT /v1/admin/pricing/fuel`        | Fuel surcharge configuration |

---

## Integration points

| Flow              | File                                          |
| ----------------- | --------------------------------------------- |
| Website quotes    | `apps/api/booking_engine/quote_service.py`    |
| Merchant bookings | `apps/api/merchant_engine/booking_service.py` |
| DB rules loader   | `apps/api/pricing_engine/repository.py`       |
| Legacy bridge     | `apps/api/services/pricing.py`                |

---

## Install

```bash
cd apps/api && pip install -e ../../services/pricing-engine
pnpm dev:api
```

---

## Related documents

- [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)
- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [services/pricing-engine/README.md](./services/pricing-engine/README.md)
