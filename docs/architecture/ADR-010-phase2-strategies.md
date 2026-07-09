# ADR-010 — Phase 2 capabilities are strategies, not services

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-08  
**masterrule:** [§21.4](../../masterrule.md#214-phase-1-vs-phase-2-uber-30-for-b2b-logistics)  
**Checklist:** §1.2.5 · §4.2 · Appendix D5  
**Related:** [ADR-014-phase2-feature-flags.md](./ADR-014-phase2-feature-flags.md)

---

## Context

Porterchain Phase 1 ships the **shipment loop** (quote → pay → dispatch → track → POD → invoice). Phase 2 adds intelligence and analytics **without** new deployables, duplicate UIs, or microservice sprawl.

Investor diligence and internal gates require an explicit decision before CRM, Route Center, AI dispatch, or analytics surfaces return.

---

## Decision

Phase 2 capabilities plug into **existing engines** as strategies/read models:

| Capability         | Phase 2 rule                                               |
| ------------------ | ---------------------------------------------------------- |
| AI dispatch        | Strategy behind existing dispatch port — no new admin app  |
| Predictive ETA     | Read model + events — no duplicate tracking UI             |
| Dynamic pricing    | Extension to pricing engine — same quote API               |
| Analytics / fleet  | Read APIs + admin widgets — no Reports BI center           |
| CRM / Route Center | **Deferred** — deleted from Phase 1 surfaces (Appendix D2) |

Do **not** add `ai_dispatch_engine`, `analytics_engine`, or resurrect CRM/Route Center until Phase 1 is boring in production.

---

## Consequences

- Event catalog may include Phase 2 stub events with no consumers (see `EVENT_CATALOG.md`).
- `Order.assigned_executor_type` and FleetExecutor ACL remain Phase 1 hooks only.
- Feature flags (`PORTERCHAIN_PHASE2_*`) default **false** — see ADR-014.
