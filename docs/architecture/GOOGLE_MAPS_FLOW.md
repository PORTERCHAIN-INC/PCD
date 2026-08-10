# Google Maps Flow

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-08

**Source:** `packages/maps/`, `shared/maps/` (`@porterchain/mobile-maps`)  
**See also:** [GOOGLE_MAPS_USAGE.md](../../GOOGLE_MAPS_USAGE.md)

---

## Rule (masterrule.md)

Google Maps is used for **visualization and address autocomplete only**. Distance, ETA, and pricing use **OSRM/Valhalla** via `MapsService`. Route polylines on maps are **display-only** from Porterchain API data.

## Web Packages (`@porterchain/maps`)

| App             | Port    | Purpose                                         |
| --------------- | ------- | ----------------------------------------------- |
| Website         | `:3000` | Public **track** map embed only                 |
| Customer portal | `:3004` | Book delivery autocomplete (retail book SoT)    |
| Merchant portal | `:3001` | Book + tracking map viz                         |
| Admin           | `:3002` | Live map markers (`apps/admin/src/lib/maps.ts`) |
| Driver portal   | `:3003` | Navigation map chrome                           |

Package: `packages/maps/src/GoogleMapsProvider.tsx` wraps `@vis.gl/react-google-maps`.

Env: `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`

## Mobile (`@porterchain/mobile-maps`)

React Native maps in `shared/maps/` — `EnterpriseMap`, session adapters. Used by `apps/mobile-driver` and `apps/mobile-customer` for navigation/tracking visualization. **Not** used for pricing or dispatch routing.

## Server-Side geocode

Retail quote/book geocode is **not** on the marketing website (no `/api/quote`). Autocomplete/geocode for booking is customer/merchant portal + API (`MapsService` / Places).

## NOT Google

- `QuoteService` / `PricingService` → `MapsService.route_distance_meters()` (Valhalla primary, OSRM when engine=osrm)
- Fleetbase execution routing

## Diagram

```mermaid
flowchart TB
  subgraph Browser["Browser (Client-Side)"]
    PKG["@porterchain/maps<br/>packages/maps"]
    GMP["GoogleMapsProvider<br/>@vis.gl/react-google-maps"]
    AC["AddressAutocomplete"]
  end

  subgraph Mobile["React Native"]
    MM["@porterchain/mobile-maps<br/>shared/maps"]
    EM[EnterpriseMap]
  end

  subgraph Apps["Consumers"]
    WEB["website :3000 track only"]
    CUST[customer :3004 book]
    MERCH[merchant :3001]
    ADMIN[admin :3002 places/tiles]
    MDRV[mobile-driver]
  end

  subgraph NOT_USED["NOT used for routing/pricing in API"]
    NOTE["Distance/pricing uses Valhalla/OSRM<br/>via MapsService — not Google"]
  end

  WEB & CUST & MERCH & ADMIN --> PKG
  MDRV --> MM
  PKG --> GMP --> GAPI[Google Maps JavaScript API]
  MM --> EM --> GAPI
  CUST & MERCH --> AC
  AC --> GAPI
```

## PlantUML

See [plantuml/google_maps_flow.puml](./plantuml/google_maps_flow.puml)
---
