# Model cards — Porterchain

**Type:** CANONICAL  
**Checklist:** §4.3.2 · AI-G1 (Phase 2)  
**Last verified:** 2026-07-08  
**Governance:** [ADR-016](../architecture/ADR-016-no-llm-pricing-routing.md)

---

## Phase 1 (production — deterministic)

| Model / system          | Owner                     | Input                         | Output                               | Pay path?            | Monitoring                          |
| ----------------------- | ------------------------- | ----------------------------- | ------------------------------------ | -------------------- | ----------------------------------- |
| **Valhalla routing**    | `pricing_engine`          | Lat/lng pairs, vehicle class  | Distance km, duration min, polyline  | Yes (quote distance) | `/health/ready` routing check       |
| **OSRM fallback**       | `pricing_engine`          | Same                          | Distance/duration when Valhalla down | Yes (degraded)       | API health `routing`                |
| **Rate card pricing**   | `services/pricing-engine` | Distance, vehicle, surcharges | `amount_cents`                       | Yes                  | Unit tests `test_pricing_engine.py` |
| **Rule-based dispatch** | `fleetbase_engine`        | Order ready → adapter         | Fleetbase job create                 | Yes                  | Fleetbase sync SLO dashboard        |

**Marketing rule:** Do not call Phase 1 systems "AI" or "ML" in public copy (`validate:design` ban-list).

---

## Phase 2 (planned — feature-flagged)

| Model               | Target metric                   | Flag                              | Status      |
| ------------------- | ------------------------------- | --------------------------------- | ----------- |
| ETA calibration v0  | MAE < 15 min vs actual          | `PORTERCHAIN_PHASE2_INTELLIGENCE` | Not trained |
| Dispatch scorer     | On-time % lift vs manual        | `PORTERCHAIN_PHASE2_AI_DISPATCH`  | Not trained |
| Demand forecast     | WAPE on weekly volume           | `PORTERCHAIN_PHASE2_ANALYTICS`    | Not trained |
| Admin copilot (LLM) | Human-accepted suggestions only | `PORTERCHAIN_PHASE2_INTELLIGENCE` | Not wired   |

Each Phase 2 model requires: training data contract, offline eval notebook, owner, rollback, and an updated row in this file before prod enable.

---

## Explicit bans (ADR-016)

- No LLM / generative model on quote `amount_cents` or route distance.
- No auto-apply of copilot output to `Order.state` without admin confirm.
- No "AI-powered" marketing until a row above shows **prod** status with measured lift.
