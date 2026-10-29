# 21 — NOW vs PLANNED delta + migration order

| Layer       | NOW (as-built, files 01–10)                   | PLANNED (12–20)                                             | Step  |
| ----------- | --------------------------------------------- | ----------------------------------------------------------- | ----- |
| Context     | portals, Shopify, Stripe, Interac             | + WhatsApp, cooler logger, agents                           | 6     |
| Containers  | api, worker, Redis lists + Streams, no outbox | outbox → Kafka (Redpanda); LangGraph agents; DBOS workflows | 2, 5  |
| Data        | 04 ER; POD 365 d; no BOL/temp/approvals       | 14 additions; POD ≥ 6 y                                     | 1, 3  |
| Modules/API | 06 drift (20 handlers not in snapshot)        | regenerate OpenAPI; new endpoints (15)                      | 2     |
| Interface   | 07, 20 redirect stubs                         | 16 IA, approvals inbox                                      | 7     |
| States      | free-string offer/route status                | enums + maps (17)                                           | 3     |
| Authz       | staff roles only                              | agent identities + approve_* (17)                           | 5     |
| Async       | 22 sweeps, 4 unused events                    | workflow timers; outbox                                     | 4     |
| Compliance  | 19 table                                      | all B                                                       | 1 → 8 |

Order (each step passes the six-check gate, `NEW_ADDITION_GATE.md`, and local rehearsal L13):

1. **Legal blockers first:** POD retention ≥ 6 y (A01), DG hard refuse (L3), BN RT validation (A07), claims deadlines, declared-value disclosure.
2. Regenerate OpenAPI snapshot; local Redpanda (29092) + DBOS (week 1); `event_outbox` + relay to Kafka topics (week 4).
3. Enums/transition maps; `temp_readings`, `contract_of_carriage` (BOL), `vehicle_compliance_docs`, `driver_pay_statements`, `driver_access_notices`.
4. Replace all 22 sweeps with DBOS scheduled workflows / Kafka consumers in weeks 6–7 (L18, L20); delete the worker polling loop.
5. Agent identities in SpiceDB; approvals table; LangGraph runtime at autonomy rung 0.
6. WhatsApp webhook + CASL consent gate.
7. Admin/super-admin IA reorg; delete redirect stubs.
8. Box truck go-live only after CVOR + cargo insurance + BOL done; DPWRA features before contractor scale-up.

Schedule (L24): 14 build + 8 proven weeks, a 2-week slip from 12 + 8 caused by Kafka (L19, about 1 week: broker, outbox relay, topics, consumers, week-13 hardening) and moving all 22 sweeps (L20, about 1 week). All 11 S1 fixes by week 6 (L21); sweeps weeks 6–7; Kafka hardening week 13; rehearsal + pilot week 14; proven window weeks 15–22. Box truck price from Ravi by week 3; truck runs only after BOL, CVOR and cargo insurance (L23).
