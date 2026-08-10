# OSRM usage

**Type:** CANONICAL  
**Last verified:** 2026-08-07

**Role:** Distance, travel time, and ETA legs — fallback when Valhalla is unavailable.  
**Not** for route optimization UI or Fleetbase execution ownership.

Primary engine: [VALHALLA_USAGE.md](./VALHALLA_USAGE.md).

---

## Responsibilities

| Function                             | Status                                                   |
| ------------------------------------ | -------------------------------------------------------- |
| Distance / travel time               | ✅ via `MapsService`                                     |
| Multi-leg sum                        | ✅ `route_distance_meters()`                             |
| Pricing distance fallback            | ✅ when `ROUTING_ENGINE=osrm` or Valhalla down           |
| ETA legs (merchant/driver tracking)  | ✅                                                       |
| Public merchant matrix API           | ❌ not exposed                                           |
| Nearest-driver spatial math in admin | ❌ — use Valhalla/adapter; no live-map haversine service |

---

## Call sites

| Location                                               | Purpose                   |
| ------------------------------------------------------ | ------------------------- |
| `services/python/porterchain_services/maps/service.py` | Authoritative HTTP client |
| `apps/api/.../services/routing.py`                     | Pricing bridge            |
| `apps/api/.../booking_engine/quote_service.py`         | Quote distance            |
| `apps/api/.../merchant_engine/tracking_service.py`     | Tracking ETA              |
| `services/driver-platform/.../navigation.py`           | Driver ETA polylines      |
| `website/src/lib/quote/routing.ts`                     | Quote preview fallback    |

Frontends never call OSRM directly. Former admin Route Center / live-map OSRM matrix paths were **removed** (Fleetbase-first).

---

## Configuration

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) and [DOCKER_SETUP.md](./DOCKER_SETUP.md) (`ROUTING_ENGINE`, OSRM host).
