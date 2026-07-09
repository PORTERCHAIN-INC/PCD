# Priority TODOs — Porterchain

**Type:** CANONICAL  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-09  
**Progress:** 289/418 checklist items (~69%)

---

## Next up — dev layer only

| #     | ID          | Task                                                   |
| ----- | ----------- | ------------------------------------------------------ |
| **1** | **FND-G5**  | Close 0.7.5 prod Fleetbase bridge (DD-05) — prod layer |
| **2** | **§0 FND**  | Foundation gates (0.1 prod, FND-G1–G3)                 |
| **3** | **§6 DES**  | DES-G1 designer review (subjective)                    |
| **4** | **§4 AI**   | AI-G1 prod models with lift (Phase 2 data)             |
| **5** | **§8 MOAT** | Medical vertical §8.1.2–8.1.5 · food §8.1.8–8.1.9      |

**Skipped:** §7.2.1 Shopify · §7.2.2 WooCommerce native apps

---

## Dev verification

```bash
pnpm validate:moat
pnpm validate:ai-governance && pnpm validate:category-positioning
pnpm validate:developer-portal && pnpm validate:design
pnpm validate:product-vision && pnpm validate:architecture
```

---

## Completed (latest)

- §8.1.7 — liftgate pricing surcharge ($45) in `porterchain_pricing` + merchant booking checkbox
- §8.1.12 — vertical onboarding selector (construction/medical/food/wholesale) on merchant portal
- §8.1.6 — construction site access notes on merchant booking (API + UI + guard)
- E.2 — root POINTER stubs consolidated to 20 (`docs/POINTER_STUB_INDEX.md`)

**Frozen:** Stripe · **Deferred:** §1.3.3 prod merchants, FND-G5 prod bridge
