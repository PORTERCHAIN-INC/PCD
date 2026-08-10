# TAM — vertical expansion narrative (§10 · INV-G4)

**Type:** CANONICAL  
**Checklist:** INV-G4  
**Last verified:** 2026-07-09  
**Companion:** [ICP.md](../ICP.md) · [PORTERCHAIN_CHARTER.md](../PORTERCHAIN_CHARTER.md)

## Category (not courier)

Porterchain is **B2B last-mile orchestration software** — merchants keep the shipper relationship; we provide quote → pay → dispatch → track → POD → invoice on one platform.

## Phase 1 wedge (GTA)

| Vertical                  | Workflow moat                               | Checklist    |
| ------------------------- | ------------------------------------------- | ------------ |
| Construction / industrial | Site access, liftgate, standing orders      | §8.1.6–8.1.7 |
| Medical / lab             | Chain-of-custody metadata, cold-chain flags | §8.1.12      |
| Food wholesale            | Standing orders, temperature bands          | §8.1.9       |

**SAM (Phase 1):** ~2,400 GTA B2B shippers in ICP band (50–500 shipments/week) × $24k ACV ≈ **$58M CAD**.

## Expansion vectors (TAM growth)

| Vector              | Mechanism                                            | When                         |
| ------------------- | ---------------------------------------------------- | ---------------------------- |
| **Geo**             | Clone dispatch playbook to Montreal, Vancouver       | After GTA ≥95% auto-dispatch |
| **Vertical depth**  | Compliance dossier, ERP adapters (NetSuite MVP live) | Phase 1 prod loop            |
| **Platform GMV**    | Merchant API + webhooks (25%+ GMV target §7.3.5)     | Dev metrics green            |
| **3PL white-label** | Parent/subsidiary orgs + tracking domain             | §9.2, §11.2.3                |

**TAM (North America B2B orchestration):** $4–6B — mid-market shippers outsourcing last-mile without building dispatch software.

## Investor talking points

1. **Land:** GTA vertical workflows (construction, medical, wholesale) — not a horizontal courier play.
2. **Expand:** Same engine + adapter interface (`ADAPTER_INTERFACE.md`) for ERP and storefront integrations.
3. **Compound:** Network data (route density, margin intelligence) via `monopoly-metrics` — switching cost rises with volume.

## Evidence in product

- `/solutions/{vertical}` pages — `validate:product-vision`
- Case study with metrics — `case-study-construction-distributor-gta`
- Platform + monopoly admin metrics APIs
