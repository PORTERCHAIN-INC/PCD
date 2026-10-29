# 14 — PLANNED ER additions (Phase 1)

```mermaid
erDiagram
  orders ||--o{ temp_readings : "cooler run"
  orders ||--o{ contract_of_carriage : "BOL (O.Reg 643/05 s.4)"
  orders ||--o{ approvals : "gated actions"
  agent_runs ||--o{ approvals : requests
  agent_runs ||--o{ agent_steps : has
  whatsapp_threads ||--o{ whatsapp_messages : has
  whatsapp_threads }o--|| crm_leads : links
  consent_records }o--|| crm_contacts : "CASL proof"
  drivers ||--o{ driver_pay_statements : "DPWRA s.7(5)"
  drivers ||--o{ driver_access_notices : "DPWRA s.11"
  vehicles ||--o{ vehicle_compliance_docs : "CVOR, insurance"
  event_outbox { uuid id PK; text type; jsonb payload; timestamptz relayed_at }
  temp_readings { uuid id PK; uuid order_id FK; numeric celsius; timestamptz at; text source }
  approvals { uuid id PK; text case_type; text status; uuid requested_by_run FK; text decided_by }
  agent_runs { uuid id PK; text agent; text tier; text thread_id; text status }
```

Status columns above must be enums with transition maps (rule: no hand-rolled state). `consent_records` may reuse `collaboration_engine/lead_consent.py` storage (U-09).

## Promotions (kept)

`promotions` (as-built `admin_models.py:194`) gains `max_uses`, `uses`, `merchant_scope`, `stackable`, `rate_card_version_id`; `booking_drafts.promo_code` and quotes reference `promotions.code`. Every promo is scored by the margin band (L2 amended; warns, never blocks).
