# Ideal Customer Profile (ICP)

**Type:** CANONICAL  
**Parent SSOT:** [PORTERCHAIN_CHARTER.md](./PORTERCHAIN_CHARTER.md)  
**Checklist:** §1.3.1 · §1.3.5  
**Last verified:** 2026-07-09  
**Stage:** Phase 1 — Transportation Capacity Network (customers buy vehicle + driver capacity)  
**Category:** B2B last-mile orchestration software — merchants keep the shipper relationship; Porterchain provides quote → pay → dispatch → track → POD → invoice on one platform.

## Who we serve

| Dimension     | Phase 1 ICP                                                                                                                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Industry**  | Ontario B2B shippers: construction supply, electrical/plumbing wholesale, pharmacy/lab, manufacturing, regional distribution |
| **Geo**       | Greater Toronto Area (GTA) + Ontario metros; expand after network density in core lanes                                      |
| **Buyer**     | Ops manager / owner who already runs vehicles and drivers but needs **overflow, backup, and same-day capacity**              |
| **Deal size** | Quote-based by vehicle class, route, urgency, and proof requirements — **not** platform subscription ACV                     |
| **Pain**      | Driver sick · vehicle breakdown · urgent order · peak season · jobsite emergency · forgotten material · address change       |

## Pain moments (when Porterchain wins)

| Moment                   | What they need                                         |
| ------------------------ | ------------------------------------------------------ |
| Fleet is full            | Extra cargo van, Sprinter, or box truck + driver today |
| Driver unavailable       | Backup professional driver on a known lane             |
| Urgent same-day          | Vehicle matched to load with tracking and proof        |
| Recurring route overflow | Scheduled capacity without hiring                      |
| Different vehicle class  | Sedan through box truck without owning the asset       |

## Who we are not (Phase 1)

- Consumer parcel / “book a courier” app (Uber/DoorDash UX)
- Enterprise buyer evaluating **dispatch SaaS** or platform subscription as the primary purchase
- API-first integrator where automation is the first sales motion (integrations are **by request** after capacity programs)
- National LTL carrier — we are a **capacity partner** for regional B2B execution in Ontario

## What customers buy today

> **Transportation capacity** — professional drivers and commercial vehicles (sedan through box truck), orchestrated with tracking, proof of delivery, and accountable execution.

Software runs behind every delivery in the network. It is **not** sold as a separate SKU in Phase 1.

## Core loop (Phase 1 revenue)

Request capacity → quote → dispatch → track → proof of delivery → invoice

## 15-second test (must pass)

A construction, pharmacy, or electrical ops buyer can answer:

1. **What do I buy?** Vehicle-and-driver capacity
2. **When do I use it?** When my own logistics cannot cover the shipment
3. **What next?** Get a quote

## Traction gates (§1.3.3)

- [ ] 3+ recurring capacity programs with repeat weekly volume
- [x] 1 published case study with on-time % + cost delta — `blog/case-study-construction-distributor-gta` 2026-07-08
- [ ] “Who misses us if we disappear?” → ops teams lose overflow/backup capacity + proof they trust on critical lanes

## Expansion (Phase 2+)

Business logistics platform, deeper integrations, ETA calibration, vertical workflows — **after** Phase 1 capacity network proves repeat demand and execution quality. See [PORTERCHAIN_CHARTER.md](./PORTERCHAIN_CHARTER.md) for Phases 2–4.

## Website alignment

- Primary CTA: **Get a quote** (`/contact?intent=quote`)
- Vehicle catalog: `/business#fleet`
- Execution plan: [WEBSITE_GTM_EXECUTION_PLAN.md](./WEBSITE_GTM_EXECUTION_PLAN.md)
