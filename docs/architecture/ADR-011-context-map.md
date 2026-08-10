# ADR-011 — Bounded context map (strangler)

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-08  
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity) · Appendix D  
**Checklist:** §3.2.10, ARCH-G2  
**Related:** [MODULE_DEPENDENCY.md](./MODULE_DEPENDENCY.md) · [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) · `verify_d2_contracts.py` · `verify_model_ownership.py`

---

## Context

Porterchain is a **modular monolith** (`apps/api`). Phase 1 ships the ops loop without rebuilding microservices. Martin Fowler strangler discipline requires:

1. Explicit bounded contexts with table ownership
2. Thin routers → `*_engine` services → repositories
3. CI guards that **freeze** legacy coupling while preventing new debt

This ADR is the context map investors and engineers use before extracting engines further.

---

## Decision

| Context                 | ORM module                             | Write owner                 | Read via                                        |
| ----------------------- | -------------------------------------- | --------------------------- | ----------------------------------------------- |
| **Booking / shipment**  | `booking_models.py`                    | `booking_engine`            | Admin ops, support, order_engine (legacy reads) |
| **Merchant B2B**        | `merchant_models.py`                   | `merchant_engine`           | Admin 360, auth provisioning (legacy writes)    |
| **Admin ops**           | `admin_models.py`                      | `admin_engine`              | Routers only                                    |
| **Driver**              | `driver_models.py`                     | `driver_engine`             | Admin driver 360                                |
| **Fleetbase mirror**    | `fleetbase_models.py`                  | `fleetbase_engine`          | Booking sync, admin diagnostics                 |
| **CRM / collaboration** | `crm_models.py`                        | `collaboration_engine`      | Admin CRM sales bridge                          |
| **Identity**            | `identity_models.py`, `user_models.py` | `auth/user_sync_service.py` | All portals                                     |
| **Billing**             | `billing_engine/models.py`             | `billing_engine`            | Merchant billing, Stripe webhooks               |
| **Notifications**       | `notification_engine/models.py`        | `notification_engine`       | Event router                                    |
| **Shared kernel**       | `domain/states.py`, `domain/tenant_*`  | N/A (no tables)             | All engines                                     |

`porterchain_api.models` is a **shim** re-exporting `booking_models` during migration (§3.2.1).

---

## Integration patterns (allowed)

| Pattern                        | Example                                                 | Guard                                                 |
| ------------------------------ | ------------------------------------------------------- | ----------------------------------------------------- |
| **Domain events**              | `booking_engine._core.emit_event` → notification router | Event catalog only (§3.3)                             |
| **Adapter bridge**             | `fleetbase_engine.integration_bridge`                   | No Fleetbase HTTP outside adapter (§3.1.2)            |
| **Read-only cross-context**    | `admin_engine` queries `Merchant` for live map          | No new `db.add/commit` on foreign tables (§3.2.2)     |
| **Legacy cross-engine import** | `merchant_engine` → `booking_engine` transitions        | Frozen allowlist in `verify_d2_contracts.py` (§3.2.9) |

**Forbidden (new code):**

- Router → ORM mutation (§0.3.3)
- Frontend → Fleetbase / Stripe SDK (§3.1.2–3.1.3)
- New `*_engine` → other `*_engine` import not on legacy list (§3.2.9)
- New non-owner writes to `merchant_models` tables (§3.2.2)

---

## Strangler sequence

```
Phase A (now)     — CI freeze + model module splits (booking_models, ownership guards)
Phase B (next)    — Repositories per context; auth provisioning → merchant_engine
Phase C (later)   — Schemas per engine (§3.2.13 done); horizontal scale docs
```

Do **not** extract microservices until ARCH-G2 is green and P0 loop SLO holds in CI.

---

## CI enforcement

| Guard                       | Script                                  | Checklist      |
| --------------------------- | --------------------------------------- | -------------- |
| Cross-engine imports        | `verify_d2_contracts.py`                | §3.2.9         |
| Merchant table writes       | `verify_model_ownership.py`             | §3.2.2         |
| Admin table writes          | `verify_model_ownership.py`             | §3.2.3         |
| Driver / Fleetbase writes   | `verify_model_ownership.py`             | §3.2.4–3.2.5   |
| Order transition paths      | `verify_order_transitions.py`           | §3.3.1         |
| Context repositories        | `verify_repositories.py`                | §3.2.8         |
| CRM table writes            | `verify_model_ownership.py`             | §3.2.6         |
| Identity / user writes      | `verify_model_ownership.py`             | §3.2.7         |
| Shared kernel states        | `verify_shared_kernel.py`               | §3.2.11        |
| Event catalog version       | `verify_event_catalog.py`               | §3.3.4         |
| Merchant webhook fanout     | `verify_merchant_webhook_event_path.py` | §3.3.4         |
| Reporting context           | `verify_reporting_context.py`           | §3.2.12        |
| Schema modules              | `verify_schema_context.py`              | §3.2.13        |
| Queue backpressure RUNBOOK  | `verify_queue_runbook.py`               | §3.4.5         |
| Fleetbase sync handlers     | `verify_fleetbase_event_handlers.py`    | §3.3.2         |
| Notification templates      | `verify_notification_catalog.py`        | §3.3.3         |
| Fleetbase / Stripe / UI API | `verify_architecture_boundaries.py`     | §3.1.2–3.1.4   |
| API stateless               | `verify_api_stateless.py`               | §3.4.1         |
| DB pool tuning              | `verify_db_pool.py`                     | §3.4.3         |
| WebSocket scale doc         | `verify_realtime_scale_doc.py`          | §3.4.2, §3.5.4 |
| Managed Postgres + replica  | `verify_managed_postgres.py`            | §3.4.7         |
| Masterrule §3 layer audit   | `verify_masterrule_layer_audit.py`      | ARCH-G3        |
| Router thinness             | `verify_d2_contracts.py`                | §0.3.9         |

```bash
pnpm validate:architecture && pnpm validate:d2
```

---

## Consequences

- **Positive:** Diligence can point to frozen debt registers; new coupling fails CI.
- **Negative:** 21 legacy merchant writers remain until auth/admin paths delegate to `merchant_engine`.
- **Neutral:** Reads across contexts stay common until repository facades land (§3.2.8).

---
