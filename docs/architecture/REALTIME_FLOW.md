# Realtime Flow

> **Source:** `routers/operations.py`, `admin_engine/live_map_service.py`, `apps/admin/src/lib/maps.ts`

## WebSocket (Only One)

| Path                                                    | Auth                  | Behavior                                                  |
| ------------------------------------------------------- | --------------------- | --------------------------------------------------------- |
| `WS /v1/admin/operations/live-map/ws?token=<clerk_jwt>` | Clerk JWT query param | Push `{"type":"snapshot","data":...}` every **5 seconds** |

Implementation: `operations.py` `@router.websocket("/live-map/ws")` → `LiveMapService.snapshot()`.

Close codes: `4401` auth failure, `1011` server error.

## Admin Client

`apps/admin/src/lib/maps.ts` opens WebSocket to API base URL with Clerk token.

## Polling Alternatives

- Website booking confirmation: `GET /v1/bookings/confirmation?quote_id=` polling
- Public tracking: `GET /v1/orders/{tracking}/tracking` HTTP polling (Fleetbase live data)

## No Realtime For

- Customer portal (HTTP only)
- Merchant portal (HTTP only)
- Driver portal (HTTP polling via REST)

## Diagram

```mermaid
sequenceDiagram
  participant Admin as Admin Portal
  participant WS as WS /live-map/ws
  participant LMS as LiveMapService
  participant DB as Database
  participant FB as Fleetbase Tracking

  Admin->>WS: Connect ?token=clerk_jwt
  WS->>WS: verify_clerk_token
  loop every 5 seconds
    WS->>LMS: snapshot()
    LMS->>DB: active orders + drivers
    LMS->>FB: live positions (via adapter)
    LMS-->>WS: map data
    WS-->>Admin: {"type":"snapshot","data":...}
  end

  Note over Admin,FB: Only WebSocket in codebase.<br/>No customer/merchant WS.
```

## PlantUML

See [plantuml/realtime_flow.puml](./plantuml/realtime_flow.puml)
