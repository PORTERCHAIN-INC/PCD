# Merchant Portal — Component Matrix

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) · [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)

Maps portal surfaces to API endpoints, application services, and models.

**Legend:** ✅ Wired end-to-end · ⚠ Partial · ❌ Missing · 🔑 API key auth

---

## 1. UI → API → Service matrix

| Portal route   | UI component         | API endpoint                                 | Service                                                | Model                               |
| -------------- | -------------------- | -------------------------------------------- | ------------------------------------------------------ | ----------------------------------- |
| `/dashboard`   | `DashboardClient`    | `GET /v1/merchant/dashboard`                 | `MerchantDashboardService`                             | `Order`, `Invoice` aggregates       |
| `/dashboard`   | `NotificationCenter` | `POST /v1/notifications/inbox/{id}/read`     | `notification_engine`                                  | `NotificationRecord`                |
| `/book`        | `BookDeliveryClient` | `POST /booking/preview`, `/booking/confirm`  | `MerchantBookingFlowService`, `MerchantBookingService` | `Order`                             |
| `/bulk`        | `bulk/page`          | `POST /bulk/upload`, `/bulk/{id}/confirm`    | `MerchantBulkService`                                  | `BulkImportJob`, `Order`            |
| `/orders`      | `orders/page`        | `GET /orders`, cancel, duplicate             | `MerchantOrdersService`, `MerchantBookingService`      | `Order`                             |
| `/orders/[id]` | `Order360View`       | `GET /orders/{id}/360`, `/tracking`          | `MerchantOrdersService`, `MerchantTrackingService`     | `Order`, `OrderEvent`               |
| `/track`       | `track/page`         | `GET /track/{number}`                        | `MerchantTrackingService`                              | `Order`                             |
| `/billing`     | `BillingClient`      | `GET /billing/*`                             | `MerchantBillingService`                               | `Invoice`                           |
| `/reports`     | `ReportsClient`      | `GET /reports/*`                             | `MerchantReportsService`                               | `Order`                             |
| `/settings`    | `SettingsClient`     | `GET/PATCH /settings/profile`, `/recipients` | `MerchantSettingsService`                              | `Merchant`, `MerchantRecipient`     |
| `/team`        | `TeamClient`         | `GET/POST/DELETE /team/*`                    | `MerchantTeamService`                                  | `MerchantUser`                      |
| `/api`         | `IntegrationsClient` | `/integrations/api-keys/*`, `/webhooks/*`    | `MerchantIntegrationsService`                          | `MerchantApiKey`, `MerchantWebhook` |

Domain libs (`lib/orders.ts`, `lib/booking.ts`, etc.) wrap the same endpoints with Clerk token + org headers.

---

## 2. Programmatic API matrix

| Endpoint                                       | Auth | Scope             | Service                   |
| ---------------------------------------------- | ---- | ----------------- | ------------------------- |
| `POST /v1/merchant-api/bookings`               | 🔑   | `shipments:write` | `MerchantBookingService`  |
| `GET /v1/merchant-api/orders`                  | 🔑   | `shipments:read`  | `MerchantOrdersService`   |
| `GET /v1/merchant-api/orders/{id}`             | 🔑   | `shipments:read`  | `MerchantOrdersService`   |
| `GET /v1/merchant-api/track/{tracking_number}` | 🔑   | `shipments:read`  | `MerchantTrackingService` |
| `POST /v1/merchant-api/orders/{id}/cancel`     | 🔑   | `shipments:write` | `MerchantBookingService`  |

Same application services as portal — no duplicate business logic.

---

## 3. Shared infrastructure

| Component                  | Path                                            | Used by                  |
| -------------------------- | ----------------------------------------------- | ------------------------ |
| `PortalShell`              | `components/portal/PortalShell.tsx`             | All routes               |
| `MerchantAuthProvider`     | `components/providers/MerchantAuthProvider.tsx` | App root                 |
| `useMerchantRealtime`      | `hooks/useMerchantRealtime.ts`                  | Dashboard, orders, track |
| `AddressAutocompleteInput` | `@porterchain/maps`                             | Book page                |
| `middleware.ts`            | Clerk route protection                          | All portal routes        |

---

## 4. Backend module matrix

| Module             | Router                           | Services                                               | Models                                                         |
| ------------------ | -------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------- |
| Dashboard          | `merchant.py`                    | `MerchantDashboardService`                             | `Order`, `Invoice`                                             |
| Booking            | `merchant.py`, `merchant_api.py` | `MerchantBookingService`, `MerchantBookingFlowService` | `Order`                                                        |
| Bulk               | `merchant.py`                    | `MerchantBulkService`                                  | `BulkImportJob`                                                |
| Orders / tracking  | `merchant.py`, `merchant_api.py` | `MerchantOrdersService`, `MerchantTrackingService`     | `Order`, `OrderEvent`                                          |
| Billing            | `merchant.py`                    | `MerchantBillingService`                               | `Invoice`                                                      |
| Reports            | `merchant.py`                    | `MerchantReportsService`                               | `Order`                                                        |
| Settings / profile | `merchant.py`                    | `MerchantSettingsService`, `MerchantProfileService`    | `Merchant`, `SavedAddress`, `MerchantRecipient`                |
| Team               | `merchant.py`                    | `MerchantTeamService`                                  | `MerchantUser`                                                 |
| Integrations       | `merchant.py`                    | `MerchantIntegrationsService`, `MerchantApiKeyService` | `MerchantApiKey`, `MerchantWebhook`, `merchant_api_usage_logs` |
| Support bridge     | `merchant.py`                    | `MerchantSupportBridgeService`                         | tickets/claims via admin                                       |
| Webhook delivery   | worker                           | `webhook_delivery_service`                             | `merchant_webhook_deliveries`                                  |

---

## 5. Admin vs Merchant separation

| Concern  | Merchant                               | Admin staff                            |
| -------- | -------------------------------------- | -------------------------------------- |
| Prefix   | `/v1/merchant/*`, `/v1/merchant-api/*` | `/v1/admin/merchants/*`                |
| Auth     | Clerk org / API key                    | Clerk admin JWT                        |
| Services | `merchant_engine/*`                    | `admin_engine/*`, `Merchant360Service` |

Intentional separation — not duplicate implementations.

---

## 6. Event bus matrix (merchant path)

| Event                      | Emitter                        | Handler / downstream                       |
| -------------------------- | ------------------------------ | ------------------------------------------ |
| `merchant.booking_created` | `MerchantBookingService`       | Audit                                      |
| `order.dispatch_ready`     | `transition_to_dispatch_ready` | `fleetbase_sync_handler`                   |
| `order.cancelled`          | state transition               | Direct cancel sync today (G-M010)          |
| `order.*`                  | Various                        | `_handle_merchant_webhook_fanout` → worker |

---

## 7. Coverage summary (July 2026)

| Category                             | Clerk UI wired | Backend-only | merchant-api             |
| ------------------------------------ | -------------- | ------------ | ------------------------ |
| Core ops (book/orders/track/billing) | ✅             | —            | ✅ bookings/orders/track |
| Integrations (keys/webhooks)         | ✅ `/api`      | —            | —                        |
| Settings (recipients)                | ✅ tab         | —            | —                        |
| Scheduled reports                    | ⚠ metadata     | ⚠ no worker  | —                        |
| **Programmatic**                     | —              | —            | **5/5 routes**           |

**UI coverage:** ~90% of merchant-facing Clerk endpoints  
**Programmatic:** 100% of implemented merchant-api routes

---

## 8. File index

```
apps/merchant-portal/src/app/(portal)/**/page.tsx
apps/merchant-portal/src/components/**/*
apps/merchant-portal/src/lib/*.ts
apps/merchant-portal/src/hooks/useMerchantRealtime.ts

apps/api/src/porterchain_api/routers/merchant.py
apps/api/src/porterchain_api/routers/merchant_api.py
apps/api/src/porterchain_api/merchant_engine/
apps/api/src/porterchain_api/gateway_engine/
```

---

## Related

| Document                                                           | Purpose            |
| ------------------------------------------------------------------ | ------------------ |
| [MERCHANT_INTEGRATION_MATRIX.md](./MERCHANT_INTEGRATION_MATRIX.md) | Full endpoint list |
| [MERCHANT_GAP_ANALYSIS.md](./MERCHANT_GAP_ANALYSIS.md)             | Open gaps          |

_Matrix per masterrule §19 — reuse existing services._
