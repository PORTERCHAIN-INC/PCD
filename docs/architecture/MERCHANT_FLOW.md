# Merchant Flow

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Source:** `merchant_engine/`, `routers/merchant.py`, `routers/merchant_api.py`, `gateway_engine/`  
**See also:** [DISPATCH_FLOW.md](./DISPATCH_FLOW.md) · [PAYMENT_FLOW.md](./PAYMENT_FLOW.md) · [MERCHANT_FLOW.md](MERCHANT_FLOW.md)

---

## Overview

Merchants authenticate via **Clerk** with organization context (`X-Merchant-Org-Id`, `X-Merchant-Role` headers). Portal requests go to `/v1/merchant/*`. Programmatic integrations use **`/v1/merchant-api/*`** with API keys (`X-Api-Key`) and scoped permissions (`shipments:read`, `shipments:write`, etc.).

No Stripe checkout — orders are created on **net terms** (`Merchant.billing_cycle`: NET_7, NET_14, etc.).

## Flow

| Stage                   | Service                                                    | Notes                                                                                    |
| ----------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Contract                | `MerchantContract` in `admin_models.py`, CRM `CrmContract` | `resolve_order_type(has_contract=True)` → `CONTRACT`                                     |
| Single booking (portal) | `MerchantBookingService.create_shipment()`                 | Order at `BOOKED`, immediate `transition_to_dispatch_ready()`                            |
| Single booking (API)    | Same service via `POST /v1/merchant-api/bookings`          | `order_source=MERCHANT` (API tag TODO)                                                   |
| Bulk CSV                | `MerchantBulkService` upload + confirm                     | `order_source=CSV`                                                                       |
| Operations              | Admin `ControlTowerService` / dispatch                     | Same Fleetbase path as retail                                                            |
| Billing                 | `MerchantBillingService` + `MerchantArService`             | Statement + invoice list; **admin Generate cycle invoices** + offline **Record payment** |
| API keys                | `MerchantApiKeyService` + `gateway_engine`                 | Keys stored; rate limits per key on `/v1/merchant-api/*`                                 |

## Webhook HMAC & Rate Limits

### Outbound merchant webhooks (HMAC verification)

When you create a webhook via `POST /v1/merchant/integrations/webhooks`, Porterchain returns a `signing_secret` in the response. Store it and use it to verify every outbound webhook delivery.

For each webhook delivery, Porterchain sends:

- HTTP `Content-Type: application/json`
- Headers:
  - `X-Porterchain-Timestamp`: unix timestamp in seconds (base-10)
  - `X-Porterchain-Signature`: hex-encoded HMAC-SHA256 signature
- Body: JSON payload delivered by Porterchain (event envelope + order fields)

Signature algorithm (match Porterchain exactly):

1. Serialize the delivered JSON body as Porterchain does:
   - `body_bytes = json.dumps(body, separators=(',', ':'), default=str).encode('utf-8')`
2. Build the signed message:
   - `signed = timestamp + '.' + body_bytes`
3. Compute:
   - `HMAC-SHA256(signing_secret, signed).hexdigest()`

Example (Python):

```python
import hashlib, hmac

timestamp = request.headers["X-Porterchain-Timestamp"]
signature = request.headers["X-Porterchain-Signature"]

body = request.json
body_bytes = json.dumps(body, separators=(",", ":"), default=str).encode("utf-8")
signed = f"{timestamp}.".encode("utf-8") + body_bytes
expected = hmac.new(signing_secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()

assert expected == signature
```

If verification fails, treat the delivery as untrusted (do not process it).

### Merchant API rate limits (per API key tier)

Merchant API endpoints live under `/v1/merchant-api/*` and require an API key in `X-Api-Key`.

Rate limits are enforced **per API key** (tier):

- Default: `rate_limit_per_minute = 60`
- If a key exceeds its limit, Porterchain returns:
  - HTTP `429`
  - JSON: `detail=rate_limit_exceeded`, `limit_per_minute`, `requests_last_minute`
  - Header: `Retry-After: 60`

Read and update limits:

- `GET /v1/merchant/integrations/rate-limits`
- `PATCH /v1/merchant/integrations/api-keys/{key_id}/rate-limit`

## Diagram

```mermaid
flowchart TD
  M[Merchant User<br/>Clerk + org headers] --> APP[Merchant Portal :3001]
  APP --> API["/v1/merchant/*"]
  API --> CTX[get_merchant_context<br/>merchant_engine/rbac]
  CTX --> CONTRACT[MerchantContract<br/>admin_models / CRM]
  CONTRACT --> BOOK[POST /bookings<br/>MerchantBookingService]
  BOOK --> ORD[Order BOOKED<br/>order_source=MERCHANT]
  BOOK --> DR[transition_to_dispatch_ready]
  BULK[POST /bulk/upload] --> CSV[MerchantBulkService<br/>order_source=CSV]
  CSV --> CONFIRM[POST /bulk/{id}/confirm]
  CONFIRM --> ORD
  ORD --> OPS[Admin Operations<br/>dispatch queue]
  OPS --> FB[order.dispatch_ready → Fleetbase]
  ORD --> BILL[MerchantBillingService<br/>statement + invoices]
  BILL --> LEDGER[billing_engine SettlementService<br/>retail Stripe path only]
  KEYS[Integrations UI] --> MAPI["/v1/merchant-api/*<br/>X-Api-Key + scopes"]
  MAPI --> GW[gateway_engine middleware<br/>usage + rate limits]
  GW --> BOOK
```

## PlantUML

See [plantuml/merchant_flow.puml](./plantuml/merchant_flow.puml)
---
