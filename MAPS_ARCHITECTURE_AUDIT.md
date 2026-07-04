# Porterchain — Maps Architecture Audit

**Reference:** [masterrule.md](./masterrule.md)  
**Date:** June 30, 2026  
**Status key:** ✅ Correct · ⚠ Needs Improvement · ❌ Missing

---

## Ownership model (locked)

| Layer | Owns | Must NOT own |
|-------|------|--------------|
| **Google Maps** | UI, autocomplete, geocoding, visualization | Routing, pricing, dispatch, business rules |
| **OSRM** | Distance, travel time, ETA, matrix (when configured) | Optimization, UI, business logic |
| **Valhalla** | Route optimization path, multi-stop sequencing (via engine config) | CRM, billing, execution GPS |
| **Fleetbase** | Dispatch execution, GPS, tracking, POD, navigation | Pricing, merchants, finance, support |
| **FastAPI** | All business rules, orchestration, adapter boundary | Direct map rendering |

---

## Portal compliance

### Website (`website/`)

| Check | Status |
|-------|--------|
| Google Maps autocomplete | ✅ `AddressAutocompleteInput` via `@porterchain/maps` |
| Geocoding | ✅ `lib/quote/geocode.ts` (server) |
| Map rendering (marketing) | ✅ Contact embed iframe |
| Routing for quote preview | ✅ Valhalla/OSRM in `lib/quote/routing.ts` — not Google |
| Calls Fleetbase | ✅ Never |
| Calls FastAPI for booking | ✅ |

### Customer Portal (`apps/customer/` + website `/portal/customer`)

| Check | Status |
|-------|--------|
| Google Maps autocomplete | ❌ Missing |
| Tracking map | ❌ Links to website text track |
| FastAPI only | ✅ |
| Stripe via API | ✅ |

### Merchant Portal (`apps/merchant-portal/`)

| Check | Status |
|-------|--------|
| Google Maps autocomplete | ✅ **Added** — `@porterchain/maps` on book page |
| FastAPI → Pricing → Booking → Fleetbase | ✅ Event-driven dispatch |
| Direct Fleetbase | ✅ Never |

### Admin Portal (`apps/admin/`)

| Check | Status |
|-------|--------|
| Live map visualization | ✅ `MapCanvas.tsx` |
| Heatmap, traffic, geofences, drawing | ✅ |
| Fleetbase SSO only (not API) | ✅ |
| Data via FastAPI mirror | ✅ |

### Driver App (`apps/driver-portal/`, `apps/mobile-driver/`)

| Check | Status |
|-------|--------|
| Google Maps UI | ❌ Missing (external nav link in driver-platform only) |
| Business logic in app | ✅ None — BFF → FastAPI |
| Fleetbase via adapter | ✅ |

---

## Shared maps package

| Item | Status |
|------|--------|
| `@porterchain/maps` package | ✅ **Added** — single source for autocomplete + provider |
| Website re-exports | ✅ Thin shims preserve existing imports |
| Merchant portal wired | ✅ |

---

## Anti-patterns checked

| Violation | Found? |
|-----------|--------|
| Google Directions for commercial routing | ❌ None |
| Google Distance Matrix for pricing | ❌ None |
| Frontend → OSRM/Valhalla for authoritative price | ⚠ Website preview only (documented) |
| Frontend → Fleetbase | ❌ None |
| Duplicate autocomplete implementations | ✅ Resolved via `@porterchain/maps` |

---

## Recommended next steps (not implemented)

- Customer portal tracking map (Google viz + API tracking data)
- Driver portal route polyline map (viz only)
- Warehouse visualization (admin geofence persistence)
