# Porterchain — Google Maps Usage Report

**Reference:** [masterrule.md](./masterrule.md) — routing belongs to Fleetbase  
**Audit date:** June 30, 2026

---

## Policy (verified intent)

| Allowed | Forbidden |
|---------|-----------|
| Address search / autocomplete | Commercial routing |
| Geocoding | Turn-by-turn navigation |
| Live map visualization | Route optimization |
| Distance preview (non-authoritative) | Dispatch routing decisions |
| Customer tracking map display | Replacing Fleetbase/OSRM/Valhalla for pricing |

**Authoritative routing:** Fleetbase (execution) + Valhalla/OSRM (website quote preview only).

---

## Usage by application

### Website (`website/`)

| Use case | File | API | Status |
|----------|------|-----|--------|
| Address autocomplete | `components/maps/AddressAutocompleteInput.tsx` | Google Places (client) | ✅ Allowed |
| Maps provider | `components/maps/GoogleMapsProvider.tsx` | `@vis.gl/react-google-maps` | ✅ |
| Geocoding (quote) | `lib/quote/geocode.ts` | `maps.googleapis.com/maps/api/geocode/json` | ✅ Allowed |
| Routing (quote preview) | `lib/quote/routing.ts` | **Valhalla/OSRM** — not Google | ✅ Correct |
| Static embed | `components/corporate/sections/ContactMap.tsx` | Google Maps iframe | ✅ Allowed |
| Live tracking map | — | — | ❌ Missing (text status only) |

**Env:** `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, server `GOOGLE_MAPS_SERVER_KEY` (geocode)

### Admin (`apps/admin/`)

| Use case | File | API | Status |
|----------|------|-----|--------|
| Live operations map | `components/live-map/MapCanvas.tsx`, `LiveMapApp.tsx` | Google Maps JS | ✅ Visualization |
| Marker clustering | `MapCanvas.tsx` | `@googlemaps/markerclusterer` | ✅ |
| Traffic / transit / bike layers | `MapCanvas.tsx` | Google Maps layers | ✅ Allowed |
| Heatmap | `MapCanvas.tsx` | Google visualization | ✅ |
| Drawing tools / geofences | `MapCanvas.tsx` | Google drawing | ✅ Admin viz |
| Route measure (display) | `MapCanvas.tsx` | Polyline from API data | ✅ Display only |
| Dashboard embed | `DashboardEmbeddedMap.tsx` | Google Maps | ✅ |
| Order 360 embed | `Order360EmbeddedMap.tsx` | Google Maps | ✅ |
| Address autocomplete | — | — | ❌ Not implemented |
| Directions API routing | — | — | ✅ Not used (correct) |

**Env:** `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`  
**Data source:** `LiveMapService` snapshot via Porterchain API — **not** Fleetbase direct

### Merchant portal (`apps/merchant-portal/`)

| Use case | Status |
|----------|--------|
| All Google Maps | ❌ Missing — plain text address fields |

### Driver portal (`apps/driver-portal/`)

| Use case | Status |
|----------|--------|
| All Google Maps | ❌ Missing — `route_polyline` in API unused |

### Customer app (`apps/customer/`)

| Use case | Status |
|----------|--------|
| All Google Maps | ❌ Missing |

### Porterchain API (`apps/api/`)

| Use case | Status |
|----------|--------|
| Google Maps HTTP calls | ❌ None |
| Settings health check | ✅ Key presence check in `AdminSettingsService` |

---

## Routing engine comparison

| Engine | Used where | Role |
|--------|------------|------|
| **Fleetbase + Valhalla/OSRM** | Fleetbase Docker stack | Execution routing, dispatch |
| **Valhalla** | `website/lib/quote/routing.ts` | Quote distance preview |
| **OSRM** | `website/lib/quote/routing.ts` | Fallback distance preview |
| **Google Directions** | — | **Not used** ✅ |
| **Google Distance Matrix** | — | **Not used** ✅ |

---

## Compliance matrix

| Requirement | Website | Admin | Merchant | Driver | API |
|-------------|---------|-------|----------|--------|-----|
| Autocomplete | ✅ | ❌ | ❌ | ❌ | N/A |
| Geocoding | ✅ | ❌ | ❌ | ❌ | N/A |
| Live map viz | ❌ | ✅ | ❌ | ❌ | N/A |
| Distance preview | ✅ (Valhalla) | ❌ | ❌ | ❌ | N/A |
| Customer tracking map | ❌ | N/A | N/A | N/A | N/A |
| Admin visualization | N/A | ✅ | N/A | N/A | N/A |
| Commercial routing | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Gaps (non-violations)

| Gap | Priority | Notes |
|-----|----------|-------|
| Merchant book autocomplete | P2 | Integration gap, not policy violation |
| Customer/public tracking map | P2 | Could use Google viz + API tracking data |
| Driver navigation map | P2 | Should use Fleetbase nav or viz-only overlay |
| Admin address geocode on CRM | P3 | Optional enhancement |

---

## API key management

| Key | Scope | Location |
|-----|-------|----------|
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Client-side maps + Places | Frontends |
| `GOOGLE_MAPS_SERVER_KEY` | Server geocode | `website` quote API route |
| Restrictions | HTTP referrer / IP | Google Cloud Console |

Keys referenced in `env/.env.example` — never committed to repo.

---

## Conclusion

**No Google Maps routing violations found.** Google is used correctly for autocomplete, geocoding, and administrative visualization. All execution routing remains with Fleetbase and Valhalla/OSRM per locked architecture.
