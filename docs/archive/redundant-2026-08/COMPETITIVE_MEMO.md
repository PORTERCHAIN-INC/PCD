# Competitive memo — Porterchain positioning

**Type:** CANONICAL  
**Checklist:** §9.3.1–9.3.4 · §10.2.4  
**Last verified:** 2026-07-08  
**Category:** B2B last-mile orchestration software (not consumer courier)

---

## Category definition (§9.1.1)

**Porterchain** = orchestration platform for merchants who own the customer relationship. We sell dispatch controls, SLA visibility, and audit-ready proof — merchants keep their brand; we run structured last-mile execution via Fleetbase adapter.

**Not:** Uber/DoorDash-style consumer courier app, generic 3PL marketing site, or Fleetbase console resale.

---

## Threat matrix

| Competitor             | What they optimize                        | Porterchain counter                                                    | Risk                               |
| ---------------------- | ----------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------- |
| **Uber / DoorDash**    | Consumer on-demand, marketplace liquidity | B2B SLAs, recurring routes, merchant API, no gig UX on web             | Commodity price pressure narrative |
| **Amazon Shipping**    | Amazon-ecosystem scale                    | Independent merchants, multi-vertical Ontario focus, own ERP keys      | Enterprise shipper lock-in         |
| **Onfleet**            | Mid-market route SaaS                     | Full quote→pay→invoice loop + Fleetbase execution depth                | Feature parity on routing UI       |
| **Fleetbase (vendor)** | Dispatch OS product                       | Porterchain owns merchant UX, billing, Stripe, Clerk; adapter boundary | Over-dependence on vendor roadmap  |

---

## Win themes (deck + site + masterrule)

1. **Shipment loop in one stack** — quote, pay, dispatch, track, POD, invoice (Phase 1).
2. **Orchestration, not marketplace** — accountable workflows vs ad-hoc drivers.
3. **Open platform** — merchant API, webhooks, OAuth partners (`/developers`).
4. **Vertical proof** — construction distributor case study with on-time % + cost delta.

---

## Narrative consistency (§9.1.2)

Canonical phrase: **"logistics orchestration software"** / **"operating system for commercial logistics"**.

Sources must align: `masterrule.md` §2, `docs/ICP.md`, `website/messages/corporate-en.json` hero, `docs/CATEGORY.md`.

CI: `pnpm validate:category-positioning`

---

## What we do not claim (§9.1.3 · §9.1.4)

- Cheapest courier in the GTA.
- Marketplace driver signup on homepage (drivers → `/vehicle-partner`).
- Autonomous AI dispatch in production (Phase 2 only, flagged).
