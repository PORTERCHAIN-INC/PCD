# Google Maps Flow

> **Source:** `packages/maps/`, `website/src/lib/quote/geocode.ts`, `apps/admin/src/lib/maps.ts`

## Rule (masterrule.md)

Google Maps is used for **visualization and address autocomplete only**. Distance, ETA, and pricing use **OSRM/Valhalla** via `MapsService`.

## Client-Side Usage

| App | File | Purpose |
|-----|------|---------|
| Website | `website/src/app/[locale]/book/` | Address autocomplete via `@porterchain/maps` |
| Merchant | `apps/merchant-portal/src/app/(portal)/book/` | Same shared package |
| Admin | `apps/admin/src/lib/maps.ts`, live-map pages | Map markers, driver positions |

Package: `packages/maps/src/GoogleMapsProvider.tsx` wraps `@vis.gl/react-google-maps`.

Env: `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`

## Server-Side (Website Quote Preview Only)

`website/src/app/api/quote/route.ts` → `geocode.ts` calls `maps.googleapis.com` for address → lat/lng. This is **estimation preview**; server re-validates at `POST /v1/quotes`.

## NOT Google

- `QuoteService` / `PricingService` → `MapsService.route_distance_meters()` (OSRM/Valhalla)
- Fleetbase execution routing

## Diagram

```mermaid
flowchart TB
  subgraph Browser["Browser (Client-Side)"]
    PKG["@porterchain/maps<br/>packages/maps"]
    GMP["GoogleMapsProvider<br/>@vis.gl/react-google-maps"]
    AC["AddressAutocomplete"]
  end

  subgraph Apps["Consumers"]
    WEB[website book page]
    MERCH[merchant-portal book]
    ADMIN[admin live-map<br/>map visualization]
  end

  subgraph ServerPreview["Server Preview Only"]
    WQR["website POST /api/quote<br/>geocode.ts → maps.googleapis.com"]
  end

  subgraph NOT_USED["NOT used for routing/pricing in API"]
    NOTE["Distance/pricing uses OSRM/Valhalla<br/>via MapsService — not Google"]
  end

  WEB & MERCH & ADMIN --> PKG
  PKG --> GMP --> GAPI[Google Maps JavaScript API]
  PKG --> AC
  WEB --> WQR
  WQR --> GAPI
```

## PlantUML

See [plantuml/google_maps_flow.puml](./plantuml/google_maps_flow.puml)
