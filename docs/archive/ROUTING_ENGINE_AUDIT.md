# Porterchain — Routing Engine Audit

**Reference:** [masterrule.md](./masterrule.md) §11 · [INTEGRATIONS.md](./INTEGRATIONS.md)  
**Audit date:** 2026-06-30 · **Doc updated:** 2026-07-04  
**Canonical:** [OSRM_USAGE.md](./OSRM_USAGE.md) · [VALHALLA_USAGE.md](./VALHALLA_USAGE.md)

---

## Engine responsibilities

| Responsibility              | Google | OSRM        | Valhalla      | Fleetbase         |
| --------------------------- | ------ | ----------- | ------------- | ----------------- |
| Distance calculation        | ❌     | ✅          | ✅ (`/route`) | ✅ (execution)    |
| Travel time / ETA legs      | ❌     | ✅          | ✅            | ✅                |
| Matrix / nearest driver     | ❌     | ⚠️ Partial  | ⚠️ Partial    | ✅                |
| Route optimization          | ❌     | ❌          | ✅ (path)     | ✅ (orchestrator) |
| Multi-stop sequencing       | ❌     | ⚠️ Leg sum  | ✅            | ✅                |
| GPS / live tracking         | ❌     | ❌          | ❌            | ✅                |
| Pricing authoritative input | ❌     | ✅ fallback | ✅ primary    | ❌                |
| Map visualization           | ✅     | ❌          | ❌            | ❌                |

---

## Single implementation boundary

All Porterchain Python routing HTTP calls go through:

**`services/python/porterchain_services/maps/service.py`** → `MapsService`

Bridge for pricing:

**`apps/api/src/porterchain_api/services/routing.py`** → `resolve_route_distance()`

---

## Implementation map

### Website quote preview (`website/src/lib/quote/routing.ts`)

| Engine    | Role                                   | Status |
| --------- | -------------------------------------- | ------ |
| Valhalla  | Primary when `ROUTING_ENGINE=valhalla` | ✅     |
| OSRM      | Fallback / default when env unset      | ✅     |
| Haversine | Last-resort estimate in quote flow     | ✅     |

**Note:** UX preview only — masterrule §11. Porterchain API revalidates via `MapsService`.

**Default mismatch:** Website defaults to `osrm` when `ROUTING_ENGINE` unset; API defaults to `valhalla`. Align env in production.

### Porterchain API (`apps/api/`)

| Path                                   | Engine                                       | Status                   |
| -------------------------------------- | -------------------------------------------- | ------------------------ |
| `services/routing.py`                  | `MapsService`                                | ✅                       |
| `services/pricing.py`                  | `resolve_route_distance()`                   | ✅                       |
| `merchant_engine/booking_service.py`   | Same                                         | ✅                       |
| `booking_engine/quote_service.py`      | Same (multi-stop)                            | ✅                       |
| `merchant_engine/tracking_service.py`  | OSRM ETA + Valhalla routes                   | ✅                       |
| `admin_engine/route_center_service.py` | Optimize + simulate + Fleetbase orchestrator | ✅                       |
| `admin_engine/live_map_service.py`     | Haversine nearest drivers                    | ⚠️ Acceptable for ops UI |

### Driver platform (`services/driver-platform/`)

| Path                               | Role                                          | Status |
| ---------------------------------- | --------------------------------------------- | ------ |
| `porterchain_driver/navigation.py` | OSRM ETA polylines, Valhalla optimized routes | ✅     |

### Fleetbase integration

| Path                                        | Role                             | Status          |
| ------------------------------------------- | -------------------------------- | --------------- |
| Fleetbase Docker `OSRM_HOST` / `VALHALLA_*` | Execution routing                | ✅ override yml |
| `fleetbase-adapter/.../routes/`             | Route geometry via Fleetbase API | ✅              |

Frontends render polylines from API — never call OSRM/Valhalla directly (enforced in `@porterchain/mobile-maps` via `verifyRoutingEngines()`).

---

## `MapsService` methods

| Method                            | Status                                   |
| --------------------------------- | ---------------------------------------- |
| `route(origin, destination)`      | ✅ Valhalla or OSRM per `routing_engine` |
| `route_distance_meters(points[])` | ✅ Multi-leg sum                         |
| `_valhalla_route`                 | ✅ POST `/route`, `costing: auto`        |
| `_osrm_route`                     | ✅ GET `/route/v1/driving/...`           |

Haversine fallback when routing unreachable: `resolve_route_distance()` → `porterchain_pricing.total_route_meters()`.

---

## Infrastructure

| Engine          | Local dev                                        | Config                                   |
| --------------- | ------------------------------------------------ | ---------------------------------------- |
| Valhalla        | `porterchain-valhalla` :8002 (profile `routing`) | `VALHALLA_BASE_URL`, `VALHALLA_BASE_URI` |
| OSRM            | Public router or self-hosted                     | `OSRM_HOST`, `OSRM_URL`                  |
| Fleetbase stack | Shares routing env in override                   | `env/fleetbase.env.example`              |

See [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) and [integrations.yaml](./integrations.yaml).

---

## Duplication analysis

| Duplicate                             | Resolution                                              |
| ------------------------------------- | ------------------------------------------------------- |
| Website `routing.ts` vs `MapsService` | ⚠️ Intentional — preview (TS) vs authoritative (Python) |
| Pricing haversine vs road network     | ✅ API uses Valhalla/OSRM with haversine fallback       |
| `OSRM_HOST` not mapping to `osrm_url` | ✅ Fixed — `AliasChoices` in `PlatformSettings`         |
| Multiple Python routing clients       | ✅ Single `MapsService`                                 |

---

## Gaps remaining

| Gap                                            | Priority | Notes                                                 |
| ---------------------------------------------- | -------- | ----------------------------------------------------- |
| Bulk distance matrix API for merchant CSV      | P2       | Not exposed                                           |
| `route.optimized` on domain event bus          | P2       | Admin audit log only — Route Center `optimize_plan()` |
| Website/API `ROUTING_ENGINE` default alignment | P2       | Set explicitly in env                                 |
| Valhalla truck restrictions / avoid tolls      | P3       | Future                                                |
| Nearest driver via OSRM matrix                 | P3       | Live map uses haversine                               |

---

## Conclusion

**No routing ownership violations found.** Google is excluded from routing. Valhalla is primary for API pricing and optimized paths; OSRM provides ETA legs and fallback. Fleetbase owns execution routing, GPS, and orchestrator runs.
