# Priority TODOs — Porterchain

**Type:** CANONICAL  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-09  
**Progress:** 392/418 checklist items (~94%)

---

## Next up — dev layer only

| #     | ID          | Task                                                   |
| ----- | ----------- | ------------------------------------------------------ |
| **1** | **FND-G5**  | Close 0.7.5 prod Fleetbase bridge (DD-05) — prod layer |
| **2** | **§0 FND**  | Foundation gates FND-G1–G2 (prod execution loop)       |
| **3** | **§10.2.2** | Record 3-min MP4 from `docs/investor/DEMO_VIDEO.md`    |
| **4** | **§4 AI**   | Train prod models with lift (AI-G1)                    |
| **5** | **§6**      | External designer review (DES-G1 rubric ready)         |

**Skipped:** §7.2.1 Shopify · §7.2.2 WooCommerce (`[—]` in checklist)

---

## Dev verification

```bash
pnpm validate:notification-catalog   # via notifications-billing
pnpm validate:pod-media
pnpm validate:mobile-appendix
pnpm validate:notifications-billing
```

Seed analytics legs (§4.1.1 dev):

```bash
cd apps/api && source .venv/bin/activate && PYTHONPATH=src python scripts/seed_analytics_stop_legs.py --count 10000
```

---

## Completed (latest)

- Medical temp excursion → event bus (fixes `verify_notification_catalog`)
- B.17 POD retention doc · C.7 EAS config · MON-G4 metro playbook
- DES-G1 rubric · EXE-G4 monthly prod validate doc
- §4.1.1 analytics seed script (dev path)

**Frozen:** Stripe · **Deferred:** FND-G5 prod bridge
