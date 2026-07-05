# Merchant Portal — Integration Matrix

**Last verified:** 2026-07-04  
**See also:** [MERCHANT_COMPONENT_MATRIX.md](./MERCHANT_COMPONENT_MATRIX.md) · [MERCHANT_ARCHITECTURE_REPORT.md](./MERCHANT_ARCHITECTURE_REPORT.md)

Legend: **✅** Complete · **⚠** Partial · **❌** Missing

---

## Portal ↔ API integration

| Portal feature          | HTTP endpoint(s)                                                         | Backend service                | Engine / adapter    | Status            |
| ----------------------- | ------------------------------------------------------------------------ | ------------------------------ | ------------------- | ----------------- |
| Dashboard KPIs          | `GET /v1/merchant/dashboard`                                             | `MerchantDashboardService`     | aggregates          | ✅                |
| Dashboard activity      | `GET /v1/merchant/dashboard/activity`                                    | `MerchantDashboardService`     | —                   | ✅                |
| Dashboard notifications | `GET /v1/notifications/inbox`                                            | `notification_engine`          | —                   | ✅                |
| Notification read       | `POST /v1/notifications/inbox/{id}/read`                                 | `notification_engine`          | —                   | ✅                |
| Orders list             | `GET /v1/merchant/orders`                                                | `MerchantOrdersService`        | —                   | ✅                |
| Order 360               | `GET /v1/merchant/orders/{id}/360`                                       | `MerchantOrdersService`        | —                   | ✅                |
| Order tracking          | `GET /v1/merchant/orders/{id}/tracking`                                  | `MerchantTrackingService`      | fleetbase + maps    | ✅                |
| Book preview            | `POST /v1/merchant/booking/preview`                                      | `MerchantBookingFlowService`   | pricing_engine      | ✅                |
| Book confirm            | `POST /v1/merchant/booking/confirm`                                      | `MerchantBookingService`       | event bus           | ✅                |
| Book drafts / templates | `/v1/merchant/booking/drafts/*`, `/templates/*`                          | `MerchantBookingFlowService`   | —                   | ✅                |
| Bulk upload             | `POST /v1/merchant/bulk/upload`, `/bulk/{id}/confirm`                    | `MerchantBulkService`          | —                   | ✅                |
| Track by number         | `GET /v1/merchant/track/{number}`                                        | `MerchantTrackingService`      | fleetbase + maps    | ✅                |
| Billing tabs            | `GET /v1/merchant/billing/*`                                             | `MerchantBillingService`       | billing_engine      | ✅                |
| Reports                 | `GET /v1/merchant/reports/summary`, `/overview`, `/workspace`, `/export` | `MerchantReportsService`       | SQL aggregates      | ✅                |
| Scheduled reports       | `/reports/scheduled/*`                                                   | `MerchantReportsService`       | profile JSON only   | ⚠                 |
| API keys / webhooks     | `/v1/merchant/integrations/*`                                            | `MerchantIntegrationsService`  | gateway_engine      | ✅                |
| Team                    | `/v1/merchant/team/*`                                                    | `MerchantTeamService`          | —                   | ⚠ (no Clerk sync) |
| Settings / recipients   | `/v1/merchant/settings/*`, `/recipients`                                 | `MerchantSettingsService`      | —                   | ✅                |
| Support / claims        | `/v1/merchant/support/*`, `/claims/*`                                    | `MerchantSupportBridgeService` | admin bridge        | ✅                |
| WebSocket               | `WS /v1/notifications/ws`                                                | `realtime_hub`                 | notification_engine | ⚠                 |

---

## Programmatic API (`/v1/merchant-api/*`)

| Endpoint                       | Service                   | Scope             | Status |
| ------------------------------ | ------------------------- | ----------------- | ------ |
| `POST /bookings`               | `MerchantBookingService`  | `shipments:write` | ✅     |
| `GET /orders`                  | `MerchantOrdersService`   | `shipments:read`  | ✅     |
| `GET /orders/{id}`             | `MerchantOrdersService`   | `shipments:read`  | ✅     |
| `GET /track/{tracking_number}` | `MerchantTrackingService` | `shipments:read`  | ✅     |
| `POST /orders/{id}/cancel`     | `MerchantBookingService`  | `shipments:write` | ✅     |

**Gateway:** `MerchantApiGatewayMiddleware` — rate limit + `merchant_api_usage_logs` on all routes.

No invoice routes on merchant-api (billing is portal `/v1/merchant/billing/*` only).

---

## External system integration

| System                  | Entry point                                     | Used by merchant              | Status      |
| ----------------------- | ----------------------------------------------- | ----------------------------- | ----------- |
| **Fleetbase**           | `fleetbase_engine` → `fleetbase_integration.py` | Sync, tracking, POD           | ✅          |
| **Pricing Engine**      | `pricing_engine`                                | All bookings                  | ✅          |
| **Billing Engine**      | `billing_engine/merchant_service.py`            | NET invoices/statements       | ✅          |
| **Notification Engine** | `/v1/notifications/*`                           | Inbox, WS                     | ⚠           |
| **Event Bus**           | `platform/bus.py`                               | Dispatch, webhook fanout      | ✅          |
| **Google Maps**         | `@porterchain/maps`                             | Map render                    | ⚠ (env key) |
| **Valhalla / OSRM**     | `MapsService`                                   | ETA / polyline in tracking    | ✅          |
| **Clerk**               | `@clerk/nextjs`                                 | Auth, org                     | ✅          |
| **Stripe**              | billing (retail path)                           | Not primary for NET merchants | ⚠           |
| **Shopify/WooCommerce** | integrations readiness docs                     | OAuth                         | ❌          |

---

## Event bus → webhook chain

```
Domain event (order.*)
  → emit_event → Redis event bus
  → _handle_merchant_webhook_fanout
  → webhooks queue
  → webhook_delivery_service.deliver_merchant_fanout()
  → HMAC POST to merchant webhook URL
  → merchant_webhook_deliveries
```

Portal: Integrations → Webhooks → delivery logs + retry.

---

## Frontend lib → API mapping

| Lib module             | Primary routes                        |
| ---------------------- | ------------------------------------- |
| `lib/orders.ts`        | `/v1/merchant/orders/*`               |
| `lib/booking.ts`       | `/v1/merchant/booking/*`              |
| `lib/tracking.ts`      | `/track/*`, order tracking            |
| `lib/billing.ts`       | `/v1/merchant/billing/*`              |
| `lib/reports.ts`       | `/v1/merchant/reports/*`              |
| `lib/integrations.ts`  | `/v1/merchant/integrations/*`         |
| `lib/team.ts`          | `/v1/merchant/team/*`                 |
| `lib/settings.ts`      | settings, support, claims, recipients |
| `lib/notifications.ts` | `/v1/notifications/inbox/*`           |
| `lib/api.ts`           | Legacy — superseded                   | ⚠   |

---

## Communication verification

| Hop                                              | Status |
| ------------------------------------------------ | ------ |
| Merchant → FastAPI `:8001`                       | ✅     |
| FastAPI → `merchant_engine/*`                    | ✅     |
| Services → Event Bus                             | ✅     |
| Event Bus → Fleetbase adapter                    | ✅     |
| Zero direct Fleetbase HTTP in `merchant_engine/` | ✅     |
