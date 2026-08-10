# ADR-014 — Phase 2 feature flags

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-08  
**masterrule:** [§21.4](../../masterrule.md#214-phase-1-vs-phase-2-uber-30-for-b2b-logistics)  
**Checklist:** §1.2.4 · DD-26  
**Related:** [ADR-010-phase2-strategies.md](./ADR-010-phase2-strategies.md)

---

## Context

Phase 2 surfaces (CRM, Route Center, AI dispatch, analytics widgets) must not appear in default UX or production until Phase 1 loop metrics are green. Environment flags give operators an explicit, auditable switch per capability.

---

## Decision

Introduce **`PORTERCHAIN_PHASE2_*` flags** — all default **`false`**:

| Env var                           | Capability gated                              |
| --------------------------------- | --------------------------------------------- |
| `PORTERCHAIN_PHASE2_CRM`          | Admin CRM modules                             |
| `PORTERCHAIN_PHASE2_ROUTE_CENTER` | **Retired** — do not re-enable; use Fleetbase |
| `PORTERCHAIN_PHASE2_AI_DISPATCH`  | ML dispatch strategies                        |
| `PORTERCHAIN_PHASE2_ANALYTICS`    | Analytics warehouse widgets                   |
| `PORTERCHAIN_PHASE2_INTELLIGENCE` | Intelligence engine copilots                  |

Shared definitions:

- Python: `porterchain_shared.config.phase2`
- TypeScript: `@porterchain/config/phase2`
- API: `Settings.phase2_flags` property

CI guard: `pnpm validate:phase2-flags` — flags exist, default off, ADR-010/014 present.

---

## Consequences

- Enabling any flag in production requires explicit ops approval and checklist update.
- Phase 2 code paths must check flags before registering routes or UI nav items.
- Forbidden paths (CRM, Route Center) remain absent regardless of flags until deliberately reintroduced behind flags **and** ADR review.
