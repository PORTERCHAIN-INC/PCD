# Fleetbase Webhooks — Reference

**Packages:** core-api 1.6.47 (delivery), fleetops-api 0.6.48 (domain triggers)  
**Admin UI:** `@fleetbase/dev-engine` in console

---

## Overview

Fleetbase has **two webhook directions**:

| Direction | Purpose | Porterchain role |
|-----------|---------|------------------|
| **Outbound** | Fleetbase → your systems | **Primary integration** — status sync to Porterchain API |
| **Inbound** | External → Fleetbase | Telematics only (not Porterchain-critical today) |

---

## Outbound webhooks (Fleetbase → Porterchain)

### How delivery works

1. Domain action fires Laravel event (e.g. `OrderDispatched`)
2. `SendResourceLifecycleWebhook` listener runs
3. Row created in `fleetbase_api_events`
4. Enabled endpoints in `fleetbase_webhook_endpoints` filtered by event subscription
5. `WebhookCall` dispatched (queued) to endpoint URL
6. Result logged in `fleetbase_webhook_request_logs`

### Configuration tables

**`fleetbase_webhook_endpoints`**

| Column | Purpose |
|--------|---------|
| `uuid` | Endpoint ID |
| `company_uuid` | Tenant |
| `url` | Destination HTTPS URL |
| `events` | JSON array of subscribed event names |
| `api_credential_uuid` | Linked credential (for signing) |
| `status` | `enabled` / `disabled` |
| `mode` | `live` / `test` |

**`fleetbase_webhook_request_logs`**

| Column | Purpose |
|--------|---------|
| `webhook_uuid` | Endpoint reference |
| `api_event_uuid` | Triggering event |
| `status_code`, `duration` | HTTP result |
| `response`, `headers` | Debug payload |
| `attempt` | Retry count |
| `status` | `success` / `failed` |

**`fleetbase_api_events`**

| Column | Purpose |
|--------|---------|
| `event` | e.g. `order.dispatched` |
| `data` | Full webhook JSON payload |
| `source` | `api` or `console` |
| `description` | Human-readable audit text |

### Admin API

| Method | Path | Action |
|--------|------|--------|
| CRUD | `int/v1/webhook-endpoints` | Manage endpoints |
| PATCH | `int/v1/webhook-endpoints/enable/{id}` | Enable |
| PATCH | `int/v1/webhook-endpoints/disable/{id}` | Disable |
| GET | `int/v1/webhook-endpoints/events` | List available events |
| GET | `int/v1/webhook-endpoints/versions` | API versions |
| CRUD | `int/v1/webhook-request-logs` | View delivery logs |

### Payload format

```json
{
  "id": "event_abc123",
  "api_version": "1.0",
  "event": "order.dispatched",
  "created_at": "2026-06-29T15:30:00",
  "data": {
    "id": "order_xyz",
    "status": "dispatched",
    "driver_assigned_uuid": "...",
    "payload": { },
    "meta": { "porterchain_order_id": "..." }
  }
}
```

Signing uses the API credential **secret** associated with the webhook (`useSecret($apiSecret)`).

### Retry behavior

| Event | Listener |
|-------|----------|
| Success | `WebhookCallSucceededEvent` → `LogSuccessfulWebhook` |
| Failure | `WebhookCallFailedEvent` → `LogFailedWebhook` |
| Final failure | `FinalWebhookCallFailedEvent` → `LogFinalWebhookAttempt` |

Delivery is **queued** via Laravel queue (Redis) — requires `queue` container healthy.

---

## Recommended Porterchain webhook subscription

Register endpoint: `https://api.porterchain.com/v1/webhooks/fleetbase` (handler to implement)

| Event | Porterchain action |
|-------|-------------------|
| `order.created` | Confirm mirror exists; link IDs |
| `order.dispatched` | Update status; notify ops |
| `order.driver_assigned` | `DRIVER_ASSIGNED`; push to driver app |
| `order.completed` | `PARCEL_DELIVERED`; trigger invoice if needed |
| `order.canceled` | `ORDER_CANCELLED`; refund workflow |
| `order.dispatch_failed` | Ops alert |
| `order.failed` | Claim/support workflow |
| `driver.updated` | Refresh admin map cache |
| `driver.created` | Confirm sync from Porterchain |

Store `porterchain_order_id` in Fleetbase order `meta` during bridge sync for correlation.

---

## Inbound webhooks (external → Fleetbase)

| Method | Path | Purpose |
|--------|------|---------|
| ANY | `/webhooks/telematics/{providerKey}` | Telematics vendor callback |
| ANY | `/webhooks/telematics/ingest/{id}` | Raw device ingest |

Used for GPS hardware, sensors, and third-party fleet telematics — not required for Porterchain MVP.

---

## Porterchain → Fleetbase (not webhooks)

Porterchain uses **HTTP API calls** (not webhooks) to push data into Fleetbase:

| Call | Direction |
|------|-----------|
| `POST /int/v1/porterchain/orders` | Porterchain → Fleetbase |
| `POST /int/v1/porterchain/drivers` | Porterchain → Fleetbase |
| `POST /int/v1/porterchain/vehicles` | Porterchain → Fleetbase |
| `GET /int/v1/porterchain/orders/{id}/tracking` | Porterchain ← Fleetbase |

These are synchronous REST calls from `FleetbaseService` / `fleetbase_sync_service.py`.

**Note:** `porterchain/*` routes are Porterchain extension endpoints — not in upstream OSS. Until deployed, use `POST /v1/orders` etc.

---

## Environment variables

| Variable | Side | Purpose |
|----------|------|---------|
| `FLEETBASE_API_URL` | Porterchain | Fleetbase base URL |
| `FLEETBASE_API_KEY` | Porterchain | Outbound auth to Fleetbase |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Fleetbase | Inbound auth from Fleetbase to Porterchain (if reverse calls added) |
| `PORTERCHAIN_API_URL` | Fleetbase | Porterchain base for callbacks |

---

## Security checklist

| Control | Implementation |
|---------|----------------|
| HTTPS only | Production webhook URLs must be TLS |
| Signature verification | Validate Fleetbase HMAC on Porterchain handler |
| Idempotency | Dedupe on `event.id` |
| IP allowlist | Optional at reverse proxy |
| Secret rotation | `api-credentials/roll/{id}` in Fleetbase |
| Sandbox isolation | Use `flb_test_*` keys in staging |

---

## Testing webhooks locally

1. Start Fleetbase stack: `pnpm docker:fleetbase:up`
2. Use ngrok or similar to expose Porterchain API :8001
3. Create webhook endpoint in Fleetbase console → Developer → Webhooks
4. Dispatch a test order in Fleetbase console
5. Inspect `int/v1/webhook-request-logs` for delivery status

---

## Comparison: webhooks vs polling

| Approach | When to use |
|----------|-------------|
| **Webhooks** | Production status sync (recommended) |
| **Polling** | `GET /v1/orders/{id}/tracker` for customer tracking page |
| **SocketCluster** | Fleetbase console live map only |
| **Porterchain events** | Commercial domain (quotes, payments) — separate bus |

---

## Related documents

- [FLEETBASE_EVENTS.md](./FLEETBASE_EVENTS.md) — event catalog
- [FLEETBASE_APIS.md](./FLEETBASE_APIS.md) — REST reference
- [FLEETBASE_DATABASE.md](./FLEETBASE_DATABASE.md) — webhook tables
