# Fleetbase Webhooks — Reference

**Last verified:** 2026-07-04  
**Packages:** core-api 1.6.47 (delivery), fleetops-api 0.6.48 (domain triggers)  
**Admin UI:** `@fleetbase/dev-engine` in Fleetbase console

> **Integration:** [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) · **Event mapping:** [FLEETBASE_EVENTS.md](./FLEETBASE_EVENTS.md)

---

## Overview

Fleetbase has **two webhook directions**:

| Direction    | Purpose                  | Porterchain role                             |
| ------------ | ------------------------ | -------------------------------------------- |
| **Outbound** | Fleetbase → your systems | **Primary** — status sync to Porterchain API |
| **Inbound**  | External → Fleetbase     | Telematics only (not Porterchain-critical)   |

---

## Porterchain inbound handler (implemented)

| Route                      | Handler                                      |
| -------------------------- | -------------------------------------------- |
| `POST /webhooks/fleetbase` | `WebhookIngressService` → `WebhookProcessor` |

**Flow:**

1. Verify HMAC signature (`FLEETBASE_WEBHOOK_SECRET`)
2. Emit `webhook.received` to event bus
3. `apply_fleetbase_webhook_from_event` maps Fleetbase event → Porterchain order state
4. Emit canonical domain events (`order.delivered`, etc.)

**Code:** `apps/api/.../routers/webhooks.py`, `fleetbase_engine/webhook_ingress_service.py`, `fleetbase_engine/webhook_processor.py`

---

## Outbound webhooks (Fleetbase → Porterchain)

### How delivery works

1. Domain action fires Laravel event (e.g. `OrderDispatched`)
2. `SendResourceLifecycleWebhook` listener runs
3. Row created in `fleetbase_api_events`
4. Enabled endpoints in `fleetbase_webhook_endpoints` filtered by subscription
5. `WebhookCall` queued to endpoint URL
6. Result logged in `fleetbase_webhook_request_logs`

### Recommended subscription

Register in Fleetbase console → Developer → Webhooks:

**URL:** `https://api.porterchain.com/webhooks/fleetbase` (local: `http://localhost:8001/webhooks/fleetbase`)

| Event                   | Porterchain action           |
| ----------------------- | ---------------------------- |
| `order.dispatched`      | Driver assigned notification |
| `order.driver_assigned` | `order.driver_assigned`      |
| `order.started`         | In-transit / pickup events   |
| `order.completed`       | `order.delivered` + POD flow |
| `order.canceled`        | `order.cancelled`            |
| `order.failed`          | Exception / claim workflow   |
| `order.dispatch_failed` | Ops alert                    |

Store `porterchain_order_id` in Fleetbase order `meta` during adapter sync.

---

## Payload format

```json
{
  "id": "event_abc123",
  "api_version": "1.0",
  "event": "order.dispatched",
  "created_at": "2026-06-29T15:30:00",
  "data": {
    "id": "order_xyz",
    "status": "dispatched",
    "meta": { "porterchain_order_id": "..." }
  }
}
```

Signing uses the API credential **secret** associated with the webhook endpoint.

---

## Porterchain → Fleetbase (REST, not webhooks)

Outbound sync uses **`POST /v1/orders`** (and drivers, vehicles, dispatch) via `services/fleetbase-adapter/` — not webhooks.

Optional SSO extension routes: `POST /int/v1/porterchain/sso/*` — requires `porterchain-bridge` Fleetbase extension.

---

## Environment variables

| Variable                         | Side        | Purpose                  |
| -------------------------------- | ----------- | ------------------------ |
| `FLEETBASE_API_URL`              | Porterchain | Fleetbase base URL       |
| `FLEETBASE_API_KEY`              | Porterchain | Outbound auth            |
| `FLEETBASE_WEBHOOK_SECRET`       | Porterchain | Inbound signature verify |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Fleetbase   | Reverse auth (if added)  |

---

## Security checklist

| Control                     | Status                                |
| --------------------------- | ------------------------------------- |
| HTTPS in production         | Required                              |
| HMAC signature verification | ✅ Implemented                        |
| Idempotency on `event.id`   | ✅ Via event bus idempotency store    |
| Secret rotation             | Fleetbase `api-credentials/roll/{id}` |

---

## Testing locally

1. `pnpm docker:fleetbase:up`
2. Expose Porterchain API :8001 (ngrok if Fleetbase needs external URL)
3. Register webhook in Fleetbase console
4. Dispatch test order → check `int/v1/webhook-request-logs`

---

## Related documents

| Document                                         | Purpose                 |
| ------------------------------------------------ | ----------------------- |
| [FLEETBASE_EVENTS.md](./FLEETBASE_EVENTS.md)     | Event catalog + mapping |
| [FLEETBASE_APIS.md](./FLEETBASE_APIS.md)         | REST reference          |
| [FLEETBASE_DATABASE.md](./FLEETBASE_DATABASE.md) | Webhook tables          |
