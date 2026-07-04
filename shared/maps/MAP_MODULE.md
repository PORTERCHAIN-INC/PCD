# Enterprise Map Module

`@porterchain/mobile-maps` — Google Maps rendering only. All routing, tracking, and ETA data comes from **Porterchain API**.

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

| Concern         | Provider            | Client                            |
| --------------- | ------------------- | --------------------------------- |
| Map display     | Google Maps         | `MapView` + `PROVIDER_GOOGLE`     |
| Live tracking   | Fleetbase (via API) | Render `driver_location`          |
| ETA             | OSRM (via API)      | Render `eta.polyline`             |
| Optimized route | Valhalla (via API)  | Render `optimized_route.polyline` |
| Geofences       | API                 | `Circle` components               |
| Traffic         | Google Maps UI      | `showsTraffic`                    |
| Heatmaps        | Google Maps         | `Heatmap` from replay density     |
| Route replay    | API `replay[]`      | Polyline + scrubber               |

**The client never calls OSRM, Valhalla, or Fleetbase directly.**

## Usage

```tsx
import {
  EnterpriseMap,
  driverSessionToMapSession,
  liveTrackingToMapSession,
  verifyRoutingEngines,
} from "@porterchain/mobile-maps";

const mapSession = driverSessionToMapSession(navigationApiResponse);

<EnterpriseMap
  session={mapSession}
  height={400}
  showTraffic
  showGeofences
  showHeatmap
  showReplayControls
/>;
```

## Entities

| Marker    | Kind        | Color  |
| --------- | ----------- | ------ |
| Driver    | `driver`    | Blue   |
| Customer  | `customer`  | Green  |
| Merchant  | `merchant`  | Violet |
| Warehouse | `warehouse` | Amber  |
| Pickup    | `pickup`    | Green  |
| Dropoff   | `dropoff`   | Red    |

## Verification

```tsx
import { verifyRoutingEngines, MAP_ARCHITECTURE } from "@porterchain/mobile-maps";

const { valid, violations } = verifyRoutingEngines(session.routing_engines);
// Expect: gps=fleetbase, eta=osrm, optimized_route=valhalla, map_display=google_maps
```

## Polyline decoding

- OSRM / Google encoded polyline → precision **5**
- Valhalla shape → precision **6**

Use `decodeRoutePolyline(polyline, source)` — never fetch routes on device.
