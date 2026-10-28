# 18 — PLANNED agents and autonomy ladder (L7, L14–L17)

```mermaid
flowchart TB
  G[Goal agent] --> O[Orchestration agent] --> TK[Task agent]
  TK --> D1[Sales/CRM] & D2[Dispatch] & D3[Cooler/box truck] & D4[Billing/HST] & D5[Support/WhatsApp] & D6[Driver mgmt] & D7[Platform]
  D1 & D2 & D3 & D4 & D5 & D6 & D7 --> CK[(LangGraph Postgres checkpointer)]
  D1 & D2 & D3 & D4 & D5 & D6 & D7 -.-> APR{{6 human approval cases}}
```

21 department agents under the 3 core agents; names per plan canvas table. Model tiers T0–T3. Promotion up the autonomy ladder requires ≥ 99 % agreement with human decisions over 500 jobs; demotion and kill switch are super-admin. Every agent action is logged (`ai_usage_logs` exists today; `agent_runs` planned).
