# Route Center Integration

**Last verified:** 2026-07-04  
**Authority:** [masterrule.md](./masterrule.md) §7, §8  
**Architecture:** [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md)

---

## Integration map

| System | Role in Route Center | Access path |
| ------ | -------------------- | ----------- |
| Porterchain Order mirror | Planning queue, stops, dispatch | SQLAlchemy `Order` |
| Valhalla | Multi-stop leg routing | `MapsService` (`routing_engine=valhalla`) |
| OSRM | ETA / distance refinement | `MapsService` + `_osrm_leg_matrix` |
| Fleetbase Adapter | Orchestrator run/commit, dispatch sync | `get_fleetbase_integration(settings)` |
| Google Maps | Map visualization only | Admin `MapCanvas` (client) |
| Clerk | Admin authentication | `get_admin_context` |
| Event bus | Order state on dispatch | `AdminOperationsService` → `emit_event` |

---

## Fleetbase adapter calls

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

## Maps integration

### Valhalla (primary)

- Endpoint: `{valhalla_url}/route` (default `http://localhost:8002`)
- Used for: leg-by-leg distance accumulation across stops
- Config: `VALHALLA_BASE_URL`, `VALHALLA_BASE_URI` → `PlatformSettings.valhalla_url`

### OSRM (refinement)

- Endpoint: `{osrm_url}/route/v1/driving/{coords}`
- Used for: optional full-path refinement on optimize
- Config: `OSRM_HOST`, `OSRM_URL` → `PlatformSettings.osrm_url`

### Fallback

Route Center does **not** silently fall back to haversine. Unreachable engines → `400 insufficient_stops` / zero distance. Pricing haversine fallback is separate (`resolve_route_distance()`).

---

## Reused admin APIs (not duplicated)

| Consumer | Reused endpoint / service |
| -------- | ------------------------- |
| Dispatch driver picker | `GET /v1/admin/operations/assignable-drivers` |
| Live map | `LiveMapApp` → live-map REST + WS |
| Order detail from Route 360 | Link to `/orders/[id]` |
| Driver profile | Link to `/drivers/[id]` |

---

## Environment variables

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md):

| Variable | Integration |
| -------- | ------------- |
| `VALHALLA_BASE_URL` | Route optimization (host) |
| `VALHALLA_BASE_URI` | Docker-internal Valhalla |
| `OSRM_HOST` / `OSRM_URL` | Distance / ETA refinement |
| `ROUTING_ENGINE` | `valhalla` (API default) |
| `FLEETBASE_API_URL` | Adapter base |
| `fleetbase_api_key` (Settings) | Adapter auth — set in API env |
| `FLEETBASE_DISPATCH_BRIDGE` | Orchestrator + dispatch sync |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Admin map visualization |

Local dev defaults: `env/api.env.example`

---

## WebSocket flow (Live Execution)

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

Route Center `GET /live-execution` provides initial snapshot; WS unchanged.

---

## Dispatch sequence

```
1. User selects optimized plan + driver (admin UI)
2. POST /v1/admin/route-center/plans/{id}/dispatch
3. RouteCenterService.dispatch_plan
4. commit_orchestrator if fleetbase_run_id present
5. For each order_id:
   a. AdminOperationsService.assign_driver → DRIVER_ASSIGNED
   b. BookingSyncService.push_driver_assignment → FleetbaseAdapter.dispatch
6. AdminAuditLog route.dispatched
```

---

## Error handling

| Error | HTTP | Meaning |
| ----- | ---- | ------- |
| `route_plan_not_found` | 404 | Invalid plan ID |
| `route_plan_locked` | 400 | Plan already dispatched/active |
| `dispatch_approval_required` | 403 | `requires_approval` without approve |
| `insufficient_stops` | 400 | < 2 stops for optimization |
| `missing_coordinates` | 400 | Stops lack lat/lng |
| `driver_not_found` | 404 | Invalid driver ID |

Fleetbase failures enqueue via `RetryQueue` in `BookingSyncService` (existing pattern).

---

## Related

| Document | Purpose |
| -------- | ------- |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) | Fleetbase bridge |
| [ROUTING_ENGINE_AUDIT.md](./ROUTING_ENGINE_AUDIT.md) | Engine ownership |
