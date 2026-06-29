# Porterchain ↔ Fleetbase Integration

**Version:** 1.0  
**Date:** June 29, 2026  
**Status:** Implemented

---

## Overview

Fleetbase is Porterchain's **internal logistics engine**. Porterchain owns customer experience, auth, pricing, billing, and CRM. Fleetbase owns drivers, vehicles, operational orders, dispatch, GPS tracking, routes, and proof of delivery.

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Website   │────►│ Porterchain API │────►│ FleetbaseIntegration   │────►│ Fleetbase   │
│  :3000      │     │  :8001          │     │ Service              │     │ API :8000   │
├─────────────┤     │                 │     │ services/fleetbase/  │     └─────────────┘
│  Merchant   │────►│  /v1/*          │     └──────────────────────┘
│  Portal     │     │  /webhooks/*    │
├─────────────┤     └────────▲────────┘
│  Admin      │──────────────┘
│  Portal     │
└─────────────┘

Fleetbase Console :4200 — ops dispatch only (unchanged)
```

**Never:** Website → Fleetbase API  
**Always:** Website → Porterchain API → Fleetbase Service → Fleetbase API

---

## Ownership matrix

| Domain | Owner |
|--------|-------|
| Authentication (Clerk) | Porterchain |
| Website, merchant portal, admin portal UX | Porterchain |
| Business rules, pricing, billing, CRM, analytics | Porterchain |
| Drivers, vehicles, ops orders, dispatch | Fleetbase |
| GPS tracking, routes, POD capture | Fleetbase |

---

## Integration service

**Package:** `porterchain-fleetbase` at `services/fleetbase/`

### Modules

| Module | Class | Responsibility |
|--------|-------|----------------|
| `client` | `FleetbaseClient` | HTTP transport, auth headers, error handling |
| `orders` | `OrderSyncService` | Create/update Fleetbase orders |
| `drivers` | `DriverSyncService` | Sync approved Porterchain drivers |
| `vehicles` | `VehicleSyncService` | Sync Porterchain vehicles |
| `dispatch` | `DispatchSyncService` | Dispatch, schedule, start, complete |
| `tracking` | `TrackingSyncService` | Tracker, ETA, proof aggregation |
| `routes` | `RouteSyncService` | Route polyline, orchestrator |
| `webhooks` | verify/parse | HMAC validation, envelope normalization |
| `events` | mappers | Fleetbase event → Porterchain state |
| `integration` | `FleetbaseIntegrationService` | Unified facade |

### Usage (Python)

```python
from porterchain_fleetbase import FleetbaseIntegrationService, FleetbaseSettings

svc = FleetbaseIntegrationService(
    FleetbaseSettings(
        api_url="http://localhost:8000",
        api_key="flb_live_...",
        company_uuid="...",
        dispatch_bridge=True,
    )
)

fleetbase_order_id = svc.sync_order({
    "porterchain_order_id": order.id,
    "order_number": order.order_number,
    "tracking_number": order.tracking_number,
    "pickup": order.pickup,
    "dropoff": order.dropoff,
    "scheduled_at": order.scheduled_at.isoformat(),
})

tracking = svc.fetch_tracking(fleetbase_order_id)
```

---

## Sync flows

### 1. Order sync

**When:** Retail booking confirmed, merchant creates shipment, order reaches `DISPATCH_READY`

**Path:**
```
BookingConfirmationService / MerchantBookingService
  → FleetbaseSyncService.sync_order()
  → OrderSyncService.create_or_update()
  → POST /v1/orders
  → order.fleetbase_order_id saved
```

**ID mapping:** `orders.meta.porterchain_order_id` in Fleetbase (via mapper)

### 2. Driver sync

**When:** Admin approves driver (`POST /v1/admin/drivers/{id}/approve`)

**Path:**
```
AdminDriverService.approve_driver()
  → sync active vehicles first
  → sync driver
  → driver.fleetbase_driver_id saved
```

### 3. Vehicle sync

**When:** Bundled with driver approval (active vehicle)

**Path:** `VehicleSyncService.sync()` → `POST /v1/vehicles`

### 4. Dispatch sync

**When:** Admin assigns driver to order

**Path:**
```
AdminOperationsService.assign_driver()
  → sync_order (ensure Fleetbase order exists)
  → sync_dispatch(fleetbase_driver_id)
  → PATCH /v1/orders/{id}/dispatch
```

### 5. Tracking sync

**When:** Customer views tracking page

**API:** `GET /v1/orders/{tracking_number}/tracking`

**Path:**
```
TrackingService.get_live_tracking()
  → GET /v1/orders/{id}/tracker
  → GET /v1/orders/{id}/eta
  → GET /v1/orders/{id}/proofs
```

Returns Porterchain order state + `live_tracking` blob from Fleetbase.

### 6. Status sync (webhooks)

**When:** Fleetbase fires order lifecycle event

**API:** `POST /webhooks/fleetbase`

**Subscribed events:**

| Fleetbase event | Porterchain state |
|-----------------|-------------------|
| `order.dispatched` | `DRIVER_ASSIGNED` |
| `order.driver_assigned` | `DRIVER_ASSIGNED` |
| `order.started` | `PICKED_UP` |
| `order.completed` | `DELIVERED` → `POD_COMPLETED` |
| `order.canceled` | `CANCELLED` |
| `order.failed` | `FAILED` |

**Path:**
```
Fleetbase webhook
  → verify HMAC signature
  → process_webhook()
  → apply_webhook_update()
  → transition_order_state()
```

### 7. Proof sync

**When:** `order.completed` webhook received

**Path:** `GET /v1/orders/{id}/proofs` → transition to `POD_COMPLETED` if proofs exist

---

## API endpoints (Porterchain)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/orders/{tracking_number}` | Order summary (Porterchain DB) |
| GET | `/v1/orders/{tracking_number}/tracking` | Order + live Fleetbase tracking |
| POST | `/webhooks/fleetbase` | Fleetbase status webhooks |

Merchant and admin endpoints trigger sync internally — no Fleetbase URLs exposed to clients.

---

## Configuration

Add to Porterchain API `.env`:

```env
FLEETBASE_API_URL=http://localhost:8000
FLEETBASE_API_KEY=flb_live_your_key_here
FLEETBASE_DEFAULT_COMPANY_UUID=your-company-uuid
FLEETBASE_DISPATCH_BRIDGE=true
FLEETBASE_WEBHOOK_SECRET=your_api_credential_secret
```

Create API credentials in Fleetbase console (`@fleetbase/dev-engine`).

---

## Development setup

```bash
# Start Fleetbase stack
pnpm docker:fleetbase:up

# Install Porterchain API with fleetbase package
cd apps/api && pip install -r requirements.txt

# Start API
pnpm dev:api
```

Complete Fleetbase onboarding at http://localhost:4200 and copy company UUID.

---

## Fleetbase UI policy

- **Do not modify** Fleetbase Ember console (`apps/fleetbase/console/`)
- Ops staff use stock Fleetbase console for dispatch, live map, orchestrator
- Merchants and retail customers use Porterchain portals only

---

## Error handling

| Scenario | Behavior |
|----------|----------|
| Bridge disabled | Sync skipped, logged |
| Fleetbase unreachable | Order stays in Porterchain; `fleetbase.sync_failed` event |
| Webhook signature invalid | 200 ignored (logged) |
| Order not found for webhook | `order_not_found` response |
| Invalid state transition | Logged, no crash |

---

## File index

| Path | Purpose |
|------|---------|
| `services/fleetbase/porterchain_fleetbase/` | Integration package |
| `apps/api/.../fleetbase_sync_service.py` | DB orchestration |
| `apps/api/.../fleetbase_integration.py` | Settings factory |
| `services/python/porterchain_services/fleetbase/service.py` | Worker/gateway delegate |
| `apps/api/.../routers/webhooks.py` | Webhook receiver |

---

## Related documents

- [FLEETBASE_ANALYSIS.md](./FLEETBASE_ANALYSIS.md)
- [FLEETBASE_MODULES.md](./FLEETBASE_MODULES.md)
- [FLEETBASE_APIS.md](./FLEETBASE_APIS.md)
- [FLEETBASE_WEBHOOKS.md](./FLEETBASE_WEBHOOKS.md)
- [services/fleetbase/README.md](./services/fleetbase/README.md)
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)
