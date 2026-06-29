# Porterchain Pricing & Contract Engine

**Package:** `porterchain-pricing` at `services/pricing-engine/`  
**Rule:** Fleetbase never calculates prices. Porterchain owns all pricing logic.

## Modules

| Module | Class | Responsibility |
|--------|-------|----------------|
| `pricing_service.py` | `PricingService` | Main facade for B2C + B2B |
| `contract/` | `ContractService` | Merchant contracts, lanes, zones, flat rates |
| `promotion/` | `PromotionService` | Promo codes, credits, coupons |
| `tax/` | `TaxService` | HST / tax calculation |
| `zone/` | `ZoneService` | Geographic zone resolution |
| `engine/` | `PricingEngine` | Core calculation pipeline |
| `simulator.py` | `PricingSimulator` | Admin preview with overrides |

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

## API integration

- Website quotes: `apps/api/booking_engine/quote_service.py`
- Merchant bookings: `apps/api/merchant_engine/booking_service.py`
- Admin simulator: `POST /v1/admin/pricing/simulate`
- DB rules: `apps/api/pricing_engine/repository.py`

## Install

```bash
cd apps/api && pip install -e ../../services/pricing-engine
```
