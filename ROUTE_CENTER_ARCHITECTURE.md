# Route Center Architecture

**Authority:** [masterrule.md](./masterrule.md) §1 Locked architecture, §3 Layered architecture

---

## Layer Stack

```
Admin Portal (Next.js)
        │
        ▼
Route Center UI (/routes/*)
        │
        ▼  HTTPS + Clerk JWT
Porterchain API — Logistics Orchestrator
        │
        ├── RouteCenterService (admin_engine)
        │         ├── ControlTowerService      (queue, drivers, KPIs)
        │         ├── AdminOperationsService   (assign driver)
        │         ├── LiveMapService           (live execution snapshot)
        │         ├── MapsService              (Valhalla / OSRM)
        │         └── BookingSyncService       (Fleetbase outbound)
        │
        ▼
Fleetbase Adapter (porterchain_fleetbase_adapter)
        │
        ▼
Fleetbase Core (dispatch, GPS, orchestrator, POD)
```

**Rule:** Admin never calls Fleetbase, Valhalla, or OSRM directly.

---

## Module Boundaries

| Layer | Responsibility | Route Center files |
|-------|----------------|-------------------|
| Router | HTTP, RBAC guard, schema validation | `routers/route_center.py` |
| Application service | Orchestration, audit, plan lifecycle | `admin_engine/route_center_service.py` |
| Domain models | Plan + template persistence | `admin_models.RouteCenterPlan`, `RouteCenterTemplate` |
| Integration | External systems | `MapsService`, `FleetbaseAdapter`, `BookingSyncService` |
| UI | Presentation only | `apps/admin/src/app/(ops)/routes/*` |

---

## Data Model

### RouteCenterPlan

| Field | Purpose |
|-------|---------|
| `status` | `waiting → planned → optimized → dispatched → active → completed` |
| `order_ids` | Porterchain order mirror IDs |
| `stops` | Pickup/delivery stop JSON (built from orders or manual PATCH) |
| `strategy` | Optimization strategy enum |
| `simulation` | Pre-dispatch distance, fuel, cost, revenue, profit |
| `recommendations` | Vehicle class, driver, warnings |
| `fleetbase_run_id` | Orchestrator run from adapter |
| `requires_approval` | Dispatch approval workflow flag |

### RouteCenterTemplate

Reusable stop patterns for daily/weekly/merchant/recurring routes.

---

## API Surface

Prefix: `/v1/admin/route-center`

| Endpoint group | RBAC module |
|----------------|-------------|
| dashboard, planning-queue, plans (read) | `routes_read` |
| plans (write), optimize, templates | `routes` |
| dispatch, pause, resume, cancel | `routes_dispatch` |

---

## Optimization Pipeline

1. **Build stops** from Porterchain `Order.pickup` / `Order.dropoff`
2. **Valhalla** — multi-leg route distance & duration (`MapsService.route_distance_meters`)
3. **OSRM** — optional full-waypoint route refinement when configured
4. **Simulate** — fuel, cost, revenue, capacity, late-risk heuristics
5. **Recommend** — vehicle class, nearest assignable driver, warnings
6. **Fleetbase orchestrator** — `adapter.routes.run_orchestrator` when bridge enabled
7. **Dispatch** — `assign_driver` per order + `push_driver_assignment` + `commit_orchestrator`

---

## Realtime

Live Execution reuses the existing operations live-map WebSocket and `LiveMapApp`. Google Maps is visualization-only; positions flow Porterchain API → admin WS.

---

## Security

- RBAC: `routes`, `routes_read`, `routes_dispatch` in `MODULE_PERMISSIONS`
- All mutations write `AdminAuditLog` with `resource_type=route_plan`
- Dispatch approval: `requires_approval` + `approve` flag on dispatch (admin/super_admin bypass)

---

## Relationship to Control Tower

Control Tower remains the **operational dispatch board** for ad-hoc order assignment. Route Center adds **plan-centric** workflow:

- Multi-order route plans
- Optimization strategies
- Simulation before dispatch
- Templates and history
- Route 360 detail view

No Control Tower functionality was removed or duplicated at the router level.
