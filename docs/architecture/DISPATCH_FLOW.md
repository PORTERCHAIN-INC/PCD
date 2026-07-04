# Dispatch Flow

> **Source:** `admin_engine/operations_service.py`, `control_tower_service.py`, `fleetbase_engine/booking_sync_service.py`, `webhook_processor.py`

## Outbound Dispatch

1. Order reaches `DISPATCH_READY` → event `order.dispatch_ready`
2. Handler `sync_order_from_event` → `BookingSyncService.push_order()`
3. Sets `order.fleetbase_order_id`, emits `fleetbase.order_created`
4. Failures → `fleetbase_sync_jobs` retry queue

## Driver Assignment

1. Admin: `POST /v1/admin/dispatch/orders/{id}/assign` or operations board
2. `transition_order_state` → `DRIVER_ASSIGNED`
3. Event `order.driver_assigned` → `push_driver_assignment()`

## Inbound (Fleetbase → Porterchain)

`POST /webhooks/fleetbase` → `WebhookIngressService` → `webhook.received` → `WebhookProcessor`:
- Status updates via `StatusTranslator`
- Tracking → `order.tracking_updated`
- POD → `DELIVERED` → `POD_COMPLETED`
- Exceptions → `OrderException`; claims → `Claim`

## Live Tracking

- Admin map: `LiveMapService.snapshot()` polled via WebSocket every 5s
- Public tracking: `TrackingService` + Fleetbase live tracking API

## Diagram

```mermaid
flowchart LR
  OPS[Admin Operations<br/>ControlTowerService] --> Q[Dispatch Queue<br/>GET /operations/queue]
  Q --> ASSIGN[POST /dispatch/orders/{id}/assign<br/>AdminOperationsService]
  ASSIGN --> TRANS[transition_order_state<br/>DRIVER_ASSIGNED]
  TRANS --> EV[order.driver_assigned event]
  EV --> SYNC[BookingSyncService<br/>push_driver_assignment]
  SYNC --> FBA[fleetbase-adapter]
  FBA --> FB[Fleetbase Dispatch API]
  FB --> DRV[Driver Mobile / Portal]
  DRV --> LOC[DriverFleetbaseBridge<br/>location pings]
  FB --> WH[POST /webhooks/fleetbase]
  WH --> WP[WebhookProcessor]
  WP --> TRACK[order.tracking_updated]
  WP --> POD[POD fetch → POD_COMPLETED]
  ADMIN_MAP[LiveMapService] --> WS[WS /live-map/ws<br/>5s snapshots]
  ADMIN_MAP --> FB_TRACK[TrackingService<br/>Fleetbase live tracking]
```

## PlantUML

See [plantuml/dispatch_flow.puml](./plantuml/dispatch_flow.puml)
