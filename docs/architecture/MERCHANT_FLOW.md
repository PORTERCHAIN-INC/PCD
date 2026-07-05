# Merchant Flow

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Source:** `merchant_engine/`, `routers/merchant.py`, `routers/merchant_api.py`, `gateway_engine/`  
**See also:** [DISPATCH_FLOW.md](./DISPATCH_FLOW.md) · [PAYMENT_FLOW.md](./PAYMENT_FLOW.md) · [MERCHANT_PRODUCTION_READINESS.md](../../MERCHANT_PRODUCTION_READINESS.md)

---

## Overview

Merchants authenticate via **Clerk** with organization context (`X-Merchant-Org-Id`, `X-Merchant-Role` headers). Portal requests go to `/v1/merchant/*`. Programmatic integrations use **`/v1/merchant-api/*`** with API keys (`X-Api-Key`) and scoped permissions (`shipments:read`, `shipments:write`, etc.).

No Stripe checkout — orders are created on **net terms** (`Merchant.billing_cycle`: NET_7, NET_14, etc.).

## Flow

| Stage                   | Service                                                    | Notes                                                           |
| ----------------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| Contract                | `MerchantContract` in `admin_models.py`, CRM `CrmContract` | `resolve_order_type(has_contract=True)` → `CONTRACT`            |
| Single booking (portal) | `MerchantBookingService.create_shipment()`                 | Order at `BOOKED`, immediate `transition_to_dispatch_ready()`   |
| Single booking (API)    | Same service via `POST /v1/merchant-api/bookings`          | `order_source=MERCHANT` (API tag TODO)                          |
| Bulk CSV                | `MerchantBulkService` upload + confirm                     | `order_source=CSV`                                              |
| Operations              | Admin `ControlTowerService` / dispatch                     | Same Fleetbase path as retail                                   |
| Billing                 | `MerchantBillingService`                                   | Statement + invoice list; batch invoice run **not implemented** |
| API keys                | `MerchantApiKeyService` + `gateway_engine`                 | Keys stored; rate limits per key on `/v1/merchant-api/*`        |

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

## Governance

| Document                                         | Role              |
| ------------------------------------------------ | ----------------- |
| [masterrule.md](../../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
