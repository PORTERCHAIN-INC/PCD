# 64 · Now vs Phase 0: data-flow diagrams L1 and L2

## L1: now (03)

```mermaid
flowchart TB
  P1((1 Order intake)) --> P2((2 Quote/pricing))
  P2 --> P3((3 Dispatch/routing))
  P3 --> P4((4 Driver execution + GPS))
  P4 --> P5((5 POD))
  P5 --> P6((6 Invoicing / credit notes / HST))
  P6 --> P7((7 Payments: Stripe + Interac, both for merchants))
  P1 & P3 & P4 & P5 & P6 & P7 -.Redis Stream XADD, not atomic.-> P8((8 Notifications: email, push, Twilio SMS))
  P9((9 CRM leads + AI lead agent)) --> P1
  P1 & P2 & P3 & P6 --> D1[(D1 Postgres public)]
  P4 --> D4[(D4 Redis GPS)]
  SW[[22 polling sweeps]] -.-> D1
```

## L1: Phase 0 target

```mermaid
flowchart TB
  P1((1 Order intake: web, apps, API, Shopify)) --> P2((2 Quote + margin band L2))
  P2 --> P3((3 Dispatch: routing adapter + VRP))
  P3 --> P4((4 Driver execution + GPS))
  P4 --> P5((5 POD, kept 6 y A01))
  P5 --> P6((6 Invoice, one status, one credit-note issuer))
  P6 --> P7a((7a Merchants: Interac matching))
  P6 --> P7b((7b Retail: Stripe))
  P1 & P3 & P4 & P5 & P6 & P7a & P7b -->|same txn| OB[(outbox)]
  OB -->|relay| K[[Redpanda pc.*.v1]]
  K --> P8((8 Notifications: email, push, TOTP))
  P9((9 CRM leads, rules only, no AI)) --> P1
  P1 & P2 & P3 & P6 --> D1[(D1 Postgres domain schemas)]
  P4 --> D4[(D4 Redis GPS)]
  DB[[DBOS schedules replace sweeps]] --> P6 & P8 & P9
```

## L2: 3 Dispatch/routing (now)

```mermaid
flowchart LR
  O[(orders/stops)] --> DP[day_plan.py] --> VRP[vrp.py]
  VRP --> OSRM[[OSRM]]
  VRP --> VAL[[Valhalla]]
  ADM[16 admin_engine modules] --> OSRM & VAL
  VRP --> R[(dispatch_routes, free-string status)]
  SW[[job_offer_sweep, stop_time_learning, delivery_sla sweeps]] -.-> R
```

## L2: 3 Dispatch/routing (Phase 0)

```mermaid
flowchart LR
  O[(ordering.orders/stops)] --> DP[day_plan] --> VRP[vrp, golden-tested]
  VRP --> RA{{routing adapter}}
  RA -->|1| VU[[Valhalla Ubuntu]]
  RA -->|2| VO[[Valhalla Oracle]]
  RA -->|3| HV[haversine x1.35, estimated]
  VRP --> R[(dispatch.routes, enum status)]
  R -->|outbox| K[[pc.dispatch.v1]]
  K --> UI[Dispatch pages: Today, Plan, Live, Exceptions, Fleet]
```

## L2: 7 Payments (now vs Phase 0)

```mermaid
flowchart LR
  subgraph NOW
    MI[merchant invoice] --> ST1[[Stripe]]
    MI --> IN1[[Interac notice IMAP]]
    RI[retail booking] --> ST2[[Stripe]]
  end
  subgraph P0
    MI2[merchant invoice] --> IN2[[Interac: bank-email match, interac_inbox schedule]]
    RI2[retail booking] --> ST3[[Stripe Checkout + webhook]]
  end
```

**L32 (29 Oct):** in 3 Dispatch/routing, the optimiser is VROOM on a Valhalla matrix (OSRM matrix only if it wins the benchmark), geometry from Valhalla truck costing, fallbacks Oracle then haversine ×1.35 flagged estimated (doc 60 §13).
