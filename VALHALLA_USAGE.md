# Valhalla usage

**Type:** CANONICAL  
**Last verified:** 2026-08-07

**API default:** `ROUTING_ENGINE=valhalla`  
Primary engine for pricing distance, optimized geometry, and matrix-style costing.  
Execution sequencing stays in **Fleetbase**.

Fallback: [OSRM_USAGE.md](./OSRM_USAGE.md).

---

## Responsibilities

| Function                              | Status                                       |
| ------------------------------------- | -------------------------------------------- |
| Pricing distance                      | ✅ `MapsService`                             |
| Optimized route geometry              | ✅ API + tracking                            |
| Multi-stop leg sum                    | ✅                                           |
| Dispatch suggestions / assign ranking | ✅ (Valhalla matrix via suggestions service) |
| Execution multi-stop sequencing       | Fleetbase                                    |
| Admin Route Center optimize UI        | **Removed** — use Fleetbase                  |

Google Maps never participates in routing.

---

## Infrastructure

| Component                                 | Endpoint                                                           |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Local `porterchain-valhalla`              | `http://127.0.0.1:8002` (GTA extract via `pnpm docker:up:routing`) |
| `VALHALLA_BASE_URL` / `VALHALLA_BASE_URI` | Host vs Docker-internal                                            |

Health: `http://localhost:8002/status` · see [DOCKER_SETUP.md](./DOCKER_SETUP.md).

---

## Call sites

| Location                                                    | Role                         |
| ----------------------------------------------------------- | ---------------------------- |
| `services/python/porterchain_services/maps/service.py`      | Authoritative client         |
| `apps/api/.../services/routing.py`                          | Pricing bridge               |
| `apps/api/.../admin_engine/dispatch_suggestions_service.py` | Ranked assign                |
| `apps/api/.../merchant_engine/tracking_service.py`          | Polylines                    |
| `services/driver-platform/.../navigation.py`                | Driver routes                |
| `website/src/lib/quote/routing.ts`                          | Preview when engine=valhalla |

---

## Related

- [docs/architecture/VALHALLA_FLOW.md](./docs/architecture/VALHALLA_FLOW.md)
- [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) (port 8002)
- [docs/ops/ORDERS_MODULE.md](./docs/ops/ORDERS_MODULE.md) (Control Tower uses suggestions, not Route Center)
