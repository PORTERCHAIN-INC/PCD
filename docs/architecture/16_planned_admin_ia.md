# 16 — PLANNED admin + super-admin information architecture

```mermaid
flowchart LR
  subgraph ADMIN[Admin - daily ops]
    T[Today: queue, exceptions, approvals inbox]
    D[Dispatch: plan, live, fleet, box truck, cooler runs]
    O[Orders + Claims]
    A[Accounts: merchants, customers, duplicates]
    S[Sales: leads, WhatsApp inbox, pipeline]
    F[Finance: cash, invoices, credit notes, payments, driver pay, GST/HST, reports]
    SP[Support: tickets]
  end
  subgraph SUPER[Super-admin - platform]
    SY[System: health, services, diagnostics]
    AG[Agents: runs, autonomy ladder, kill switch]
    CP[Compliance: retention, privacy requests, breach log, consent, CVOR/insurance expiry]
    ST[Settings: pricing floors, spend caps, approval caps, tax registration]
    US[Staff + roles (SpiceDB)]
    IN[Insights: investor/visitor metrics]
  end
```

Rules: one nav source generated from `schema.zed` permissions; every page appears in exactly one group; no redirect stubs (301 at Caddy); finance sub-pages promoted into the group; approvals are one inbox for the six human cases (L15–L17).
