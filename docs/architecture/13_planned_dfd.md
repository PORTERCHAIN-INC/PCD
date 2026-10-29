# 13 — PLANNED DFDs (Phase 1)

> **SUPERSEDED (kept for history, not deleted).** This pre-Phase-0 plan is replaced by 64 (Phase 0 DFDs), 81 (order lifecycle). Start at [00_PHASE0_MASTER.md](00_PHASE0_MASTER.md); where this file disagrees, the master and its locked decisions (L1–L36) win.

```mermaid
flowchart TB
  IN1[WhatsApp msg (P)] --> P1((1 Intake agent))
  IN2[Portal/API/Shopify] --> P1
  P1 --> GATE{Goods gate: TDG/UN3373/white-glove refused; controlled only via pharmacy profile D-70-4; cooler flag}
  GATE --> P2((2 Quote: cost model -> margin band green/yellow/red, never blocks -> public price))
  P2 --> SA{Service area: Toronto + 150 km}
  SA --> WF[[Durable order workflow (P)]]
  WF --> P3((3 Dispatch: courier vs box truck))
  P3 --> P4((4 Execution + GPS + temp log for cooler (P)))
  P4 --> P5((5 POD: photo/signature/OTP, e-signature record (ECA)))
  P5 --> P6((6 Invoice: HST, BN RT, credit-note approval > $500))
  P6 --> P7((7 Payment: Interac merchant / Stripe retail))
  WF -.outbox events.-> RS[(Kafka API - Redpanda)]
  RS -.-> P8((8 Notifications: CASL consent check before send))
  P4 --> TL[(temp_readings (P))]
```

Every step emits to `porterchain:events` from a transactional outbox (P). Timers (quote expiry, SLA, billing cycle) live in workflow timers, replacing sweeps.
