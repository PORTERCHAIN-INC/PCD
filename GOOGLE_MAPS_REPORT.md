# Google Maps Usage

**Date:** June 30, 2026 · **Policy:** Visualization + geocoding only — never commercial routing.

---

## Allowed uses (verified)

| Use | Website | Customer | Merchant | Admin | Driver |
|-----|---------|----------|----------|-------|--------|
| Address autocomplete | ✅ | ❌ | ✅ | ❌ | ❌ |
| Place search | ✅ | ❌ | ✅ | ❌ | ❌ |
| Geocoding | ✅ server | ❌ | via Places | ❌ | ❌ |
| Reverse geocoding | ⚠️ via Places | ❌ | via Places | ❌ | ❌ |
| Map rendering | ✅ embed | ❌ | ❌ | ✅ | ❌ |
| Live map visualization | ❌ | ❌ | ❌ | ✅ | ❌ |
| Heat maps | ❌ | ❌ | ❌ | ✅ | ❌ |
| Geofences / polygon drawing | ❌ | ❌ | ❌ | ✅ | ❌ |
| Traffic layer | ❌ | ❌ | ❌ | ✅ | ❌ |
| Customer tracking map | ❌ | ❌ | ❌ | ⚠️ order embed | ❌ |
| Merchant location viz | ❌ | ❌ | ❌ | ✅ markers | ❌ |
| Driver / vehicle viz | ❌ | ❌ | ❌ | ✅ live map | ❌ |
| Warehouse viz | ❌ | ❌ | ❌ | ⚠️ drawing only | ❌ |

---

## Forbidden uses (verified absent)

| Use | Status |
|-----|--------|
| Commercial route optimization | ✅ Not used |
| Pricing calculations | ✅ Not used |
| Dispatch logic | ✅ Not used |
| Business logic in Maps API calls | ✅ Not used |
| Webhooks from Google | ✅ Not used |

---

## Files

| App | Key files |
|-----|-----------|
| Shared | `packages/maps/src/*` |
| Website | `website/src/lib/quote/geocode.ts`, `website/src/lib/maps.ts` |
| Merchant | `apps/merchant-portal/.../book/page.tsx` |
| Admin | `apps/admin/src/components/live-map/MapCanvas.tsx` |

---

## Environment

| Variable | Scope |
|----------|-------|
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Client maps + Places |
| `GOOGLE_MAPS_SERVER_API_KEY` | Website server geocode |

---

## External navigation (driver)

`services/driver-platform/porterchain_driver/navigation.py` opens `google.com/maps/dir` for turn-by-turn — **external app handoff**, not Porterchain routing. ✅ Acceptable.
