# Porterchain Pricing & Contract Engine


**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `porterchain-pricing` at `services/pricing-engine/`

**Rule:** Fleetbase never calculates prices. Porterchain owns all pricing logic (masterrule §11).

---

## Modules

| Module | Class | Responsibility |
| ------ | ----- | -------------- |
| `pricing_service.py` | `PricingService` | Main facade for B2C + B2B |
| `contract/` | `ContractService` | Merchant contracts, lanes, zones, flat rates |
| `promotion/` | `PromotionService` | Promo codes, credits, coupons |
| `tax/` | `TaxService` | HST / tax calculation |
| `zone/` | `ZoneService` | Geographic zone resolution |
| `engine/` | `PricingEngine` | Core calculation pipeline |
| `simulator.py` | `PricingSimulator` | Admin preview with overrides |
| `repository.py` | Protocol + in-memory | DB adapter interface |
| `catalog.py`, `distance.py` | Helpers | Vehicle catalog, distance |

---

## Usage

```python
from porterchain_pricing import PricingService, PricingRequest, GeoPoint

service = PricingService()
breakdown = service.calculate_retail(PricingRequest(
    pickup=GeoPoint(lat=43.65, lng=-79.38),
    dropoff=GeoPoint(lat=43.70, lng=-79.40),
    vehicle_class="cargoVan",
))
print(breakdown.final_cents, breakdown.items)
```

With PostgreSQL rules:

```python
from porterchain_api.pricing_engine import get_pricing_service

service = get_pricing_service(db)
```

---

## API Integration

| Consumer | Path | Notes |
| -------- | ---- | ----- |
| Website / retail quotes | `booking_engine/quote_service.py` | `POST /v1/quotes` |
| Merchant bookings | `merchant_engine/booking_service.py` | Net terms / B2B |
| Admin simulator | `admin_engine/pricing_service.py` | `POST /v1/admin/pricing/simulate` |
| DB repository | `apps/api/pricing_engine/repository.py` | `SqlAlchemyPricingRepository` |

---

## Install (editable)

```bash
cd apps/api && source .venv/bin/activate
pip install -e ../../services/pricing-engine
```

Included automatically when using root `pnpm dev:api` PYTHONPATH.

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [../README.md](../README.md) | Services overview |
| [../../PRICING_ENGINE.md](../../PRICING_ENGINE.md) | Architecture |
| [../../docs/architecture/PAYMENT_FLOW.md](../../docs/architecture/PAYMENT_FLOW.md) | Payment/pricing flow |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../masterrule.md](../../masterrule.md) | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

