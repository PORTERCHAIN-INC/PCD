# Route Center Audit

**Last verified:** 2026-07-04  
**Scope:** Admin Enterprise Route Center (`/routes/*`, `/v1/admin/route-center/*`)  
**Authority:** [masterrule.md](./masterrule.md)  
**Architecture:** [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md)

---

## Executive summary

Route Center is **implemented** in the July 2026 monorepo. Logistics operations remain split across Control Tower, Live Map, Orders 360, and Reports — Route Center adds plan-centric planning without replacing those modules.

---

## Implemented (reused + new)

| Capability | Location | Route Center usage |
| ---------- | -------- | ------------------ |
| Control Tower KPIs & queue | `ControlTowerService`, `/v1/admin/operations/*` | Planning queue source |
| Driver assignment | `AdminOperationsService.assign_driver` | Dispatch execution |
| Fleetbase dispatch bridge | `BookingSyncService`, `FleetbaseAdapter` | Orchestrator + outbound sync |
| Live map + WebSocket | `LiveMapService`, live-map WS | Live Execution embeds `LiveMapApp` |
| Google Maps viz | `MapCanvas`, `@porterchain/maps` | Traffic, drivers, geofences |
| Valhalla / OSRM | `MapsService` | Optimization & simulation distance |
| Fleetbase orchestrator | `adapter.routes.run_orchestrator` / `commit_orchestrator` | Optimize + dispatch commit |
| RBAC | `admin_engine/rbac.py` | `routes`, `routes_read`, `routes_dispatch` |
| Audit logging | `AdminAuditLog` | Plan lifecycle + `route.optimized` / `route.dispatched` |
| Assignable drivers | `/v1/admin/operations/assignable-drivers` | Dispatch driver picker |
| Route plans & templates | `RouteCenterPlan`, `RouteCenterTemplate` | Full CRUD + templates |
| Admin UI (10 sections) | `apps/admin/src/app/(ops)/routes/*` | Dashboard through Templates |
| API client | `apps/admin/src/lib/route-center.ts` | Typed admin fetches |
| Driver route optimizer hook | `services/driver-platform/.../route_optimizer.py` | Reads active plans for driver |

---

## Partially implemented

| Capability | Gap |
| ---------- | --- |
| Multi-stop optimization | Leg-sum via `MapsService`; not full Valhalla TSP / time-window solver |
| Drag-and-drop stop reorder | Backend `stops` PATCH; no visual DnD UI |
| OSRM table matrix | Single-route / leg refinement only |
| Dedicated Route Center WS | Reuses operations live-map WebSocket |
| Route 360 extended tabs | Documents / Support / Claims link out to existing modules |
| Geofence editing | Read-only via live map |
| Bulk merge/split UI | APIs exist; limited UI |
| Template scheduler | `schedule` JSON on template; no cron runner |
| Domain event `route.optimized` | Admin audit log only — not event bus |

---

## Architecture compliance

| Check | Result |
| ----- | ------ |
| Admin → Fleetbase direct HTTP | **None** — adapter + `BookingSyncService` |
| Admin → Valhalla/OSRM direct | **None** — `MapsService` only |
| Business logic in router | **None** — delegates to `RouteCenterService` |
| Fleetbase as order system of record | **Compliant** — Porterchain order mirror canonical |
| Skipped adapter on dispatch | **Fixed** — `push_driver_assignment` on dispatch |

---

## Duplicate avoidance

| Area | Approach |
| ---- | -------- |
| Control Tower vs Live Map vs Route Live Execution | Composed — Route Center links to full `LiveMapApp` |
| Dispatch queue endpoints | Route Center uses `ControlTowerService.queue` — no third queue API |
| `AdminOperationsService` vs `ControlTowerService` | Composed inside `RouteCenterService` |
| Distance calculation | `MapsService.route_distance_meters` for routes; pricing uses `resolve_route_distance()` separately |

---

## Navigation coverage

| Section | Path | Status |
| ------- | ---- | ------ |
| Dashboard | `/routes` | ✅ |
| Planning Queue | `/routes/planning-queue` | ✅ |
| Route Builder | `/routes/builder` | ✅ |
| Optimization | `/routes/optimization` | ✅ |
| Dispatch | `/routes/dispatch` | ✅ |
| Live Execution | `/routes/live` | ✅ |
| Route 360 | `/routes/[id]` | ✅ |
| Analytics | `/routes/analytics` | ✅ |
| History | `/routes/history` | ✅ |
| Templates | `/routes/templates` | ✅ |

---

## Backend artifacts

| Artifact | Path |
| -------- | ---- |
| Service | `apps/api/src/porterchain_api/admin_engine/route_center_service.py` |
| Router | `apps/api/src/porterchain_api/routers/route_center.py` |
| Schemas | `apps/api/src/porterchain_api/schemas_route_center.py` |
| Models | `apps/api/src/porterchain_api/admin_models.py` |
| Migration | `apps/api/alembic/versions/i0j1k2l3m4n5_route_center_tables.py` |
