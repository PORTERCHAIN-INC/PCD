# Partner API (API-key)

**Type:** POINTER · **Verified:** 2026-09-16

Programmatic merchant integrations use **`/v1/merchant-api/*`**, not Clerk `/v1/merchant/*`. Auth is the interface (API key + optional `Idempotency-Key`). Do not merge this prefix into the portal.

OpenAPI: `http://localhost:8001/docs` · snapshot [`openapi.json`](openapi.json)

| Method | Path                                       | Scope             |
| ------ | ------------------------------------------ | ----------------- |
| POST   | `/v1/merchant-api/bookings`                | `shipments:write` |
| GET    | `/v1/merchant-api/orders`                  | `shipments:read`  |
| GET    | `/v1/merchant-api/orders/{id}`             | `shipments:read`  |
| GET    | `/v1/merchant-api/track/{tracking_number}` | `shipments:read`  |
| POST   | `/v1/merchant-api/orders/{id}/cancel`      | `shipments:write` |
| GET    | `/v1/merchant-api/rate-card`               | `shipments:read`  |
| POST   | `/v1/merchant-api/quotes`                  | `shipments:read`  |

Shopify, NetSuite, and other **integrations** enqueue through this API (or Clerk portal ingest). ERP adapter protocol: `apps/api/src/porterchain_api/integrations/`.

Header: `Authorization: Bearer <api_key>`. Optional `X-Porterchain-Channel` for source tagging.

## Sandbox vs production

| Concern             | Sandbox                                           | Production               |
| ------------------- | ------------------------------------------------- | ------------------------ |
| API key prefix      | `pk_sandbox_…`                                    | `pk_production_…`        |
| Booking             | `is_sandbox=true` on order; no Fleetbase dispatch | Live capacity            |
| Public `/track/{n}` | 404 (not a live shipment)                         | Resolves                 |
| Labels PDF          | TEST watermark                                    | Clean                    |
| Webhooks            | Deliver only to hooks with `environment=sandbox`  | `environment=production` |
| Idempotency         | Scoped per merchant + key + `is_sandbox`          | Same, live env           |

**Go-live checklist**

1. Create a `pk_sandbox_` key and a sandbox webhook URL.
2. Book a test shipment (`sandbox` key or portal Test mode).
3. Run the lifecycle simulator (Integrations → Sandbox → `simulate_lifecycle`, or `POST /v1/merchant/integrations/sandbox/simulate`) to walk BOOKED → POD_COMPLETED and receive signed `order.*` fixtures.
4. Verify HMAC: `X-Porterchain-Signature` = hex(HMAC-SHA256(secret, `{timestamp}.` + raw body)); timestamp in `X-Porterchain-Timestamp`.
5. Mint a production key (**Owner only**) and a production webhook only after handlers pass.
6. Portal “test preference” is a reminder banner — it does **not** force Partner API dry-run; the key environment does.

Sandbox API keys use a separate Redis rate-limit traffic class (`merchant_api_sandbox`) so test scripts cannot burn the production key’s quota.

Example webhook body (`order.delivered`):

```json
{
  "event_type": "order.delivered",
  "order_id": "…",
  "order_number": "…",
  "tracking_number": "…",
  "state": "DELIVERED",
  "merchant_id": "…",
  "is_sandbox": true,
  "occurred_at": "2026-09-16T00:00:00+00:00",
  "payload": { "simulator": true }
}
```
