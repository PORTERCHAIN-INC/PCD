# Porterchain — Maps Architecture Audit

**Reference:** [masterrule.md](./masterrule.md)  
**Audit date:** 2026-06-30 · **Doc updated:** 2026-07-04  
**Canonical usage:** [GOOGLE_MAPS_USAGE.md](./GOOGLE_MAPS_USAGE.md)

**Status key:** ✅ Correct · ⚠ Needs improvement · ❌ Missing

---

## Ownership model (locked)

| Layer | Owns | Must NOT own |
| ----- | ---- | ------------ |
| **Google Maps** | UI, autocomplete, geocoding, visualization | Routing, pricing, dispatch, business rules |
| **OSRM** | Distance, travel time, ETA legs (when configured) | Optimization UI, business logic |
| **Valhalla** | Optimized route paths, multi-stop sequencing | CRM, billing, execution GPS |
| **Fleetbase** | Dispatch execution, GPS, tracking, POD | Pricing, merchants, finance |
| **FastAPI** | Business rules, orchestration, adapter boundary | Direct map rendering |

---

## Portal compliance (July 2026)

### Website (`website/`)

| Check | Status |
| ----- | ------ |
| Google Maps autocomplete | ✅ `@porterchain/maps` |
| Server geocoding | ✅ `lib/quote/geocode.ts` |
| Marketing map embed | ✅ Contact iframe |
| Quote routing preview | ✅ Valhalla/OSRM — not Google |
| Calls Fleetbase | ✅ Never |

### Customer app (`apps/customer/`)

| Check | Status |
| ----- | ------ |
| Google Maps autocomplete (book) | ✅ `@porterchain/maps` |
| Tracking map | ❌ Text-only `/track/[trackingNumber]` |
| FastAPI only | ✅ |
| Stripe via API | ✅ |

### Merchant portal (`apps/merchant-portal/`)

| Check | Status |
| ----- | ------ |
| Book autocomplete | ✅ `@porterchain/maps` on `BookDeliveryClient` |
| Live tracking map | ✅ `TrackingMap.tsx` — viz + API polylines |
| FastAPI → booking → Fleetbase | ✅ Event-driven dispatch |
| Direct Fleetbase | ✅ Never |

### Admin portal (`apps/admin/`)

| Check | Status |
| ----- | ------ |
| Live map visualization | ✅ `MapCanvas.tsx` |
| Heatmap, traffic, geofences, drawing | ✅ |
| Fleetbase SSO only (not direct API) | ✅ |
| Data via FastAPI mirror | ✅ `LiveMapService` |

### Driver surfaces (`apps/driver-portal/`, `apps/mobile-driver/`)

| Check | Status |
| ----- | ------ |
| Google Maps UI | ✅ Driver portal `DriverNavigationMap`; mobile `EnterpriseMap` |
| Business logic in client | ✅ None — BFF → FastAPI |
| External Google Maps URL handoff | ✅ `driver-platform/navigation.py` — acceptable |
| Fleetbase via adapter | ✅ |

### Mobile customer (`apps/mobile-customer/`)

| Check | Status |
| ----- | ------ |
| Live tracking map | ✅ `LiveMapScreen` + `@porterchain/mobile-maps` |
| Direct engine calls | ✅ None |

---

## Shared packages

| Package | Path | Role |
| ------- | ---- | ---- |
| `@porterchain/maps` | `packages/maps/` | Web autocomplete, provider, types |
| `@porterchain/mobile-maps` | `shared/maps/` | React Native `EnterpriseMap`, session adapters |

Website re-exports preserve legacy import paths under `website/src/components/maps/`.

---

## Anti-patterns checked

| Violation | Found? |
| --------- | ------ |
| Google Directions for commercial routing | ❌ None |
| Google Distance Matrix for pricing | ❌ None |
| Frontend → OSRM/Valhalla for authoritative price | ⚠ Website quote preview only (documented) |
| Frontend → Fleetbase | ❌ None |
| Duplicate web autocomplete implementations | ✅ Consolidated in `@porterchain/maps` |
| Mobile client calling routing engines | ❌ None — `verifyRoutingEngines()` enforces contract |

---

## Recommended next steps (not implemented)

- Customer web app tracking map (Google viz + API tracking data)
- Website public live tracking map
- Persist admin warehouse geofence drawings

---

## Related

| Document | Purpose |
| -------- | ------- |
| [GOOGLE_MAPS_USAGE_REPORT.md](./GOOGLE_MAPS_USAGE_REPORT.md) | File-level audit |
| [shared/maps/MAP_MODULE.md](./shared/maps/MAP_MODULE.md) | Mobile map module |
| [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md) | Route Center (Group 19) |
