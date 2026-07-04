# Route Center Audit

**Date:** June 30, 2026  
**Scope:** Admin Operations Route module → Enterprise Route Center  
**Authority:** [masterrule.md](./masterrule.md)

---

## Executive Summary

The admin portal previously had **no dedicated Route Center**. Logistics operations were split across Control Tower (`/operations`), Live Map (`/live-map`), Orders 360, and Reports. This audit documents what existed, what was partial, what was missing, and what was added without rebuilding working functionality.

---

## Already Implemented (Reused)

| Capability                          | Location                                                           | Route Center usage                            |
| ----------------------------------- | ------------------------------------------------------------------ | --------------------------------------------- |
| Control Tower KPIs & dispatch queue | `ControlTowerService`, `/v1/admin/operations/*`                    | Planning queue buckets source data            |
| Driver assignment                   | `AdminOperationsService.assign_driver`                             | Dispatch execution                            |
| Fleetbase dispatch bridge           | `BookingSyncService`, `FleetbaseAdapter`                           | Outbound driver/order sync                    |
| Live map + WebSocket                | `LiveMapService`, `/v1/admin/operations/live-map/ws`               | Live Execution page embeds `LiveMapApp`       |
| Google Maps visualization           | `MapCanvas`, `GoogleMapsProvider`                                  | Live map layers (traffic, drivers, geofences) |
| Valhalla / OSRM routing             | `porterchain_services.maps.MapsService`                            | Optimization & simulation distance            |
| Fleetbase orchestrator              | `FleetbaseAdapter.routes.run_orchestrator` / `commit_orchestrator` | Optimization commit path                      |
| RBAC admin modules                  | `admin_engine/rbac.py`                                             | `routes`, `routes_read`, `routes_dispatch`    |
| Audit logging                       | `AdminAuditLog`                                                    | Plan create/update/dispatch events            |
| Assignable drivers API              | `/v1/admin/operations/assignable-drivers`                          | Dispatch UI driver picker                     |

---

## Partially Implemented

| Capability              | Gap                                                 | Status after upgrade                                    |
| ----------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| Route planning          | Control Tower had queue only, no plan entity        | `RouteCenterPlan` model + builder UI                    |
| Multi-stop optimization | MapsService leg routing only; no dedicated admin UI | `/route-center/plans/{id}/optimize` + Optimization page |
| Route simulation        | Pricing used distance; no pre-dispatch simulation   | `simulate_plan` + Route 360 overview                    |
| Vehicle recommendation  | Pricing hints in booking flow                       | Heuristic `_recommend_vehicle` on plans                 |
| Driver recommendation   | Assignable drivers list only                        | `_recommendations` with driver score from tower         |
| Route templates         | None                                                | `RouteCenterTemplate` + Templates page                  |
| Route 360               | Order 360 existed; no route-centric view            | `/routes/[id]` with tabs                                |
| Dispatch approval       | RBAC on dispatch module                             | `requires_approval` field + approve flag on dispatch    |
| Analytics               | General reports page                                | Route-specific `/route-center/analytics`                |
| Drag-and-drop builder   | Not in admin                                        | Manual/semi-auto via planning queue selection → builder |
| Route replay on map     | Live map playback endpoint exists                   | Linked via Live Execution / fleet map                   |

---

## Missing (Future Incremental Work)

| Capability                                 | Notes                                                   |
| ------------------------------------------ | ------------------------------------------------------- |
| Full drag-and-drop stop reorder UI         | Backend supports `stops` PATCH; UI not yet visual DnD   |
| True Valhalla TSP / time-window solver     | Current: leg-sum routing + strategy metadata            |
| OSRM table service for full matrix         | OSRM single-route refinement added; not full N×N matrix |
| Dedicated Route Center WebSocket           | Reuses operations live-map WS                           |
| Route 360: Documents, Support, Claims tabs | Links to existing order/claims modules                  |
| Geofence editing from Route Center         | Read-only via live map                                  |
| Bulk merge/split UI                        | APIs: `merge`, `split`; no dedicated UI yet             |
| Merchant-specific template scheduler       | `schedule` JSON on template; no cron runner             |
| Custom strategy editor                     | `custom` enum value; no rule builder UI                 |
| OTP / signature / photo on stop rows       | Order POD data via Orders 360                           |

---

## Architecture Violations

| Check                                    | Result                                                         |
| ---------------------------------------- | -------------------------------------------------------------- |
| Admin → Fleetbase direct HTTP            | **None** — all dispatch via `BookingSyncService` + adapter     |
| Admin → Valhalla/OSRM direct             | **None** — via `MapsService` in application layer              |
| Business logic in router                 | **None** — `route_center.py` delegates to `RouteCenterService` |
| Fleetbase as system of record for orders | **Compliant** — Porterchain order mirror canonical             |

---

## Fleetbase Violations

| Check                           | Result                                                     |
| ------------------------------- | ---------------------------------------------------------- |
| UI calls Fleetbase API          | **None**                                                   |
| Router imports Fleetbase client | **None** — uses `get_fleetbase_integration()`              |
| Order state owned by Fleetbase  | **None** — `transition_order_state` in Porterchain         |
| Skipped adapter on dispatch     | **Fixed** — `dispatch_plan` calls `push_driver_assignment` |

---

## Duplicate Components

| Duplicate                                                 | Recommendation                                                                           |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Control Tower map tab vs Live Map vs Route Live Execution | **Keep** — Control Tower embeds legacy snapshot; Route Center links to full `LiveMapApp` |
| `GET /v1/admin/dispatch/queue` vs `/operations/queue`     | **Do not add third** — Route Center uses `ControlTowerService.queue` via planning queue  |
| `AdminOperationsService` vs `ControlTowerService`         | **Composed** in `RouteCenterService`                                                     |

---

## Duplicate APIs

| Endpoint                        | Overlap        | Route Center approach                                                 |
| ------------------------------- | -------------- | --------------------------------------------------------------------- |
| `/v1/admin/operations/stats`    | Dashboard KPIs | New `/route-center/dashboard` aggregates plans + tower stats          |
| `/v1/admin/operations/live-map` | Live execution | `/route-center/live-execution` delegates to `LiveMapService.snapshot` |
| `/v1/admin/dispatch/*`          | Assign driver  | Reuses `AdminOperationsService` inside service layer                  |

---

## Duplicate Business Logic

| Logic                | Location                      | Mitigation                                        |
| -------------------- | ----------------------------- | ------------------------------------------------- |
| Queue listing        | Control tower + dispatch      | Single source: `_tower.queue()` in planning queue |
| Live map snapshot    | operations + live_map routers | Single source: `LiveMapService`                   |
| Distance calculation | pricing + maps                | `MapsService.route_distance_meters` for routes    |

---

## New Artifacts

### Backend

- `admin_models.RouteCenterPlan`, `RouteCenterTemplate`
- `admin_engine/route_center_service.py`
- `routers/route_center.py` — `/v1/admin/route-center/*`
- `schemas_route_center.py`
- Alembic `i0j1k2l3m4n5_route_center_tables.py`

### Admin frontend

- `/routes/*` — 10 navigation sections (Dashboard through Templates)
- `lib/route-center.ts` API client
- `components/routes/RouteCenterNav.tsx`

### Documentation

- `ROUTE_CENTER_AUDIT.md` (this file)
- `ROUTE_CENTER_ARCHITECTURE.md`
- `ROUTE_CENTER_INTEGRATION.md`
- `ROUTE_CENTER_PERFORMANCE.md`

---

## Navigation Coverage

| Required       | Path                     | Status |
| -------------- | ------------------------ | ------ |
| Dashboard      | `/routes`                | ✅     |
| Planning Queue | `/routes/planning-queue` | ✅     |
| Route Builder  | `/routes/builder`        | ✅     |
| Optimization   | `/routes/optimization`   | ✅     |
| Dispatch       | `/routes/dispatch`       | ✅     |
| Live Execution | `/routes/live`           | ✅     |
| Route 360      | `/routes/[id]`           | ✅     |
| Analytics      | `/routes/analytics`      | ✅     |
| History        | `/routes/history`        | ✅     |
| Templates      | `/routes/templates`      | ✅     |
