# Porterchain — Google Maps Usage Report

**Reference:** [masterrule.md](./masterrule.md) — routing belongs to Fleetbase + OSRM/Valhalla  
**Audit date:** 2026-06-30 · **Doc updated:** 2026-07-04  
**Canonical policy:** [GOOGLE_MAPS_USAGE.md](./GOOGLE_MAPS_USAGE.md)

---

## Policy (verified)

| Allowed | Forbidden |
| ------- | --------- |
| Address search / autocomplete | Commercial routing via Google |
| Geocoding | Turn-by-turn navigation in-app |
| Live map visualization | Route optimization |
| Distance preview (non-authoritative) | Dispatch routing decisions |
| Customer/merchant tracking map display | Replacing Fleetbase/OSRM/Valhalla for pricing |

**Authoritative routing:** Fleetbase (execution GPS) + OSRM (ETA legs) + Valhalla (optimized routes) via Porterchain API.

---

## Usage by application

### Website (`website/`)

| Use case | File | API | Status |
| -------- | ---- | --- | ------ |
| Address autocomplete | `components/maps/AddressAutocompleteInput.tsx` | Google Places via `@porterchain/maps` | ✅ |
| Maps provider | `components/maps/GoogleMapsProvider.tsx` | Re-export `@porterchain/maps/provider` | ✅ |
| Geocoding (quote) | `lib/quote/geocode.ts` | Geocode JSON (`GOOGLE_MAPS_SERVER_API_KEY`) | ✅ |
| Routing (quote preview) | `lib/quote/routing.ts` | **Valhalla/OSRM** — not Google | ✅ |
| Static embed | `components/corporate/sections/ContactMap.tsx` | Google Maps iframe | ✅ |
| Live tracking map | — | — | ❌ Text status on public track pages |

### Admin (`apps/admin/`)

| Use case | File | Status |
| -------- | ---- | ------ |
| Live operations map | `components/live-map/MapCanvas.tsx`, `LiveMapApp.tsx` | ✅ Visualization |
| Marker clustering | `MapCanvas.tsx` | ✅ `@googlemaps/markerclusterer` |
| Traffic / transit / bike layers | `MapCanvas.tsx` | ✅ |
| Heatmap, drawing, geofences | `MapCanvas.tsx` | ✅ Admin viz |
| Route measure (display) | `MapCanvas.tsx` | ✅ Polyline from API — display only |
| Dashboard / Order 360 embed | `DashboardEmbeddedMap.tsx`, `Order360EmbeddedMap.tsx` | ✅ |
| Directions API routing | — | ✅ Not used |

**Data source:** `LiveMapService` via Porterchain API — not Fleetbase direct.

### Merchant portal (`apps/merchant-portal/`)

| Use case | File | Status |
| -------- | ---- | ------ |
| Book autocomplete | `components/booking/BookDeliveryClient.tsx` | ✅ `@porterchain/maps` |
| Live tracking map | `components/tracking/TrackingMap.tsx`, `LiveTrackingView.tsx` | ✅ Viz + API polylines |
| Directions API routing | — | ✅ Not used |

### Customer app (`apps/customer/`)

| Use case | File | Status |
| -------- | ---- | ------ |
| Book autocomplete | `components/booking/CustomerBookDelivery.tsx` | ✅ `@porterchain/maps` |
| Signed-in tracking page | `app/track/[trackingNumber]/page.tsx` | ❌ Text-only — no map |
| Directions API routing | — | ✅ Not used |

### Driver portal (`apps/driver-portal/`)

| Use case | File | Status |
| -------- | ---- | ------ |
| Live navigation map | `components/navigation/DriverNavigationMap.tsx` | ✅ Google viz + API polylines |
| Maps provider | `app/layout.tsx` | ✅ `@porterchain/maps` |
| Directions API routing | — | ✅ Not used |

### Mobile (`apps/mobile-driver/`, `apps/mobile-customer/`)

| Use case | Package | Status |
| -------- | ------- | ------ |
| Enterprise map (nav / tracking) | `@porterchain/mobile-maps` | ✅ `EnterpriseMap` |
| Direct OSRM/Valhalla/Fleetbase calls | — | ✅ None — API only |

### Porterchain API (`apps/api/`)

| Use case | Status |
| -------- | ------ |
| Google Maps HTTP in business logic | ❌ None for routing/pricing |
| Admin diagnostics probe | ✅ `_probe_google_maps` in `diagnostics_service.py` |
| Settings health | ✅ Key presence in `AdminSettingsService` |

---

## Routing engine comparison

| Engine | Used where | Role |
| ------ | ---------- | ---- |
| **Fleetbase + Valhalla/OSRM** | Fleetbase Docker stack | Execution routing, dispatch |
| **Valhalla** | API + `website/lib/quote/routing.ts` | Optimized routes / quote preview |
| **OSRM** | API + website quote fallback | ETA legs / distance preview |
| **Google Directions** | — | **Not used** ✅ |
| **Google Distance Matrix** | — | **Not used** ✅ |

---

## Compliance matrix (July 2026)

| Requirement | Website | Admin | Merchant | Customer | Driver | Mobile |
| ----------- | ------- | ----- | -------- | -------- | ------ | ------ |
| Autocomplete | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Geocoding | ✅ server | ❌ | via Places | via Places | ❌ | ❌ |
| Live map viz | ❌ | ✅ | ✅ track | ❌ track | ✅ nav | ✅ |
| Distance preview | ✅ Valhalla | ❌ | via API | via API | via API | via API |
| Commercial routing | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Gaps (non-violations)

| Gap | Priority | Notes |
| --- | -------- | ----- |
| Customer web tracking map | P2 | Book has autocomplete; `/track/*` is text-only |
| Website public live map | P2 | Could add viz-only overlay |
| Admin CRM address geocode | P3 | Optional enhancement |
| Warehouse geofence persistence | P3 | Admin drawing exists; persistence TBD |

---

## API key management

| Key | Scope | Location |
| --- | ----- | -------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Client maps + Places | Next.js apps |
| `GOOGLE_MAPS_SERVER_API_KEY` | Server geocode | Website quote route |
| `GOOGLE_MAPS_BROWSER_API_KEY` | Legacy alias | `env/` templates |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | Mobile SDK | EAS / local `.env` |

Keys in `env/*.env.example` — never commit live keys.

---

## Conclusion

**No Google Maps routing violations found.** Google is used for autocomplete, geocoding, and map visualization. Execution routing remains Fleetbase + OSRM/Valhalla per locked architecture.
