# Porterchain intelligence engine (Phase 2 boundary)

**Status:** Scaffold only — no production ML on pay path in Phase 1.  
**Checklist:** §4.3.1 · AI-G3  
**ADRs:** ADR-010 · ADR-014 · ADR-016

Planned capabilities (behind `PORTERCHAIN_PHASE2_INTELLIGENCE` / `PORTERCHAIN_PHASE2_AI_DISPATCH`):

| Module               | Phase | Pay-path?                         |
| -------------------- | ----- | --------------------------------- |
| `eta_service.py`     | 2     | No — read-model enrichment        |
| `dispatch_scorer.py` | 2     | No — admin recommendation only    |
| `copilot_service.py` | 2     | No — read-only admin assist       |
| `features.py`        | 2     | No — feature store for batch jobs |

Phase 1 uses deterministic routing (Valhalla/OSRM) and `pricing_engine` rate cards only.
