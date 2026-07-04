# Valhalla Flow

> **Source:** `services/python/porterchain_services/maps/service.py`, `integrations.yaml`

## Purpose

Valhalla is the **preferred routing engine** for distance/ETA when `routing_engine=valhalla`. Used for quote pricing and optimization path — **not** for Fleetbase dispatch execution.

## HTTP Call

```
POST {valhalla_url}/route
{
  "locations": [{"lat": ..., "lon": ...}, ...],
  "costing": "auto"
}
```

Response parsed: `trip.summary.length` (km → meters), `trip.summary.time` (seconds).

## Fallback

If Valhalla unreachable or `routing_engine != valhalla`, `MapsService` falls back to OSRM.

## Event Catalog

`route.optimized` exists in `DomainEventType` but is **not actively emitted** in current booking flow — reserved for future route optimization.

## Config

- `VALHALLA_BASE_URL` / `valhalla_url` — default `http://localhost:8002`
- Docker compose overlay in `infrastructure/docker/`

## Diagram

```mermaid
flowchart LR
  subgraph Callers["API Callers"]
    QS[QuoteService]
    PS[PricingService]
    MBS[MerchantBookingService]
  end

  subgraph MapsSvc["MapsService"]
    ENG{"routing_engine<br/>== valhalla?"}
    VR[_valhalla_route]
    RDM[route_distance_meters]
  end

  subgraph Valhalla["Valhalla :8002"]
    POST["POST /route<br/>locations + costing:auto"]
  end

  QS & PS & MBS --> RDM
  RDM --> ENG
  ENG -->|yes| VR
  VR --> POST
  ENG -->|no| OSRM[OSRM fallback]
```

## PlantUML

See [plantuml/valhalla_flow.puml](./plantuml/valhalla_flow.puml)
