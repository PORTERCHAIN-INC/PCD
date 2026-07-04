# Roadmap — Porterchain Production Readiness

**Date:** July 3, 2026  
**Reference:** `GAP_ANALYSIS.md`, `PRODUCTION_READINESS_REPORT.md`, `masterrule.md`

---

## Goal

Achieve **Production Ready** status: all critical business workflows pass end-to-end without architectural violations.

**Current estimate:** 2–3 weeks focused execution.

---

## Phase 1 — Blockers (Week 1)

Priority: unblock production deploy and E2E certification.

| #   | Task                                                    | Severity | Owner   | Effort | Depends          |
| --- | ------------------------------------------------------- | -------- | ------- | ------ | ---------------- |
| 1.1 | Production Stripe webhook + E2E booking test in staging | High     | DevOps  | 4h     | Stripe Dashboard |
| 1.2 | Configure Firebase credentials; verify FCM push         | High     | Backend | 1d     | Firebase console |
| 1.3 | Global API rate limiting (Redis sliding window)         | High     | Backend | 1–2d   | Redis            |
| 1.4 | Booking draft reconciliation worker                     | High     | Backend | 1–2d   | Worker           |
| 1.5 | Fail startup on default `jwt_secret` in prod            | Medium   | Backend | 2h     | —                |
| 1.6 | Document `stripe listen` in ENVIRONMENT_VARIABLES.md    | Medium   | Docs    | 2h     | —                |

**Exit criteria:** Retail booking + notification + security gates pass in staging.

---

## Phase 2 — Architecture Debt (Week 2)

Priority: fix violations without redesigning locked topology.

| #   | Task                                                         | Severity | Effort |
| --- | ------------------------------------------------------------ | -------- | ------ |
| 2.1 | Extract `DriverRouterService` from `routers/driver.py`       | High     | 2–3d   |
| 2.2 | Create shared `order_engine/` or `domain/order_lifecycle.py` | High     | 3–5d   |
| 2.3 | Move order state constants to `domain/`                      | Medium   | 4h     |
| 2.4 | Consolidate Fleetbase bridges                                | Medium   | 2d     |
| 2.5 | Thin notification/order routers                              | Medium   | 1–2d   |

**Exit criteria:** No High architecture violations in `ARCHITECTURE_AUDIT.md`.

---

## Phase 3 — Integration & Events (Week 2–3)

| #   | Task                                                         | Severity | Effort |
| --- | ------------------------------------------------------------ | -------- | ------ |
| 3.1 | Billing handler for `refund.requested` / `refund.issued`     | High     | 1d     |
| 3.2 | Unify event catalog (`booking.created` in `DomainEventType`) | Medium   | 4h     |
| 3.3 | Fleetbase E2E dispatch test in staging                       | High     | 1d     |
| 3.4 | Add Valhalla/OSRM to `/health/ready`                         | Medium   | 4h     |
| 3.5 | Customer tracking map (`apps/customer`)                      | Medium   | 1d     |

**Exit criteria:** Dispatch → delivery → POD verified with Fleetbase stack.

---

## Phase 4 — Polish (Week 3+)

| #   | Task                                         | Severity | Effort   |
| --- | -------------------------------------------- | -------- | -------- |
| 4.1 | Finance PDF invoices                         | Medium   | 2d       |
| 4.2 | CRM audit for all entities                   | Medium   | 1d       |
| 4.3 | Route result caching                         | Medium   | 1d       |
| 4.4 | FK migration for route_center + invitations  | Medium   | 4h       |
| 4.5 | Website `draft_id` recovery on continue page | Medium   | 2h       |
| 4.6 | JSONB rollout (remaining tables)             | Low      | 1–2d     |
| 4.7 | Driver mobile app (beyond scaffold)          | Medium   | 2+ weeks |

---

## Completed This Audit ✅

| Task                                  | Files                                            |
| ------------------------------------- | ------------------------------------------------ |
| EXPIRED draft webhook race            | `domain/states.py`, `booking_draft_service.py`   |
| Checkout TTL protection               | `booking_draft_service.py`, `payment_service.py` |
| Quote endpoint draft_expired handling | `routers/quotes.py`                              |
| Unique `orders.quote_id`              | `models.py`, alembic `n2o3p4q5r6s7`              |
| Fleetbase event mapping               | `fleetbase-adapter/events/__init__.py`           |
| `notification.sent` async emit        | `delivery_service.py`                            |
| Refund events on claims               | `claims_service.py`                              |
| All audit reports                     | `*_AUDIT.md`, `GAP_ANALYSIS.md`, etc.            |

---

## Production Ready Checklist

When all items below are ✅, update `PRODUCTION_READINESS_REPORT.md` to **PRODUCTION READY**:

- [ ] Retail booking E2E with live Stripe webhook
- [ ] Merchant booking + CSV E2E
- [ ] Dispatch → delivery → POD with Fleetbase
- [ ] Firebase push verified
- [ ] Global rate limits active
- [ ] No Critical/High open gaps in `GAP_ANALYSIS.md`
- [ ] Driver router refactored (or waived with documented exception)
- [ ] Worker + Redis + PostgreSQL in production
- [ ] Alembic at head
- [ ] Security: no dev bypasses, non-default secrets

---

## Principles (masterrule §19–20)

1. **Do not redesign** the locked architecture
2. **Reuse** existing `*_engine` services
3. **Fix violations** in place — no parallel implementations
4. **Update `masterrule.md`** only for intentional architectural changes

---

_Track progress against `GAP_ANALYSIS.md` issue IDs._
