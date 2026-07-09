# Shopify integration (Porterchain merchant API)

**Checklist:** §7.2.1  
**Status:** Dev scaffold — connect via custom app + Porterchain API keys  
**API:** `/v1/merchant-api/*` · webhooks · HMAC signatures

## Overview

Merchants install a **custom Shopify app** that forwards orders to Porterchain using sandbox or production API keys. Fulfillment status and tracking flow back via webhooks and the merchant integrations console.

## Setup (dev)

1. Create a custom app in Shopify Admin → **Develop apps**.
2. In Porterchain merchant portal → **Integrations → Marketplace**, generate a `pk_sandbox_` API key with scopes `shipments:read`, `shipments:write`, `tracking:read`.
3. Configure Shopify webhooks to POST order events to your middleware, which calls `POST /v1/merchant-api/shipments`.
4. Register Porterchain webhooks for `shipment.delivered` to write fulfillments back to Shopify.

## Files (planned)

| Path                 | Purpose                             |
| -------------------- | ----------------------------------- |
| `app.toml`           | Shopify CLI app manifest            |
| `src/webhooks.ts`    | Order create → Porterchain shipment |
| `src/fulfillment.ts` | Tracking → Shopify fulfillment      |

See [PARTNER_GUIDE.md](../../docs/api/PARTNER_GUIDE.md) and `gateway_engine/merchant_api.py` ERP readiness for capabilities.
