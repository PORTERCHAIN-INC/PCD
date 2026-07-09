# Route Center Architecture

**Type:** POINTER — **removed 2026-07-05.** Route planning and optimization live in **Fleetbase console** (`:4200`) and **Admin Control Tower** (`/operations`, `/live-map`). Do not reintroduce `RouteCenterService` or `/routes/*` admin pages.

**Superseded by:** [docs/architecture/ADMIN_CONTROL_TOWER.md](./docs/architecture/ADMIN_CONTROL_TOWER.md) · [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)

---

## Historical reference (pre-removal)

```
Admin Portal (apps/admin/) — /routes/*
        │
        ▼  HTTPS + Clerk JWT
Porterchain API (:8001)
        │
        ├── RouteCenterService (admin_engine/route_center_service.py)
        │         ├── ControlTowerService      (queue, KPIs)
        │         ├── AdminOperationsService   (assign driver)
        │         ├── LiveMapService           (live execution snapshot)
        │         ├── MapsService              (Valhalla / OSRM)
        │         └── BookingSyncService       (Fleetbase outbound)
        │
        ▼
Fleetbase Adapter (services/fleetbase-adapter/)
        │
        ▼
Fleetbase Core (dispatch, GPS, orchestrator, POD)
```

**Rule:** Admin never calls Fleetbase, Valhalla, or OSRM directly.

---

## Module boundaries

| Layer               | Responsibility                       | Files                                                   |
| ------------------- | ------------------------------------ | ------------------------------------------------------- |
| Router              | HTTP, RBAC, schema validation        | `routers/route_center.py`                               |
| Application service | Orchestration, audit, plan lifecycle | `admin_engine/route_center_service.py`                  |
| Domain models       | Plan + template persistence          | `admin_models.RouteCenterPlan`, `RouteCenterTemplate`   |
| Integration         | External systems                     | `MapsService`, `FleetbaseAdapter`, `BookingSyncService` |
| UI                  | Presentation only                    | `apps/admin/src/app/(ops)/routes/*`                     |
| API client          | Typed fetch wrapper                  | `apps/admin/src/lib/route-center.ts`                    |

---

## Data model

### RouteCenterPlan

| Field               | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `status`            | `waiting → planned → optimized → dispatched → active → completed` (also `cancelled`) |
| `order_ids`         | Porterchain order mirror IDs                                                         |
| `stops`             | Pickup/delivery stop JSON (from orders or manual PATCH)                              |
| `strategy`          | Optimization strategy enum                                                           |
| `simulation`        | Pre-dispatch distance, fuel, cost, revenue, profit                                   |
| `recommendations`   | Vehicle class, driver, warnings                                                      |
| `fleetbase_run_id`  | Orchestrator run from adapter                                                        |
| `requires_approval` | Dispatch approval workflow flag                                                      |

### RouteCenterTemplate

Reusable stop patterns for daily/weekly/merchant/recurring routes.

Migration: `apps/api/alembic/versions/i0j1k2l3m4n5_route_center_tables.py`

---

## API surface

Prefix: **`/v1/admin/route-center`**

| Endpoint group                                                                                                               | RBAC module       |
| ---------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| `meta`, `dashboard`, `planning-queue`, plans (read), `simulate`, `recommendations`, `analytics`, `history`, `live-execution` | `routes_read`     |
| plans (write), `optimize`, templates, merge/split/clone                                                                      | `routes`          |
| `dispatch`, `dispatch/bulk`, pause, resume, cancel                                                                           | `routes_dispatch` |

---

## Optimization pipeline

1. **Build stops** from Porterchain `Order.pickup` / `Order.dropoff`
2. **Valhalla** — multi-leg distance & duration (`MapsService.route_distance_meters`)
3. **OSRM** — optional leg-matrix refinement when configured (`_osrm_leg_matrix`)
4. **Simulate** — fuel, cost, revenue, capacity, late-risk heuristics
5. **Recommend** — vehicle class, nearest assignable driver, warnings
6. **Fleetbase orchestrator** — `adapter.routes.run_orchestrator` when `fleetbase_dispatch_bridge` enabled
7. **Dispatch** — `assign_driver` per order + `push_driver_assignment` + `commit_orchestrator`

`route.optimized` → `AdminAuditLog` (not domain event bus).

---

## Realtime

Live Execution embeds `LiveMapApp` → WebSocket `/v1/admin/operations/live-map/ws`. Google Maps is visualization-only; positions flow Porterchain API → admin WS.

---

## Security

- RBAC: `routes`, `routes_read`, `routes_dispatch` ([RBAC_MATRIX.md](./RBAC_MATRIX.md))
- Mutations write `AdminAuditLog` with `resource_type=route_plan`
- Dispatch approval: `requires_approval` + `approve` flag (`admin` / `super_admin` bypass)

---

## Relationship to Control Tower

Control Tower (`/operations`) remains the **operational dispatch board** for ad-hoc assignment. Route Center adds **plan-centric** workflow: multi-order plans, optimization strategies, simulation, templates, Route 360. No Control Tower functionality removed at router level.

---

## Related

| Document                                                                    | Purpose                                  |
| --------------------------------------------------------------------------- | ---------------------------------------- |
| [OSRM_USAGE.md](./OSRM_USAGE.md) · [VALHALLA_USAGE.md](./VALHALLA_USAGE.md) | Valhalla/OSRM ownership                  |
| [PRICING_ENGINE.md](./PRICING_ENGINE.md)                                    | Pricing (separate from route simulation) |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
