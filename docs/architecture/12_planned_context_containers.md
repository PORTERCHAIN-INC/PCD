# 12 — PLANNED Phase 1: context + containers

Source of decisions: strict plan canvas (L1–L24). **(P)** = not in code today. L18: DBOS + LangGraph. L19: Kafka API via single-node Redpanda + transactional outbox. L20: all 22 sweeps replaced in weeks 6–7. L24: schedule 14 + 8.

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
  API --> PG[(Postgres: app + event_outbox + LangGraph checkpointer + DBOS system tables)]
  PG -->|outbox relay - DBOS workflow (P)| KF[(Redpanda single node, Kafka API, KRaft-style no ZooKeeper (P, L19) - local 127.0.0.1:29092)]
  KF --> WRK2[Kafka consumers: DBOS workflows, agents, notifications (P)]
  API -->|live GPS only| RG[(Redis: gps:last hash + gps:geo + Pub/Sub porterchain:ops:live)]
  AG[Agent runtime - LangGraph (P, L14)] --> PG
  AG --> KF
  WF[Durable order/billing workflows + all former sweeps - DBOS (P, L18, L20)] --> PG
  API --> SDB[(SpiceDB)]
```

Constraints carried in: Toronto + 150 km (L1), 50 % margin floor (L2), cooler runs in, controlled substances / dangerous goods incl. UN3373 / white-glove out (L3), contractor drivers (L4), no COD (L10), Ontario/CRA rules (L11), six-check gate (L12), local rehearsal (L13). New code in SQLModel; Granian only if benchmarked; no new hand-rolled state columns, cron jobs or polling.

Kafka (L19), lean: one Redpanda node (Kafka protocol, no ZooKeeper, no JVM, built-in schema registry); fallback Apache Kafka single-node KRaft. Local ports 29092 (Kafka API), 28081 (schema registry), 29644 (admin), 28080 (console); never 5432/6379/50051. Topics: `pc.orders.v1`, `pc.quotes.v1`, `pc.billing.v1`, `pc.dispatch.v1`, `pc.drivers.v1`, `pc.cooler.temp.v1`, `pc.pod.v1`, `pc.whatsapp.inbound.v1`, `pc.notifications.out.v1`, `pc.approvals.v1`, `pc.agent.runs.v1`, `pc.dlq.v1`. At-least-once, consumers dedupe on event id; 7-day topic retention, Postgres stays system of record. Redis Streams `porterchain:events` and list queues are retired; Redis keeps only live GPS (see 10/GPS evidence below) and cache.

GPS evidence (verified in code, Oct 28 2026): live GPS does **not** use Redis Streams. Driver ping → `services/driver-platform/porterchain_driver/location.py` `LocationService.record_ping` → `platform/last_known.py` Lua CAS into hash `porterchain:gps:last:{driver_id}` + `GEOADD porterchain:gps:geo` (TTL 86,400 s) → `platform/last_known.py:179-181` `publish_ops_live` → Redis Pub/Sub `PUBLISH porterchain:ops:live` (`platform/ops_live.py:21,42`), tested by `tests/test_ops_live.py::test_gps_fix_publishes_driver_position`. Postgres `driver_location_pings` insert is off by default (`config.py:499`, `GPS_WRITE_PING_TABLE`). Planned: unchanged (Redis hash/GEO/Pub-Sub), not moved to Kafka.
