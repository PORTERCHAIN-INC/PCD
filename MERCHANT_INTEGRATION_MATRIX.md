# Merchant Portal — Integration Matrix

**Date:** June 30, 2026

Legend: **✅** Complete · **⚠** Partial · **❌** Missing

---

## Portal ↔ API integration

| Portal feature          | HTTP endpoint(s)                          | Backend service                | Engine / adapter           | Status |
| ----------------------- | ----------------------------------------- | ------------------------------ | -------------------------- | ------ |
| Dashboard KPIs          | `GET /v1/merchant/dashboard`              | `MerchantDashboardService`     | orders, billing aggregates | ✅     |
| Dashboard activity      | `GET /v1/merchant/dashboard/activity`     | `MerchantDashboardService`     | —                          | ✅     |
| Dashboard notifications | `GET /v1/notifications/inbox`             | `notification_engine`          | —                          | ✅     |
| Notification read       | `POST /v1/notifications/inbox/{id}/read`  | `notification_engine`          | —                          | ✅     |
| Orders list             | `GET /v1/merchant/orders`                 | `MerchantOrdersService`        | —                          | ✅     |
| Order 360               | `GET /v1/merchant/orders/{id}/360`        | `MerchantOrdersService`        | —                          | ✅     |
| Order tracking          | `GET /v1/merchant/orders/{id}/tracking`   | `MerchantTrackingService`      | fleetbase + maps           | ✅     |
| Order bulk              | `POST /v1/merchant/orders/bulk`           | `MerchantOrdersService`        | —                          | ✅     |
| Book preview            | `POST /v1/merchant/booking/preview`       | `MerchantBookingFlowService`   | pricing_engine             | ✅     |
| Book confirm            | `POST /v1/merchant/booking/confirm`       | `MerchantBookingService`       | booking + event bus        | ✅     |
| Book drafts             | `/booking/drafts/*`                       | `MerchantBookingFlowService`   | —                          | ✅     |
| Book templates          | `/booking/templates/*`                    | `MerchantBookingFlowService`   | —                          | ✅     |
| Bulk upload             | `POST /v1/merchant/bulk/upload`           | `MerchantBulkService`          | —                          | ✅     |
| Track by number         | `GET /v1/merchant/track/{n}`              | `MerchantTrackingService`      | fleetbase + maps           | ✅     |
| Billing overview        | `GET /v1/merchant/billing/overview`       | `MerchantBillingService`       | billing_engine             | ✅     |
| Invoices                | `GET /v1/merchant/billing/invoices`       | `MerchantBillingService`       | billing_engine             | ✅     |
| Statement               | `GET /v1/merchant/billing/statement`      | `MerchantBillingService`       | billing_engine             | ✅     |
| Payments                | `GET /v1/merchant/billing/payments`       | `MerchantBillingService`       | billing_engine             | ✅     |
| Credits                 | `GET /v1/merchant/billing/credits`        | `MerchantBillingService`       | billing_engine             | ✅     |
| Tax                     | `GET /v1/merchant/billing/tax`            | `MerchantBillingService`       | billing_engine             | ✅     |
| Reports workspace       | `GET /v1/merchant/reports/workspace`      | `MerchantReportsService`       | reporting_engine           | ✅     |
| Report export           | `GET /v1/merchant/reports/export`         | `MerchantReportsService`       | reporting_engine           | ✅     |
| Saved reports           | `/reports/saved/*`                        | `MerchantReportsService`       | profile JSON               | ✅     |
| Scheduled reports       | `/reports/scheduled/*`                    | `MerchantReportsService`       | profile only               | ⚠      |
| API keys                | `/integrations/api-keys/*`                | `MerchantIntegrationsService`  | gateway_engine             | ✅     |
| Webhooks                | `/integrations/webhooks/*`                | `MerchantIntegrationsService`  | gateway + worker           | ✅     |
| API usage               | `GET /integrations/api-usage`             | `MerchantIntegrationsService`  | gateway_engine             | ✅     |
| Rate limits             | `GET /integrations/rate-limits`           | `MerchantIntegrationsService`  | gateway_engine             | ✅     |
| API docs                | `GET /integrations/api-docs`              | `MerchantIntegrationsService`  | gateway_engine             | ✅     |
| Team list               | `GET /v1/merchant/team`                   | `MerchantTeamService`          | —                          | ✅     |
| Team invite             | `POST /v1/merchant/team/invite`           | `MerchantTeamService`          | —                          | ⚠      |
| Settings profile        | `GET/PATCH /v1/merchant/settings/profile` | `MerchantSettingsService`      | —                          | ✅     |
| Locations               | `/settings/locations/*`                   | `MerchantSettingsService`      | —                          | ✅     |
| Warehouses              | `/settings/warehouses/*`                  | `MerchantSettingsService`      | —                          | ✅     |
| Recipients              | `GET/POST /v1/merchant/recipients`        | `MerchantSettingsService`      | —                          | ✅     |
| Support tickets         | `/support/tickets/*`                      | `MerchantSupportBridgeService` | admin support              | ✅     |
| Claims                  | `/claims/*`                               | `MerchantSupportBridgeService` | admin claims               | ✅     |
| WebSocket               | `WS /v1/notifications/ws`                 | `realtime_hub`                 | notification_engine        | ⚠      |

---

## Programmatic API (`/v1/merchant-api/*`)

| Endpoint              | Service                   | Parity with portal       | Status |
| --------------------- | ------------------------- | ------------------------ | ------ |
| `POST /bookings`      | `MerchantBookingService`  | Same as confirm flow     | ✅     |
| `GET /bookings/{id}`  | `MerchantOrdersService`   | Order detail             | ✅     |
| `GET /track/{number}` | `MerchantTrackingService` | Live tracking + timeline | ✅     |
| `GET /invoices`       | `MerchantBillingService`  | Invoice list             | ✅     |
| `GET /invoices/{id}`  | `MerchantBillingService`  | Invoice detail           | ✅     |

**Gateway:** `MerchantApiGatewayMiddleware` — rate limit + usage logging on all merchant-api routes.

---

## External system integration

| System                  | Entry point                                                                    | Used by merchant                 | Status           |
| ----------------------- | ------------------------------------------------------------------------------ | -------------------------------- | ---------------- |
| **Fleetbase**           | `fleetbase_engine/integration_bridge.py` → `services/fleetbase_integration.py` | Booking sync, live tracking, POD | ✅               |
| **Pricing Engine**      | `pricing_engine/calculate_merchant`                                            | All booking previews/confirms    | ✅               |
| **Billing Engine**      | `billing_engine/merchant_service.py`                                           | Invoices, statements, credits    | ✅               |
| **Reporting Engine**    | `reporting_engine/merchant_service.py`                                         | Aggregates, exports              | ✅               |
| **Notification Engine** | `/v1/notifications/*`, `realtime_hub`                                          | Inbox, WS, prefs                 | ⚠                |
| **Event Bus**           | `platform/bus.py`                                                              | Booking, webhook fanout          | ✅               |
| **Google Maps**         | `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` + `@porterchain/maps`                        | Map render in portal             | ⚠ (env required) |
| **OSRM**                | `MapsService._osrm_route`                                                      | ETA in tracking responses        | ✅               |
| **Valhalla**            | `MapsService._valhalla_route`                                                  | Route polyline in tracking       | ✅               |
| **Clerk**               | `@clerk/nextjs`                                                                | Auth, org context                | ✅               |
| **Stripe**              | billing_engine (contract merchants off)                                        | Not primary merchant path        | ⚠                |
| **Shopify/WooCommerce** | integrations readiness                                                         | OAuth not implemented            | ❌               |

---

## Event bus → webhook chain

```
Domain event (e.g. order.status_changed)
  → platform/bus.py publish
  → worker/webhooks.py consumer
  → webhook_delivery_service.deliver()
  → HMAC-signed POST to merchant webhook URL
  → merchant_webhook_delivery_logs row
```

**Portal visibility:** Integrations → Webhooks → delivery logs + retry.

---

## Frontend lib → API mapping

| Lib module             | Primary routes                         |
| ---------------------- | -------------------------------------- |
| `lib/orders.ts`        | `/v1/merchant/orders/*`                |
| `lib/booking.ts`       | `/v1/merchant/booking/*`               |
| `lib/tracking.ts`      | `/v1/merchant/track/*`, order tracking |
| `lib/billing.ts`       | `/v1/merchant/billing/*`               |
| `lib/reports.ts`       | `/v1/merchant/reports/*`               |
| `lib/integrations.ts`  | `/v1/merchant/integrations/*`          |
| `lib/team.ts`          | `/v1/merchant/team/*`                  |
| `lib/settings.ts`      | settings, support, claims, recipients  |
| `lib/notifications.ts` | `/v1/notifications/inbox/*`            |
| `lib/api.ts`           | Legacy — superseded                    | ⚠   |

---

## Communication verification

| Hop                            | Verified | Evidence                                                |
| ------------------------------ | -------- | ------------------------------------------------------- |
| Merchant → FastAPI             | ✅       | All portal libs use `PORTERCHAIN_API_URL` + Clerk token |
| FastAPI → Application Services | ✅       | `merchant.py` delegates to `merchant_engine/*`          |
| Services → Event Bus           | ✅       | `emit_event` in booking/support flows                   |
| Event Bus → Fleetbase Adapter  | ✅       | Worker/handlers → `fleetbase_engine`                    |
| Fleetbase Adapter → Fleetbase  | ✅       | `FleetbaseIntegrationBridge` only path                  |

**No bypass:** Grep confirms zero direct Fleetbase HTTP calls from `merchant_engine/`.
