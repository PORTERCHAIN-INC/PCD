# Carrier pool legal model (§9.2.4)

**Type:** CANONICAL  
**Checklist:** §9.2.4 · Appendix H enterprise diligence  
**Last verified:** 2026-07-09

## Model summary

Porterchain operates as a **B2B logistics orchestration platform**. Merchants contract with Porterchain for software + coordinated delivery execution. Drivers in the network are **independent contractor carriers**, not Porterchain employees or a gig marketplace.

| Party            | Relationship         | Obligation                                                             |
| ---------------- | -------------------- | ---------------------------------------------------------------------- |
| Merchant         | Platform customer    | Books shipments, owns customer relationship, pays per contract terms   |
| Porterchain      | Orchestrator         | Quote, dispatch, tracking, billing, SLA dashboard                      |
| Driver / carrier | Independent operator | Accepts assigned routes, maintains insurance + compliance docs on file |

## Why not Uber/DoorDash UX

- No open marketplace bidding or surge pricing for consumers
- No driver self-serve signup without admin vetting
- Assignment and certification gates (e.g. medical transport) enforced in API

## Fleetbase boundary

Last-mile **execution** may sync through the Fleetbase adapter. Fleetbase is infrastructure — not the merchant-facing product (see ADR-011, COMPETITIVE_MEMO.md).

## Compliance artifacts on file (driver)

- License, insurance, vehicle registration (see admin driver documents)
- Medical transport certification when required (§8.1.5)
- Background check status field on driver profile

## API reference

`GET /v1/admin/monopoly-metrics` → `carrier_pool_legal` block links to this document.
