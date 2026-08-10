# Dispatch Flow

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-07

**Source:** `admin_engine/operations_service.py`, `control_tower_service.py`, `fleetbase_engine/booking_sync_service.py`, `webhook_processor.py`  
**See also:** [BOOKING_FLOW.md](./BOOKING_FLOW.md) · [ORDERS_MODULE.md](../ops/ORDERS_MODULE.md) · [SERVICE_STATUS.md](../../SERVICE_STATUS.md)

---

## Outbound Dispatch

1. Order reaches `DISPATCH_READY` → event `order.dispatch_ready`
2. Handler `sync_order_from_event` → `BookingSyncService.push_order()`
3. Sets `order.fleetbase_order_id`, emits `fleetbase.order_created`
4. Failures → `fleetbase_sync_jobs` retry queue

## Driver Assignment

1. Admin: `POST /v1/admin/dispatch/orders/{id}/assign` or operations board (`/v1/admin/operations/queue`)
2. `transition_order_state` → `DRIVER_ASSIGNED`
3. Event `order.driver_assigned` → `push_driver_assignment()`

Batch assignment: `POST /v1/admin/operations/queue/assign-batch`.

## Inbound (Fleetbase → Porterchain)

`POST /webhooks/fleetbase` → `WebhookIngressService` → `webhook.received` → `WebhookProcessor`:

- Status updates via `StatusTranslator`
- Tracking → `order.tracking_updated`
- POD → `DELIVERED` → `POD_COMPLETED`
- Exceptions → `OrderException`; claims → `Claim`

## Live tracking

- **Ops maps / GPS:** Fleetbase console (Admin SSO) — not a PorterChain live-map surface
- **Public / merchant tracking:** `TrackingService` + Fleetbase live tracking API
- Order 360 in Admin shows adapter-fed status, POD, and documents — not a custom map engine

## Diagram

```mermaid
flowchart LR
  OPS[Admin Operations<br/>ControlTowerService] --> Q[Dispatch Queue<br/>GET /v1/admin/operations/queue]
  Q --> ASSIGN[POST /v1/admin/dispatch/orders/{id}/assign<br/>AdminOperationsService]
  ASSIGN --> TRANS[transition_order_state<br/>DRIVER_ASSIGNED]
  TRANS --> EV[order.driver_assigned event]
  EV --> SYNC[BookingSyncService<br/>push_driver_assignment]
  SYNC --> FBA[fleetbase-adapter]
  FBA --> FB[Fleetbase Dispatch API]
  FB --> DRV[Driver Mobile / Portal :3003]
  DRV --> LOC[DriverFleetbaseBridge<br/>location pings]
  FB --> WH[POST /webhooks/fleetbase]
  WH --> WP[WebhookProcessor]
  WP --> TRACK[order.tracking_updated]
  WP --> POD[POD fetch → POD_COMPLETED]
  ADMIN_SSO[Admin SSO] --> FB_UI[Fleetbase console<br/>live GPS / fleet map]
```

## PlantUML

See [plantuml/dispatch_flow.puml](./plantuml/dispatch_flow.puml)
---
