# Valhalla Usage

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**API default:** `ROUTING_ENGINE=valhalla` (`PlatformSettings.routing_engine`)

> **OSRM (ETA fallback):** [OSRM_USAGE.md](./OSRM_USAGE.md) · **Historical audit:** [docs/archive/ROUTING_ENGINE_AUDIT.md](./docs/archive/ROUTING_ENGINE_AUDIT.md)

---

## Responsibilities

| Function                            | Valhalla                          | Status                                                      |
| ----------------------------------- | --------------------------------- | ----------------------------------------------------------- |
| Pricing distance (API)              | Valhalla primary                  | ✅ via `MapsService`                                        |
| Optimized route geometry            | Valhalla                          | ✅ API + driver/merchant tracking                           |
| Multi-stop leg sum                  | Valhalla                          | ✅ `route_distance_meters()`                                |
| Route optimization (Route Center)   | Valhalla + Fleetbase orchestrator | ⚠️ Split — local optimize then Fleetbase `run_orchestrator` |
| Multi-stop sequencing (execution)   | Fleetbase                         | ✅                                                          |
| Commercial vehicle / truck costing  | Future                            | ❌ `costing: auto` only                                     |
| Avoid tolls / ferries               | Future                            | ❌                                                          |
| Merchant bulk route optimization UI | Fleetbase                         | ⚠️ Not in merchant portal                                   |

**Google Maps** never participates in routing. **OSRM** handles ETA legs when Valhalla is unavailable or engine is set to `osrm`.

---

## Infrastructure

| Component                     | Endpoint                                                         |
| ----------------------------- | ---------------------------------------------------------------- |
| Docker `porterchain-valhalla` | `http://127.0.0.1:8002` (profile `routing`)                      |
| `VALHALLA_BASE_URL`           | Host access (`http://localhost:8002`)                            |
| `VALHALLA_BASE_URI`           | Docker-internal (`http://valhalla:8002`)                         |
| Fleetbase override            | Public demo URLs in `fleetbase.porterchain.override.yml` for dev |

Start local Valhalla: `pnpm docker:up:routing` (see [DOCKER_SETUP.md](./DOCKER_SETUP.md)).

Health: `http://localhost:8002/status`

---

## Call sites

| Location                                               | Role                                   |
| ------------------------------------------------------ | -------------------------------------- |
| `services/python/porterchain_services/maps/service.py` | Authoritative API routing              |
| `apps/api/src/porterchain_api/services/routing.py`     | Pricing distance bridge                |
| `apps/api/.../admin_engine/route_center_service.py`    | Plan optimize + simulate               |
| `apps/api/.../merchant_engine/tracking_service.py`     | Optimized route polylines              |
| `services/driver-platform/.../navigation.py`           | Driver optimized route polylines       |
| `website/src/lib/quote/routing.ts`                     | Preview when `ROUTING_ENGINE=valhalla` |
| Fleetbase stack                                        | Shared routing config via override env |

---

## Engine selection note

| Runtime               | Default when `ROUTING_ENGINE` unset                        |
| --------------------- | ---------------------------------------------------------- |
| Porterchain API       | `valhalla`                                                 |
| Website quote preview | `osrm` — set `ROUTING_ENGINE=valhalla` for parity with API |

---

## Duplication check

| Duplicate Valhalla client      | Found?                  |
| ------------------------------ | ----------------------- |
| In FastAPI routers             | ❌ — only `MapsService` |
| In merchant/customer frontends | ❌                      |
| Third Python implementation    | ❌                      |

---

## Gaps

| Gap                                   | Status                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------ |
| `route.optimized` on domain event bus | ⚠️ Logged to `AdminAuditLog` in Route Center; not published to event bus |
| VROOM / multi-stop in Porterchain API | ❌ Delegated to Fleetbase orchestrator                                   |
| Truck costing profile                 | ❌ Future                                                                |
| Local Valhalla tiles for production   | ❌ Dev container only — production URL TBD                               |

---

## Related

| Document                                                                   | Purpose                 |
| -------------------------------------------------------------------------- | ----------------------- |
| [docs/architecture/VALHALLA_FLOW.md](./docs/architecture/VALHALLA_FLOW.md) | Flow diagram (Group 27) |
| [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md)             | Route Center (Group 19) |
| [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)                           | Port 8002               |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
