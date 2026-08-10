# Google Maps usage

**Type:** CANONICAL  
**Last verified:** 2026-08-07

**Policy:** Places autocomplete, map tiles, and optional server geocode only.  
**Never** use Google for commercial routing, pricing distance, dispatch ETA, matrix, or optimization.

See also: [OSRM_USAGE.md](./OSRM_USAGE.md) · [VALHALLA_USAGE.md](./VALHALLA_USAGE.md) · [docs/architecture/GOOGLE_MAPS_FLOW.md](./docs/architecture/GOOGLE_MAPS_FLOW.md)

---

## Allowed

| Use                                 | Surfaces                                                    |
| ----------------------------------- | ----------------------------------------------------------- |
| Address autocomplete / Places       | Website, customer, merchant booking                         |
| Map tile rendering                  | Website embeds, merchant tracking, driver nav, mobile       |
| Server geocode fallback             | Website quote / API diagnostics when Nominatim insufficient |
| External Google Maps directions URL | Driver handoff only (`navigation.py`) — not PC routing      |

## Forbidden (verified)

Google Directions, Distance Matrix, or optimization for pricing/dispatch — **not used**.

---

## Key files

| App           | Path                                                                |
| ------------- | ------------------------------------------------------------------- |
| Website       | `website/src/lib/quote/geocode.ts`, `website/src/components/maps/*` |
| Merchant      | `apps/merchant-portal/.../TrackingMap.tsx`, booking Places          |
| Driver portal | `apps/driver-portal/.../DriverNavigationMap.tsx`                    |
| Mobile        | `shared/maps` (`@porterchain/mobile-maps`)                          |
| Shared web    | `packages/maps` (`@porterchain/maps`)                               |

Admin Control Tower does **not** host a live-map Google canvas — execution maps are Fleetbase console / Order 360 adapter-fed views.

---

## Environment

| Variable                          | Scope                      |
| --------------------------------- | -------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Next.js client             |
| `GOOGLE_MAPS_SERVER_API_KEY`      | Website server geocode     |
| `GOOGLE_MAPS_API_KEY`             | API diagnostics / fallback |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | React Native Maps          |

Canonical list: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md).
