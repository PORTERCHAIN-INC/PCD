# Enterprise Map Module


**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `@porterchain/mobile-maps`  
**Path:** `shared/maps/`  
**Web counterpart:** `@porterchain/maps` in `packages/maps/`

Google Maps **rendering only**. All routing, tracking, and ETA data comes from **Porterchain API**.

> **Policy:** [GOOGLE_MAPS_USAGE.md](../../GOOGLE_MAPS_USAGE.md) · **Architecture audit:** [MAPS_ARCHITECTURE_AUDIT.md](../../MAPS_ARCHITECTURE_AUDIT.md)

---

## Architecture (masterrule.md)

```
Mobile EnterpriseMap
    ↓ renders
Google Maps (tiles, traffic overlay, markers, polylines)

Mobile ← Porterchain API ← Application Services
                              ├── Fleetbase adapter → live GPS / tracking
                              ├── OSRM → ETA legs + polylines
                              └── Valhalla → optimized route polylines
```

| Concern | Provider | Client |
| ------- | -------- | ------ |
| Map display | Google Maps | `MapView` + `PROVIDER_GOOGLE` |
| Live tracking | Fleetbase (via API) | Render `driver_location` |
| ETA | OSRM (via API) | Render `eta.polyline` |
| Optimized route | Valhalla (via API) | Render `optimized_route.polyline` |
| Geofences | API | `GeofenceLayer` / `Circle` |
| Traffic | Google Maps UI | `showsTraffic` |
| Heatmaps | Google Maps | `HeatmapLayer` from replay density |
| Route replay | API `replay[]` | Polyline + `RouteReplayControls` |

**The client never calls OSRM, Valhalla, or Fleetbase directly.**

---

## Consumers

| App | Entry |
| --- | ----- |
| `apps/mobile-driver/` | `NavigationScreen.tsx` — `driverSessionToMapSession` |
| `apps/mobile-customer/` | `LiveMapScreen.tsx` — `liveTrackingToMapSession` |

**Env:** `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` (see [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md)).

---

## Usage

```tsx
import {
  EnterpriseMap,
  driverSessionToMapSession,
  liveTrackingToMapSession,
  verifyRoutingEngines,
  MapsProvider,
} from "@porterchain/mobile-maps";

// Wrap app root (see AppProviders.tsx)
<MapsProvider apiKey={env.googleMapsApiKey}>
  <EnterpriseMap session={driverSessionToMapSession(navResponse)} height={400} showTraffic />
</MapsProvider>
```

---

## Entities

| Marker | Kind | Color |
| ------ | ---- | ----- |
| Driver | `driver` | Blue |
| Customer | `customer` | Green |
| Merchant | `merchant` | Violet |
| Warehouse | `warehouse` | Amber |
| Pickup | `pickup` | Green |
| Dropoff | `dropoff` | Red |

---

## Verification

```tsx
import { verifyRoutingEngines, MAP_ARCHITECTURE } from "@porterchain/mobile-maps";

const { valid, violations } = verifyRoutingEngines(session.routing_engines);
// Expect: gps=fleetbase, eta=osrm, optimized_route=valhalla, map_display=google_maps
```

Implementation: `shared/maps/src/verify.ts`.

---

## Polyline decoding

| Source | Precision |
| ------ | --------- |
| OSRM / Google encoded polyline | **5** |
| Valhalla shape | **6** |

Use `decodeRoutePolyline(polyline, source)` — never fetch routes on device.

---

## Module layout

```
shared/maps/src/
├── components/EnterpriseMap.tsx
├── components/RouteLayers.tsx
├── components/GeofenceLayer.tsx
├── components/HeatmapLayer.tsx
├── adapters.ts          # API response → MapSession
├── session.ts           # Types
├── geo.ts               # Polyline decode, fitRegion
└── verify.ts            # Architecture guardrails
```
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](../../masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
