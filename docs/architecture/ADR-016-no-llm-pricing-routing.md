# ADR-016 — No LLM on pricing or routing paths

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-08  
**Checklist:** §4.2.9 · AI-G4  
**Related:** [ADR-010-phase2-strategies.md](./ADR-010-phase2-strategies.md)

---

## Context

Investors and customers increasingly scrutinize "AI" claims. Porterchain Phase 1 pricing and routing must be **deterministic, auditable, and explainable** — Valhalla/OSRM distance, published rate cards, and OR-Tools assignment when enabled behind `PORTERCHAIN_PHASE2_AI_DISPATCH`.

LLM inference on the pay path introduces non-reproducible quotes, regulatory risk, and marketing backlash if oversold.

---

## Decision

**Ban LLM / generative models from:**

| Path                          | Allowed engine                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------ |
| Quote pricing                 | `pricing_engine` + Valhalla/OSRM distance                                      |
| Route optimization (Phase 1)  | Valhalla matrix, OSRM fallback                                                 |
| Dispatch assignment (Phase 1) | Rule-based + Fleetbase adapter                                                 |
| Admin copilot (Phase 2)       | Read-only suggestions — **no** auto-apply to live orders without human confirm |

Marketing copy must not claim "AI-powered" pricing or routing until a documented model with measured lift ships behind feature flags (see §4.2).

---

## Consequences

- `verify_no_false_ai_marketing.py` bans `AI-powered`, `GPT`, `LLM` in `website/messages/*.json`.
- `intelligence_engine/` copilot endpoints cannot mutate `Order.state` or `Quote.amount_cents` without explicit admin action.
- Phase 2 ML dispatch requires model card + ADR amendment before production enable.
