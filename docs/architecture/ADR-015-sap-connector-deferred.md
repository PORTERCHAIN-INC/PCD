# ADR-015 — SAP connector deferred (Phase 2+)

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-08  
**Checklist:** §7.2.6 · Appendix H DD enterprise ERP  
**Related:** [ADR-010-phase2-strategies.md](./ADR-010-phase2-strategies.md)

---

## Context

Enterprise diligence asks for SAP S/4HANA and NetSuite connector roadmaps. Phase 1 ships **merchant API + CSV + webhooks** — sufficient for mid-market ERP handoff without a certified SAP add-on.

---

## Decision

**Defer a native SAP connector** until:

1. Phase 1 shipment loop is boring in production (≥3 paying merchants, ≥95% auto-dispatch).
2. At least one merchant requests SAP IDoc/BAPI integration with signed SOW.
3. NetSuite MVP (§7.2.3) proves the integration adapter pattern in production.

Until then, SAP customers integrate via:

- `POST /v1/merchant-api/*` programmatic shipments
- Bulk CSV (`erp_shipments` template)
- Outbound webhooks (`order.*`, `shipment.delivered`)

---

## Consequences

- No `integrations/sap/` package in Phase 1.
- Marketplace UI lists SAP as **planned** — not App Store / SAP Store listing.
- Revisit when ACV ≥$100k enterprise pipeline justifies connector maintenance.
