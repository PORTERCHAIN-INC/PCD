# Route Center Integration

**Authority:** [masterrule.md](./masterrule.md) §7 Communication rules, §8 Fleetbase adapter

---

## Integration Map

| System | Role in Route Center | Access path |
|--------|---------------------|-------------|
| Porterchain Order mirror | Planning queue, stops, dispatch | SQLAlchemy `Order` model |
| Valhalla | Multi-stop leg routing, sequencing | `MapsService` (routing_engine=valhalla) |
| OSRM | Distance matrix / ETA refinement | `MapsService` + `_osrm_leg_matrix` |
| Fleetbase Adapter | Orchestrator run/commit, dispatch sync | `get_fleetbase_integration(settings)` |
| Google Maps | Map visualization only | Admin `MapCanvas` (client-side) |
| Clerk | Admin authentication | `get_admin_context` |
| Redis / Event bus | Order state events on dispatch | `emit_event` via `AdminOperationsService` |

---

## Fleetbase Adapter Calls

All from `RouteCenterService` only:

```python
adapter = get_fleetbase_integration(settings)

# After optimization (when fleetbase_dispatch_bridge enabled)
run = adapter.routes.run_orchestrator(fleetbase_order_ids)
plan.fleetbase_run_id = run["run_id"]

# On dispatch
adapter.routes.commit_orchestrator(plan.fleetbase_run_id)
sync.push_driver_assignment(db, settings, order, fleetbase_driver_id=...)
```

**Never:** `FleetbaseClient` in routers or admin React code.

---

## Maps Integration

### Valhalla (primary optimizer)

- Endpoint: `{VALHALLA_URL}/route`
- Used for: leg-by-leg distance accumulation across stops
- Config: `PlatformSettings.valhalla_url`, `routing_engine`

### OSRM (matrix / ETA)

- Endpoint: `{OSRM_URL}/route/v1/driving/{coords}`
- Used for: full-waypoint distance/duration when refining optimized routes
- Config: `PlatformSettings.osrm_url`

### Fallback

If routing engines unreachable, optimization returns `400 insufficient_stops` or zero distance; no silent haversine in Route Center service (pricing haversine remains separate).

---

## Reused Admin APIs (not duplicated)

| Consumer | Reused endpoint / service |
|----------|---------------------------|
| Dispatch driver picker | `GET /v1/admin/operations/assignable-drivers` |
| Live map | `LiveMapApp` → `/v1/admin/operations/live-map` + WS |
| Order detail from Route 360 | `GET /v1/admin/orders/{id}` via `/orders/[id]` link |
| Driver profile | `/drivers/[id]` link |

---

## Environment Variables

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md):

| Variable | Integration |
|----------|-------------|
| `VALHALLA_URL` | Route optimization |
| `OSRM_URL` | Distance / ETA refinement |
| `FLEETBASE_API_URL` | Adapter base |
| `FLEETBASE_API_KEY` | Adapter auth |
| `FLEETBASE_DISPATCH_BRIDGE` | Enable orchestrator + dispatch sync |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Admin map visualization |

---

## WebSocket Flow (Live Execution)

```
Browser (LiveMapApp)
    │  wss /v1/admin/operations/live-map/ws?token=...
    ▼
operations.py websocket handler
    ▼
LiveMapService.snapshot + push loop
    ▼
Driver locations, orders, vehicles (Porterchain DB)
```

Route Center `/live-execution` REST endpoint provides initial snapshot; WS unchanged.

---

## Dispatch Sequence

```
1. User selects optimized plan + driver (admin UI)
2. POST /v1/admin/route-center/plans/{id}/dispatch
3. RouteCenterService.dispatch_plan
4. For each order_id:
   a. AdminOperationsService.assign_driver → OrderState.DRIVER_ASSIGNED
   b. BookingSyncService.push_driver_assignment → FleetbaseAdapter.dispatch
5. commit_orchestrator if fleetbase_run_id present
6. AdminAuditLog route.dispatched
```

---

## Error Handling

| Error | HTTP | Meaning |
|-------|------|---------|
| `route_plan_not_found` | 404 | Invalid plan ID |
| `route_plan_locked` | 400 | Plan already dispatched/active |
| `dispatch_approval_required` | 403 | `requires_approval` without approve |
| `insufficient_stops` | 400 | < 2 stops for optimization |
| `missing_coordinates` | 400 | Stops lack lat/lng |

Fleetbase failures enqueue via `RetryQueue` in `BookingSyncService` (existing pattern).
