# Ideal Customer Profile (ICP)

**Type:** CANONICAL  
**Checklist:** §1.3.1 · §1.3.5  
**Last verified:** 2026-07-08  
**Stage:** Phase 1 — B2B last-mile orchestration software (not courier operator)

## Who we serve

| Dimension      | Phase 1 ICP                                                                          |
| -------------- | ------------------------------------------------------------------------------------ |
| **Industry**   | Regional B2B shippers: medical/lab, industrial parts, e-commerce fulfillment brokers |
| **Geo**        | Greater Toronto Area (GTA) + Ontario corridors; expand after dispatch loop boring    |
| **Buyer**      | Ops director / logistics manager at merchant with 50–500 shipments/week              |
| **ACV target** | ≥$24k CAD (platform + volume)                                                        |
| **Pain**       | Manual dispatch, no SLA visibility, courier marketplace lock-in                      |

## Who we are not

- Consumer same-day courier app (Uber/DoorDash UX)
- Generic “logistics company” — we sell **orchestration software** to merchants who own the customer relationship

## Core loop (Phase 1)

Quote → book → pay → dispatch → track → POD → invoice

## Traction gates (§1.3.3)

- [ ] 3+ paying merchants on prod dispatch
- [x] 1 published case study with on-time % + cost delta — `blog/case-study-construction-distributor-gta` 2026-07-08
- [ ] “Who misses us if we disappear?” → merchant ops teams lose dispatch + SLA dashboard

## Expansion (Phase 2+)

Vertical workflows (pharmacy cold chain, industrial), Shopify app, ETA calibration — **after** Phase 1 prod loop ≥95% auto-dispatch.
