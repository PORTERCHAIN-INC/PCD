# Gap Analysis — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` v3.1 vs current codebase

---

## Summary

| Severity | Open | Fixed This Audit |
| -------- | ---- | ---------------- |
| Critical | 0    | 1                |
| High     | 6    | 3                |
| Medium   | 14   | 0                |
| Low      | 8    | 0                |

---

## Critical Gaps (Resolved)

### GAP-C01 — EXPIRED draft blocks payment webhook finalization

| Field              | Value                                                                    |
| ------------------ | ------------------------------------------------------------------------ |
| **Severity**       | Critical                                                                 |
| **Root Cause**     | State machine + lazy expiry during webhook handler                       |
| **Affected Layer** | `booking_engine`                                                         |
| **Status**         | **FIXED**                                                                |
| **Fix**            | `EXPIRED→PAYMENT_COMPLETED`, checkout TTL protection, `_raw_by_quote_id` |
| **Effort**         | 4 hours                                                                  |

---

## High Gaps (Open)

### GAP-H01 — Fat driver router

| Field               | Value                                             |
| ------------------- | ------------------------------------------------- |
| **Severity**        | High                                              |
| **Root Cause**      | Business logic accumulated in controller          |
| **Affected Layer**  | `routers/driver.py`                               |
| **Recommended Fix** | Extract `DriverRouterService` to `driver_engine/` |
| **Effort**          | 2–3 days                                          |

### GAP-H02 — Merchant engine depends on admin engine

| Field               | Value                                                |
| ------------------- | ---------------------------------------------------- |
| **Severity**        | High                                                 |
| **Root Cause**      | Order lifecycle reuse via wrong dependency direction |
| **Affected Layer**  | `merchant_engine` → `admin_engine`                   |
| **Recommended Fix** | Shared `order_engine/` domain module                 |
| **Effort**          | 3–5 days                                             |

### GAP-H03 — No booking draft expiration/reconciliation worker

| Field               | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Severity**        | High                                                |
| **Root Cause**      | Expiry lazy-on-read only                            |
| **Affected Layer**  | `apps/worker`                                       |
| **Recommended Fix** | Scheduled job for stale drafts + order/draft repair |
| **Effort**          | 1–2 days                                            |

### GAP-H04 — Global API rate limits missing

| Field               | Value                                         |
| ------------------- | --------------------------------------------- |
| **Severity**        | High                                          |
| **Root Cause**      | Rate limit only on merchant API gateway       |
| **Affected Layer**  | API middleware                                |
| **Recommended Fix** | Redis sliding window on authenticated `/v1/*` |
| **Effort**          | 1–2 days                                      |

### GAP-H05 — Firebase FCM not production-ready

| Field               | Value                                                  |
| ------------------- | ------------------------------------------------------ |
| **Severity**        | High                                                   |
| **Root Cause**      | Optional credentials; log-only delivery                |
| **Affected Layer**  | `notification_engine/fcm_service.py`                   |
| **Recommended Fix** | Require credentials in prod; fail health check without |
| **Effort**          | 1 day                                                  |

### GAP-H06 — Billing engine refund consumer missing

| Field               | Value                                            |
| ------------------- | ------------------------------------------------ |
| **Severity**        | High                                             |
| **Root Cause**      | `refund.issued` emitted but no ledger handler    |
| **Affected Layer**  | `billing_engine`                                 |
| **Recommended Fix** | Handler for `refund.requested` / `refund.issued` |
| **Effort**          | 1 day                                            |

---

## High Gaps (Fixed This Audit)

| ID      | Issue                                              | Fix                                        |
| ------- | -------------------------------------------------- | ------------------------------------------ |
| GAP-H07 | Fleetbase → domain event mapping incomplete        | Expanded `FLEETBASE_EVENT_TO_DOMAIN_EVENT` |
| GAP-H08 | `notification.sent` not emitted for async channels | `delivery_service._mark_sent`              |
| GAP-H09 | `orders.quote_id` not unique                       | Migration `n2o3p4q5r6s7`                   |

---

## Medium Gaps

| ID      | Area         | Issue                                          | Effort   |
| ------- | ------------ | ---------------------------------------------- | -------- |
| GAP-M01 | Website      | `draft_id` query param unused on continue page | 2h       |
| GAP-M02 | DevOps       | Stripe local webhook not documented            | 2h       |
| GAP-M03 | Customer     | Tracking map missing                           | 1 day    |
| GAP-M04 | Finance      | PDF invoice generation                         | 2 days   |
| GAP-M05 | Security     | CRM audit incomplete                           | 1 day    |
| GAP-M06 | Security     | Hardcoded JWT secret default                   | 2h       |
| GAP-M07 | Database     | Missing FKs on route_center, invitations       | 4h       |
| GAP-M08 | Events       | Catalog drift (`booking.created` etc.)         | 4h       |
| GAP-M09 | Architecture | Duplicate Fleetbase bridges                    | 2 days   |
| GAP-M10 | Performance  | No routing result cache                        | 1 day    |
| GAP-M11 | Admin        | Fleetbase API browser quick-link               | 1h       |
| GAP-M12 | Driver       | Mobile app scaffold only                       | 2+ weeks |
| GAP-M13 | Health       | Valhalla/OSRM not in `/health/ready`           | 4h       |
| GAP-M14 | Website      | Customer portal client-side auth gate          | 4h       |

---

## Architecture Violations

| ID    | Violation                            | masterrule            | Severity |
| ----- | ------------------------------------ | --------------------- | -------- |
| AV-01 | Business logic in `driver.py` router | §3.3                  | High     |
| AV-02 | Merchant → admin engine import       | §3 layered separation | High     |
| AV-03 | SQL in notification/order routers    | §3.3                  | Medium   |

**No violations found for:**

- Fleetbase adapter bypass (§8) ✅
- Browser-only booking state (§2) ✅
- Frontend Fleetbase HTTP (§7) ✅

---

## Compliance vs MASTERULE_COMPLIANCE_GAPS.md

Previous checklist marked several items "Done". This audit identified:

- **BW-C01** — not previously tracked; now fixed
- **Event catalog emissions** — still partial for reverse logistics
- **Phase 4/5 billing** — retail complete; NET/refunds partial

---

_Remediation plan: `ROADMAP.md`_
