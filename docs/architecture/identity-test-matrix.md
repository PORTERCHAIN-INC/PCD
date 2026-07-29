# Unified identity — Phase 9 test matrix

**Type:** WORKING  
**Status:** Phase 9 local — matrix green via `pnpm identity:test`  
**Date:** 2026-07-28  
**Related:** [unified-identity-target.md](./unified-identity-target.md) · [clerk-consolidation.md](../runbooks/clerk-consolidation.md)

---

## 1. Command

```bash
pnpm identity:test
# equivalent:
cd apps/api && PYTHONPATH=src .venv/bin/python scripts/run_identity_matrix.py
```

Runs characterization + Phases 2–9 (+ `test_clerk_registry`).

---

## 2. Matrix (what must stay green)

| Area                | Expectation                                              | Primary tests          |
| ------------------- | -------------------------------------------------------- | ---------------------- |
| **401**             | Missing/invalid bearer; bad issuer/azp                   | phase3, phase9         |
| **403**             | Suspended; missing permission; invite-only unprovisioned | phase3, phase5, phase9 |
| **IDOR**            | Merchant org A workspaces exclude org B                  | phase9                 |
| **Multi-role**      | Customer+driver without admin                            | phase5, phase9         |
| **Portal ≠ role**   | Customer lacks `platform.admin.access`                   | phase9                 |
| **Webhook**         | Bad sig → 400; missing secret → 503                      | phase4, phase9         |
| **Idempotency**     | Duplicate Svix claim → `duplicate` / False               | phase4, phase9         |
| **Session-context** | No secrets/tokens in payload                             | phase3, phase9         |
| **Invite-only**     | Admin not open signup; allowlist for migration           | phase7, phase9         |
| **Config audit**    | Names only; test keys rejected in prod                   | phase6                 |
| **FK backfill**     | Additive targets; pending ids skipped                    | phase8, phase9         |
| **Client parity**   | Portal access keys = `UnifiedPermission`                 | phase9                 |

Frontend AccessGates rely on the same permission strings (`platform.admin.access`, …). No separate FE runner in Phase 9 — parity is asserted in Python against the catalog.

Phase 10 cutover is **manual only**: [clerk-cutover-phase10.md](../runbooks/clerk-cutover-phase10.md). Doc guards live in `test_unified_identity_phase10.py`.

---

## 3. Explicit confirmation

> No production Clerk / Doppler / DB mutations in Phase 9. This phase only expands automated tests and documentation.
