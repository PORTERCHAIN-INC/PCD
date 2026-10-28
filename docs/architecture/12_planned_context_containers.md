# 12 — PLANNED Phase 1: context + containers

Source of decisions: strict plan canvas (L1–L17). **(P)** = not in code today. Open decisions are flagged **OPEN**.

```mermaid
flowchart LR
  RC([Retail customer]) -->|web + Stripe| PC
  MER([Merchant]) -->|portal, API, Shopify, WhatsApp(P)| PC
  DRV([Contractor driver]) -->|driver app| PC
  BT([Own box truck + cooler(P)]) -->|temp logger feed(P)| PC
  OPS([Staff: admin / super-admin]) --> PC
  PC{{Porterchain Inc. platform - evolved PCD (L8, L9)}}
  PC --> WAB[[WhatsApp Business Platform (P, L6)]]
  PC --> STR[[Stripe - retail only (L10)]]
  PC --> INT[[Interac - merchants (L10)]]
  PC --> LLM[[Model tiers T0-T3 (P)]]
```

```mermaid
flowchart TB
  CADDY[Caddy] --> API[FastAPI api]
  API --> PG[(Postgres: app + LangGraph checkpointer + DBOS? )]
  API --> RS[(Redis Streams porterchain:events)]
  RS --> WRK[worker consumers]
  AG[Agent runtime - LangGraph (P, L14)] --> PG
  AG --> RS
  WF[Durable order workflows - DBOS (P) OPEN] --> PG
  API --> SDB[(SpiceDB)]
  K[[Kafka - future option only, OPEN for Ravi]] -.-> RS
```

Constraints carried in: Toronto + 150 km (L1), 50 % margin floor (L2), cooler runs in, controlled substances / dangerous goods incl. UN3373 / white-glove out (L3), contractor drivers (L4), no COD (L10), Ontario/CRA rules (L11), six-check gate (L12), local rehearsal (L13). New code in SQLModel; Granian only if benchmarked; no new hand-rolled state columns, cron jobs or polling.
