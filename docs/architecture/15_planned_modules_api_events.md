# 15 — PLANNED modules, API, events

> **SUPERSEDED (kept for history, not deleted).** This pre-Phase-0 plan is replaced by 44 (API/data), 74 (integrations), 83 §1.3 (events). Start at [00_PHASE0_MASTER.md](00_PHASE0_MASTER.md); where this file disagrees, the master and its locked decisions (L1–L36) win.

| Layer   | Change                                                                                                                                                                                                                                                    |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modules | add `agents/` (PydanticAI agents per department, run as DBOS steps), `workflows/` (durable order/billing flows, DBOS, L18; also replaces all 22 sweeps, L20), `compliance/` (rule checks from 19/20), `whatsapp/` (Business Platform webhook + templates) |
| API     | `POST /v1/webhooks/whatsapp`; `GET/POST /v1/admin/approvals`; `GET /v1/admin/agents/runs`; `POST /v1/driver/temp-readings`; `GET /v1/orders/{id}/contract-of-carriage.pdf`; `GET /v1/driver/pay-statements`                                               |
| Events  | add `approval.requested/decided`, `agent.run.*`, `order.temp_reading`, `driver.access_removed_notice`; emit or delete the 4 unused events                                                                                                                 |
| Infra   | `event_outbox` (same txn) → DBOS relay → Redpanda single node (Kafka API, L19), 12 `pc.*.v1` topics (see 12); Redis kept only for live GPS hash/GEO/Pub-Sub                                                                                               |
| Remove  | 22 sweeps → workflow timers/consumers; dead modules (11)                                                                                                                                                                                                  |

## Promotions + public pricing (kept)

- Promotions: admin CRUD + expire, `POST /v1/quotes` applies a code after tiers and before the margin band check (warn-only); promo use emitted on `pc.quotes.v1`.
- Website calculator, `/rates`, `/quote` and merchant how-we-price read the live rate card through the public quote API (`rate_card_versions`); no prices hard-coded in `website/`.
