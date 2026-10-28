# 13 — PLANNED DFDs (Phase 1)

```mermaid
flowchart TB
  IN1[WhatsApp msg (P)] --> P1((1 Intake agent))
  IN2[Portal/API/Shopify] --> P1
  P1 --> GATE{Goods gate: TDG/UN3373/controlled/white-glove refused; cooler flag}
  GATE --> P2((2 Quote: cost model -> floor cost/0.50 -> public price))
  P2 --> SA{Service area: Toronto + 150 km}
  SA --> WF[[Durable order workflow (P)]]
  WF --> P3((3 Dispatch: courier vs box truck))
  P3 --> P4((4 Execution + GPS + temp log for cooler (P)))
  P4 --> P5((5 POD: photo/signature/OTP, e-signature record (ECA)))
  P5 --> P6((6 Invoice: HST, BN RT, credit-note approval > $500))
  P6 --> P7((7 Payment: Interac merchant / Stripe retail))
  WF -.events.-> RS[(Redis Streams)]
  RS -.-> P8((8 Notifications: CASL consent check before send))
  P4 --> TL[(temp_readings (P))]
```

Every step emits to `porterchain:events` from a transactional outbox (P). Timers (quote expiry, SLA, billing cycle) live in workflow timers, replacing sweeps.
