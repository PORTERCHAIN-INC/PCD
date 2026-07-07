# Google Maps Usage

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Policy:** Visualization, autocomplete, and geocoding only — **never** commercial routing, pricing, or dispatch.

> **Flow diagrams:** [docs/architecture/GOOGLE_MAPS_FLOW.md](./docs/architecture/GOOGLE_MAPS_FLOW.md) · **Mobile module:** [shared/maps/MAP_MODULE.md](./shared/maps/MAP_MODULE.md) · **Historical audit:** [docs/archive/GOOGLE_MAPS_USAGE_REPORT.md](./docs/archive/GOOGLE_MAPS_USAGE_REPORT.md)

---

## Allowed uses (July 2026)

| Use                             | Website  | Customer     | Merchant    | Admin       | Driver portal | Mobile      |
| ------------------------------- | -------- | ------------ | ----------- | ----------- | ------------- | ----------- |
| Address autocomplete            | ✅       | ✅ book      | ✅ book     | ❌          | ❌            | ❌          |
| Place search                    | ✅       | ✅           | ✅          | ❌          | ❌            | ❌          |
| Server geocoding (quote)        | ✅       | ❌           | ❌          | ❌          | ❌            | ❌          |
| Map rendering (viz)             | ✅ embed | ❌           | ✅ track    | ✅ live map | ✅ nav        | ✅          |
| Live tracking map               | ❌       | ❌ text only | ✅          | ✅          | ✅            | ✅          |
| Heat maps / geofences / traffic | ❌       | ❌           | ⚠️ track    | ✅          | ⚠️ nav        | ⚠️          |
| Route polylines on map          | ❌       | ❌           | ✅ API data | ✅ API data | ✅ API data   | ✅ API data |

**Authoritative routing:** Fleetbase (execution) + OSRM/Valhalla (ETA/optimization via API). Google polylines are **display-only** from Porterchain API responses.

---

## Forbidden uses (verified absent)

| Use                                | Status      |
| ---------------------------------- | ----------- |
| Google Directions for dispatch     | ✅ Not used |
| Google Distance Matrix for pricing | ✅ Not used |
| Route optimization in Maps API     | ✅ Not used |
| Business logic in Maps API calls   | ✅ Not used |
| Webhooks from Google               | ✅ Not used |

---

## Shared packages

| Package                    | Path             | Consumers                                                |
| -------------------------- | ---------------- | -------------------------------------------------------- |
| `@porterchain/maps`        | `packages/maps/` | website, admin, merchant-portal, customer, driver-portal |
| `@porterchain/mobile-maps` | `shared/maps/`   | `apps/mobile-driver/`, `apps/mobile-customer/`           |

Web apps use `@vis.gl/react-google-maps` via `@porterchain/maps`. Mobile uses `react-native-maps` + `PROVIDER_GOOGLE` via `@porterchain/mobile-maps`.

---

## Key files

| App           | Files                                                                                                |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| Website       | `website/src/lib/quote/geocode.ts`, `website/src/components/maps/*`                                  |
| Admin         | `apps/admin/src/components/live-map/MapCanvas.tsx`                                                   |
| Merchant      | `apps/merchant-portal/src/components/booking/BookDeliveryClient.tsx`, `.../tracking/TrackingMap.tsx` |
| Customer      | `apps/customer/src/components/booking/CustomerBookDelivery.tsx`                                      |
| Driver portal | `apps/driver-portal/src/components/navigation/DriverNavigationMap.tsx`                               |
| Mobile        | `shared/maps/src/components/EnterpriseMap.tsx`                                                       |

---

## Environment variables

| Variable                          | Scope                                                       |
| --------------------------------- | ----------------------------------------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Next.js client maps + Places                                |
| `GOOGLE_MAPS_BROWSER_API_KEY`     | Legacy alias (loaded by some apps via `next.config`)        |
| `GOOGLE_MAPS_SERVER_API_KEY`      | Website server geocode (`website/src/lib/quote/geocode.ts`) |
| `GOOGLE_MAPS_API_KEY`             | API diagnostics / fallback geocode                          |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | React Native Maps SDK                                       |

Canonical list: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md).

---

## External navigation (acceptable)

`services/driver-platform/porterchain_driver/navigation.py` builds `https://www.google.com/maps/dir/?api=1&...` for **external turn-by-turn handoff** — not Porterchain routing. ✅ Allowed per masterrule.

---

## Related

| Document                                                                         | Purpose                  |
| -------------------------------------------------------------------------------- | ------------------------ |
| [docs/architecture/GOOGLE_MAPS_FLOW.md](./docs/architecture/GOOGLE_MAPS_FLOW.md) | Flow diagram (Group 27)  |
| [masterrule.md](./masterrule.md)                                                 | Locked routing ownership |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
