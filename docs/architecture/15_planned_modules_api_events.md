# 15 — PLANNED modules, API, events

| Layer   | Change                                                                                                                                                                                                                                |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modules | add `agents/` (LangGraph graphs per department), `workflows/` (durable order/billing flows, DBOS, L18; also replaces all 22 sweeps, L20), `compliance/` (rule checks from 19/20), `whatsapp/` (Business Platform webhook + templates) |
| API     | `POST /v1/webhooks/whatsapp`; `GET/POST /v1/admin/approvals`; `GET /v1/admin/agents/runs`; `POST /v1/driver/temp-readings`; `GET /v1/orders/{id}/contract-of-carriage.pdf`; `GET /v1/driver/pay-statements`                           |
| Events  | add `approval.requested/decided`, `agent.run.*`, `order.temp_reading`, `driver.access_removed_notice`; emit or delete the 4 unused events                                                                                             |
| Infra   | `event_outbox` (same txn) → DBOS relay → Redpanda single node (Kafka API, L19), 12 `pc.*.v1` topics (see 12); Redis kept only for live GPS hash/GEO/Pub-Sub                                                                           |
| Remove  | 22 sweeps → workflow timers/consumers; dead modules (11)                                                                                                                                                                              |
