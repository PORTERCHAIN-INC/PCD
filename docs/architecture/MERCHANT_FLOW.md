# Merchant Flow

> **Source:** `merchant_engine/`, `routers/merchant.py`, `merchant_models.py`

## Overview

Merchants authenticate via **Clerk** with organization context (`X-Merchant-Org-Id`, `X-Merchant-Role` headers). All requests go to `/v1/merchant/*`. No Stripe checkout — orders are created on **net terms** (`Merchant.billing_cycle`: NET_7, NET_14, etc.).

## Flow

| Stage          | Service                                                    | Notes                                                           |
| -------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| Contract       | `MerchantContract` in `admin_models.py`, CRM `CrmContract` | `resolve_order_type(has_contract=True)` → `CONTRACT`            |
| Single booking | `MerchantBookingService.create_shipment()`                 | Order at `BOOKED`, immediate `transition_to_dispatch_ready()`   |
| Bulk CSV       | `MerchantBulkService` upload + confirm                     | `order_source=CSV`                                              |
| Operations     | Admin `ControlTowerService` / dispatch                     | Same Fleetbase path as retail                                   |
| Billing        | `MerchantBillingService`                                   | Statement + invoice list; batch invoice run **not implemented** |
| API keys       | `MerchantApiKeyService`                                    | Keys stored; **no `/v1/merchant-api` auth router**              |

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
  BILL --> LEDGER[billing_engine SettlementService<br/>via payment.succeeded for retail only]
  M --> KEYS[MerchantApiKeyService<br/>keys stored, no auth router]
```

## PlantUML

See [plantuml/merchant_flow.puml](./plantuml/merchant_flow.puml)
