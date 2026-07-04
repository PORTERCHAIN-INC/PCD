# Valhalla Usage

**Date:** June 30, 2026 · **Default engine:** `ROUTING_ENGINE=valhalla`

---

## Responsibilities

| Function | Valhalla | Status |
|----------|----------|--------|
| Route optimization | Valhalla + Fleetbase orchestrator | ⚠️ Split ownership |
| Multi-stop optimization | Fleetbase orchestrator primarily | ⚠️ |
| Route sequencing | Fleetbase execution | ✅ |
| Commercial vehicle routing | Future | ❌ |
| Truck restrictions | Future | ❌ |
| Avoid tolls / ferries | Future | ❌ |
| Time-dependent routing | Future | ❌ |
| Merchant bulk route optimization | Fleetbase | ⚠️ Not in merchant portal UI |
| Pricing distance (API) | Valhalla primary | ✅ **Wired** |

---

## Infrastructure

| Component | Endpoint |
|-----------|----------|
| Docker `porterchain-valhalla` | `http://localhost:8002` |
| `VALHALLA_BASE_URL` | Host access |
| `VALHALLA_BASE_URI` | Docker internal (`valhalla:8002`) |

---

## Call sites

| Location | Role |
|----------|------|
| `website/src/lib/quote/routing.ts` | Preview when `ROUTING_ENGINE=valhalla` |
| `porterchain_services/maps/service.py` | API authoritative routing |
| `apps/api/services/routing.py` | Pricing bridge |
| Fleetbase stack | Shared Valhalla per `fleetbase.porterchain.override.yml` |

---

## Duplication check

| Duplicate Valhalla client | Found? |
|---------------------------|--------|
| In FastAPI routers | ❌ |
| In merchant frontend | ❌ |
| Third Python implementation | ❌ — only `MapsService` |

---

## Gaps

| Gap | Status |
|-----|--------|
| `route.optimized` event on orchestrator commit | ❌ Catalog only |
| VROOM / multi-stop in Porterchain API | ❌ Delegated to Fleetbase |
| Truck costing profile | ❌ Future |
