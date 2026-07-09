# NetSuite MVP integration (§7.2.3)

**Checklist:** §7.2.3 · ADR-015  
**Status:** Dev MVP — SuiteScript RESTlet → Porterchain merchant API  
**API:** `POST /v1/merchant/integrations/netsuite/sync`

## Overview

NetSuite item fulfillments export to Porterchain as same-day shipments. The MVP uses a **field mapping adapter** (`porterchain_api.integrations.netsuite_adapter`) — no SuiteApp certification required for dev/CI.

## NetSuite → Porterchain flow

1. Item fulfillment approved in NetSuite.
2. SuiteScript RESTlet POSTs JSON to Porterchain (or middleware).
3. Porterchain maps `external_id`, ship/pickup addresses, and `ship_date` → `MerchantBookDeliveryRequest`.
4. Outbound webhooks (`order.delivered`, `order.tracking_updated`) push status back to NetSuite (custom record or RESTlet callback).

## Setup (dev)

1. Merchant portal → **Integrations → API Keys** — production key with `shipments:write`.
2. `POST /v1/merchant/integrations/netsuite/connect` with `account_id` (stores connection in merchant profile).
3. Point NetSuite RESTlet at `POST /v1/merchant/integrations/netsuite/sync` with Bearer API key or portal session.
4. Sample payload: [`samples/fulfillment.json`](./samples/fulfillment.json).

## Field mapping

| NetSuite field             | Porterchain field       |
| -------------------------- | ----------------------- |
| `external_id` / `tranid`   | `internal_reference`    |
| `purchase_order`           | `purchase_order_number` |
| `ship_address` + lat/lng   | `dropoff`               |
| `pickup_address` + lat/lng | `pickup`                |
| `ship_date`                | `scheduled_at`          |
| `memo`                     | `special_instructions`  |
| `subsidiary`               | `cost_centre`           |

See [`inbound.schema.json`](./inbound.schema.json) for the RESTlet contract.
