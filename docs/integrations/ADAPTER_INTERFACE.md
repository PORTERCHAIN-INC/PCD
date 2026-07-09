# ERP / platform integration adapter interface (§7 · PLT-G4)

**Type:** CANONICAL  
**Checklist:** PLT-G4  
**ADR:** [ADR-015](../architecture/ADR-015-sap-connector-deferred.md)  
**Last verified:** 2026-07-09

## Contract

All third-party order sources map **external payloads → `MerchantBookDeliveryRequest`** (or gateway order create) through a named adapter module under `porterchain_api.integrations.*_adapter`.

| Rule                            | Meaning                                                               |
| ------------------------------- | --------------------------------------------------------------------- |
| **No HTTP in adapters**         | Adapters are pure mapping + validation; HTTP lives in routers/workers |
| **Stable function names**       | `map_<source>_fulfillment(payload) -> MerchantBookDeliveryRequest`    |
| **Setup bundle**                | `*_setup_bundle()` returns merchant integration metadata              |
| **Version in module docstring** | Breaking field changes bump adapter module version comment            |

## Reference implementation

| Adapter       | Module                             | Status       |
| ------------- | ---------------------------------- | ------------ |
| NetSuite      | `integrations/netsuite_adapter.py` | MVP — §7.2.3 |
| Zapier        | merchant integrations console      | Event fanout |
| Shopify / Woo | deferred §7.2.1–7.2.2              | Not started  |

## Adding a new adapter

1. Create `apps/api/src/porterchain_api/integrations/<vendor>_adapter.py`
2. Implement `map_<vendor>_fulfillment` + tests in `tests/test_<vendor>_*.py`
3. Wire merchant `integrations_service.py` action — no direct router imports
4. Document field mapping in `integrations/<vendor>/README.md`
5. Run `pnpm validate:integration-adapter`

## Stability window

Interface frozen for **2 quarters** after first prod merchant uses an adapter. Breaking changes require:

- ADR amendment
- Migration note in `PARTNER_GUIDE.md`
- Dual-read period or versioned webhook topic
