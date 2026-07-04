# Porterchain — API Flow Diagram

**Date:** June 30, 2026 · **Reference:** [masterrule.md](./masterrule.md) §7

---

## Canonical request flow

```mermaid
flowchart TB
  subgraph frontends [Frontends]
    W[Website]
    MP[Merchant Portal]
    CP[Customer Portal]
    AP[Admin Portal]
    DP[Driver Portal]
  end

  subgraph maps_ui [Google Maps - UI only]
    GM[Autocomplete / Live Map Viz]
  end

  subgraph api [FastAPI :8001 - Logistics Orchestrator]
    R[Routers]
    BE[booking_engine]
    ME[merchant_engine]
    AE[admin_engine]
    PE[pricing_engine]
    BLE[billing_engine]
    NE[notification_engine]
    FE[fleetbase_engine]
    DE[driver_engine]
  end

  subgraph data [Persistence]
    REPO[Repositories]
    DB[(Porterchain DB)]
  end

  subgraph async [Async]
    EB[Event Bus]
    WK[Worker]
  end

  subgraph routing [Routing Engines]
    VAL[Valhalla]
    OSRM[OSRM]
  end

  subgraph adapter [Adapter]
    FA[Fleetbase Adapter]
  end

  FB[(Fleetbase)]
  ST[Stripe]

  W --> GM
  MP --> GM
  AP --> GM
  GM -.->|no business calls| W
  W & MP & CP & AP & DP --> R
  R --> BE & ME & AE & DE
  BE & ME --> PE
  BE --> BLE
  BE & AE --> NE
  BE & ME & AE & FE --> REPO --> DB
  PE -->|resolve_route_distance| VAL & OSRM
  BE & ME & FE --> EB --> WK
  FE --> FA --> FB
  BLE --> ST
```

---

## Merchant booking flow

```
Merchant UI (Google autocomplete)
  → POST /v1/merchant/bookings
  → MerchantBookingService
  → resolve_route_distance() → Valhalla/OSRM
  → pricing_engine.calculate_merchant()
  → Order created
  → transition_to_dispatch_ready()
  → order.dispatch_requested + order.dispatch_ready
  → Event bus → BookingSyncService → FleetbaseAdapter → Fleetbase
```

---

## Retail customer flow

```
Website (Google autocomplete + quote preview Valhalla/OSRM)
  → POST /v1/quotes (server revalidates distance)
  → Booking draft → Stripe Checkout
  → POST /webhooks/stripe
  → BookingConfirmationService → order.dispatch_ready
  → Fleetbase sync (event-driven)
  → GET /v1/orders/{tracking}/tracking (adapter read)
```

---

## Admin live map flow

```
Admin UI (Google Maps viz)
  → WS /v1/admin/operations/live-map/ws
  → LiveMapService.snapshot() — Porterchain DB mirror
  → Never Fleetbase HTTP
```

---

## Driver flow

```
Driver UI
  → BFF /api/driver → /driver-api/v1/*
  → DriverAuthService / StopsService / DriverFleetbaseBridge
  → FleetbaseAdapter (GPS, POD) — execution only
  → order_transitions → Event bus
```

---

## Anti-shortcut verification

| Shortcut                             | Allowed?                     |
| ------------------------------------ | ---------------------------- |
| Frontend → Fleetbase                 | ❌                           |
| Frontend → Valhalla/OSRM for payment | ❌ (preview only on website) |
| Router → Fleetbase HTTP              | ❌                           |
| Service → Fleetbase without adapter  | ❌                           |
| Google Maps → pricing                | ❌                           |
