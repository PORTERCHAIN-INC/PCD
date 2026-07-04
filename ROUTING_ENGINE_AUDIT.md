# Porterchain — Routing Engine Audit

**Reference:** [masterrule.md](./masterrule.md) §11, [INTEGRATIONS.md](./INTEGRATIONS.md)  
**Date:** June 30, 2026

---

## Engine responsibilities

| Responsibility | Google | OSRM | Valhalla | Fleetbase |
|----------------|--------|------|----------|-----------|
| Distance calculation | ❌ | ✅ | ✅ (via `/route`) | ✅ (execution) |
| Travel time / ETA | ❌ | ✅ | ✅ | ✅ |
| Matrix / nearest driver | ❌ | ⚠️ Partial | ⚠️ Partial | ✅ |
| Route optimization | ❌ | ❌ | ✅ (primary config) | ✅ (orchestrator) |
| Multi-stop sequencing | ❌ | ⚠️ Leg sum | ✅ | ✅ |
| GPS / live tracking | ❌ | ❌ | ❌ | ✅ |
| Pricing authoritative input | ❌ | ✅ | ✅ | ❌ |

---

## Implementation map

### Website quote preview (`website/src/lib/quote/routing.ts`)

| Engine | Role | Status |
|--------|------|--------|
| Valhalla | Primary when `ROUTING_ENGINE=valhalla` | ✅ |
| OSRM | Fallback / default engine | ✅ |
| Haversine | Last-resort estimate | ✅ |

**Note:** UX preview only — masterrule §11. Server revalidates.

### Porterchain API (`apps/api/`)

| Path | Engine | Status |
|------|--------|--------|
| `services/routing.py` | Delegates to `MapsService` | ✅ **Added** |
| `services/pricing.py` | `resolve_route_distance()` | ✅ **Wired** |
| `merchant_engine/booking_service.py` | Same | ✅ **Wired** |
| `booking_engine/quote_service.py` | Same for multi-stop | ✅ **Wired** |
| `admin_engine/live_map_service.py` | Haversine for nearest drivers | ⚠️ Acceptable for ops UI |

### `porterchain_services.maps.MapsService`

| Method | Status |
|--------|--------|
| `route()` | ✅ Valhalla or OSRM per `routing_engine` |
| `route_distance_meters()` | ✅ **Added** — multi-leg sum |

### Fleetbase Docker stack

| Engine | Config | Status |
|--------|--------|--------|
| Valhalla | `VALHALLA_BASE_URL`, `:8002` | ✅ |
| OSRM | `OSRM_HOST` fallback | ✅ |

---

## Duplication analysis

| Duplicate | Resolution |
|-----------|------------|
| Website `routing.ts` vs `MapsService` | ⚠️ Intentional — website preview (TS) vs server authoritative (Python). Same engines, different runtimes. |
| Pricing `haversine` vs road network | ✅ **Fixed** — API uses Valhalla/OSRM with haversine fallback |
| `OSRM_HOST` env not mapping to `osrm_url` | ✅ **Fixed** — `PlatformSettings` aliases |

---

## Gaps remaining

| Gap | Priority |
|-----|----------|
| Bulk distance matrix API endpoint for merchant CSV | P2 |
| `route.optimized` event when Fleetbase orchestrator runs | P2 |
| Valhalla truck restrictions / avoid tolls | P3 (future) |
| Nearest driver via OSRM matrix (live map uses haversine) | P3 |
