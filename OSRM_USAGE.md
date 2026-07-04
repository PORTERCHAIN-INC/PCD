# OSRM Usage

**Date:** June 30, 2026

---

## Responsibilities

| Function                      | Owner | Status                                |
| ----------------------------- | ----- | ------------------------------------- |
| Distance calculation          | OSRM  | ✅                                    |
| Travel time                   | OSRM  | ✅                                    |
| ETA estimation                | OSRM  | ✅                                    |
| Matrix calculations           | OSRM  | ⚠️ Not exposed in Porterchain API yet |
| Nearest driver                | OSRM  | ❌ Live map uses haversine            |
| Pricing engine distance input | OSRM  | ✅ Fallback via `MapsService`         |
| Bulk distance matrix          | OSRM  | ❌ Not implemented                    |

---

## Call sites

| Location                               | Purpose                    | Direct?                |
| -------------------------------------- | -------------------------- | ---------------------- |
| `website/src/lib/quote/routing.ts`     | Quote preview fallback     | Server-side Next route |
| `porterchain_services/maps/service.py` | Authoritative API distance | Python httpx           |
| Fleetbase Docker `OSRM_HOST`           | Execution routing          | Fleetbase internal     |
| `fleetbase-adapter/routes`             | Distance-and-time read     | Via Fleetbase API      |

---

## Configuration

| Env var     | Maps to                        |
| ----------- | ------------------------------ |
| `OSRM_HOST` | `PlatformSettings.osrm_url` ✅ |
| `OSRM_URL`  | `PlatformSettings.osrm_url` ✅ |

Default: `https://router.project-osrm.org` (public router for dev).

---

## Duplication

| Issue                                   | Status                         |
| --------------------------------------- | ------------------------------ |
| Second OSRM client in API routers       | ❌ None — single `MapsService` |
| Frontend authoritative pricing via OSRM | ❌ None                        |

---

## Status summary

✅ Correct for distance/ETA fallback  
⚠ Matrix and nearest-driver not wired  
❌ Bulk merchant matrix endpoint missing
