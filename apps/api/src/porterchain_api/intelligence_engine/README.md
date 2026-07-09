# Porterchain intelligence engine (Phase 2 boundary)

**Status:** Scaffold only — no production ML on pay path in Phase 1.  
**Checklist:** §4.3.1 · AI-G3  
**ADRs:** ADR-010 · ADR-014 · ADR-016

Planned capabilities (behind `PORTERCHAIN_PHASE2_INTELLIGENCE` / `PORTERCHAIN_PHASE2_AI_DISPATCH`):

| Module                  | Phase | Pay-path?                            |
| ----------------------- | ----- | ------------------------------------ |
| `features.py`           | 2     | No — feature store for batch jobs    |
| `eta_service.py`        | 2     | No — read-model enrichment           |
| `dispatch_scorer.py`    | 2     | No — admin recommendation only       |
| `copilot_service.py`    | 2     | No — read-only admin assist          |
| `assignment_service.py` | 2     | No — admin batch recommendation only |
| `pricing_model.py`      | 2     | No — margin elasticity report        |
| `forecast_service.py`   | 2     | No — admin demand widget             |
| `monitoring.py`         | 2     | No — drift alerts                    |

Phase 1 uses deterministic routing (Valhalla/OSRM) and `pricing_engine` rate cards only.
