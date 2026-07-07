# OSRM Usage

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Role:** Distance, travel time, and ETA legs — **not** route optimization or dispatch.

> **Valhalla (primary):** [VALHALLA_USAGE.md](./VALHALLA_USAGE.md) · **Historical audit:** [docs/archive/ROUTING_ENGINE_AUDIT.md](./docs/archive/ROUTING_ENGINE_AUDIT.md)

---

## Responsibilities

| Function               | Owner | Status                                                                      |
| ---------------------- | ----- | --------------------------------------------------------------------------- |
| Distance calculation   | OSRM  | ✅                                                                          |
| Travel time / ETA legs | OSRM  | ✅                                                                          |
| Multi-leg leg sum      | OSRM  | ✅ via `MapsService.route_distance_meters()`                                |
| Matrix calculations    | OSRM  | ⚠️ Partial — Route Center `_osrm_leg_matrix`; no public merchant matrix API |
| Nearest driver         | OSRM  | ❌ Live map uses haversine (`live_map_service.py`)                          |
| Pricing distance input | OSRM  | ✅ Fallback when `ROUTING_ENGINE=osrm` or Valhalla unavailable              |
| Bulk distance matrix   | OSRM  | ❌ Not exposed to merchant portal                                           |

**Optimization and dispatch** belong to Valhalla (path) + Fleetbase (execution) — not OSRM.

---

## Call sites

| Location                                               | Purpose                             | Direct HTTP?                           |
| ------------------------------------------------------ | ----------------------------------- | -------------------------------------- |
| `services/python/porterchain_services/maps/service.py` | Authoritative API routing           | ✅ Python httpx                        |
| `apps/api/src/porterchain_api/services/routing.py`     | Pricing distance bridge             | Via `MapsService`                      |
| `apps/api/.../merchant_engine/booking_service.py`      | Merchant booking distance           | Via `resolve_route_distance()`         |
| `apps/api/.../booking_engine/quote_service.py`         | Quote distance                      | Via `resolve_route_distance()`         |
| `apps/api/.../merchant_engine/tracking_service.py`     | ETA legs for live tracking          | Via `MapsService`                      |
| `apps/api/.../admin_engine/route_center_service.py`    | Optional OSRM leg matrix refinement | Via `MapsService` / `_osrm_leg_matrix` |
| `services/driver-platform/.../navigation.py`           | Driver ETA polylines                | Via `MapsService`                      |
| `website/src/lib/quote/routing.ts`                     | Quote preview (fallback engine)     | Server-side Next route                 |
| Fleetbase Docker `OSRM_HOST`                           | Execution routing                   | Fleetbase internal                     |
| `fleetbase-adapter/.../routes/`                        | Distance/time read                  | Via Fleetbase API                      |

Frontends **never** call OSRM directly.

---

## Configuration

| Env var     | Maps to                     | Notes           |
| ----------- | --------------------------- | --------------- |
| `OSRM_HOST` | `PlatformSettings.osrm_url` | Primary alias   |
| `OSRM_URL`  | `PlatformSettings.osrm_url` | Alternate alias |

Default when unset in website: `https://router.project-osrm.org` (public router — dev only).  
API `osrm_url` defaults to empty until env is set; `env/api.env.example` sets the public router for local dev.

---

## Engine selection

| Runtime                              | Default when `ROUTING_ENGINE` unset                              |
| ------------------------------------ | ---------------------------------------------------------------- |
| Porterchain API (`PlatformSettings`) | `valhalla` — OSRM used as fallback leg                           |
| Website quote preview (`routing.ts`) | `osrm` — set `ROUTING_ENGINE=valhalla` in website env for parity |

`MapsService.route()` uses Valhalla when `routing_engine=valhalla` and `valhalla_url` is set; falls back to OSRM when configured.

---

## Duplication check

| Issue                                   | Status                                                 |
| --------------------------------------- | ------------------------------------------------------ |
| Second OSRM client in API routers       | ❌ None — single `MapsService`                         |
| Frontend authoritative pricing via OSRM | ❌ None                                                |
| Website TS vs Python `MapsService`      | ⚠️ Intentional — preview vs authoritative revalidation |

---

## Status summary

✅ Correct for distance/ETA and fallback routing  
⚠ Matrix and nearest-driver not fully wired  
❌ Bulk merchant matrix endpoint missing

---

## Related

| Document                                                           | Purpose                  |
| ------------------------------------------------------------------ | ------------------------ |
| [docs/architecture/OSRM_FLOW.md](./docs/architecture/OSRM_FLOW.md) | Flow diagram (Group 27)  |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)             | Env reference            |
| [masterrule.md](./masterrule.md)                                   | Locked routing ownership |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
