# Module Scorecard — Porterchain Platform

**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) (canonical doc).

**Reference:** `masterrule.md` §5 (Application boundaries)

**Legend:** ✅ Complete · ⚠️ Partial · ❌ Missing · 🔴 Architecture Violation · 🟡 Technical Debt

---

## Summary

| Status                 | Count                     |
| ---------------------- | ------------------------- |
| Complete               | 9                         |
| Partial                | 4                         |
| Missing                | 0                         |
| Architecture Violation | 1 (merchant→admin engine) |

---

## Portal Modules

| Module       | Port | Status      | API Engine                 | UI                     | RBAC                                    | Gaps                                        |
| ------------ | ---- | ----------- | -------------------------- | ---------------------- | --------------------------------------- | ------------------------------------------- |
| **Website**  | 3000 | ✅ Complete | `quotes`, `booking_drafts` | Marketing, book, track | Public + Clerk                          | Client pricing display-only (compliant §11) |
| **Customer** | 3004 | ⚠️ Partial  | `customers`, booking       | Dashboard, book, track | Clerk + access gate                     | Tracking map missing                        |
| **Merchant** | 3001 | ✅ Complete | `merchant_engine/*`        | 15+ portal pages       | `merchant_engine/rbac`                  | 🔴 Depends on `admin_engine` for orders     |
| **Driver**   | 3003 | ⚠️ Partial  | `driver_engine/*`          | Web portal 20 pages    | JWT cookie                              | Fat router debt; map viz gap                |
| **Admin**    | 3002 | ✅ Complete | `admin_engine/*`           | Ops control tower      | `admin_engine/rbac` + `AdminAccessGate` | CRM/Route Center UI removed (Phase 2)       |

---

## Business Modules

| Module                   | Status      | Service                            | Admin UI                  | Notes                                    |
| ------------------------ | ----------- | ---------------------------------- | ------------------------- | ---------------------------------------- |
| **Booking Workflow**     | ✅ Complete | `booking_engine/`                  | Booking drafts grid       | Critical draft race fixed                |
| **CRM (sales pipeline)** | ⚠️ Deferred | `collaboration_engine/crm_service` | — (admin CRM UI removed)  | Phase 2 — `/v1/admin/collaboration` only |
| **Orders**               | ✅ Complete | `admin_engine/orders_service`      | Grid + Order360           | Embedded map                             |
| **Operations**           | ✅ Complete | `control_tower_service`            | Dispatch board            |                                          |
| **Route Center**         | ❌ Removed  | —                                  | —                         | Fleetbase + Control Tower                |
| **Finance**              | ⚠️ Partial  | `finance_service`                  | Invoices grid/detail      | No PDF export                            |
| **Billing**              | ⚠️ Partial  | `billing_engine/`                  | Merchant NET views        | Credit notes roadmap §11.2               |
| **Pricing**              | ✅ Complete | `pricing_engine/` + library        | Admin tariffs + simulator |                                          |
| **Claims**               | ✅ Complete | `claims_service`                   | List + detail             | Refund events wired                      |
| **Support**              | ✅ Complete | `support_service`                  | Grid + detail             | Enterprise tickets                       |
| **Reports**              | ✅ Complete | `reports_service`                  | Charts + exports          |                                          |
| **Settings**             | ✅ Complete | `settings_service`                 | Settings center           |                                          |
| **Notifications**        | ⚠️ Partial  | `notification_engine/`             | Admin + inbox WS          | FCM log-only without creds               |
| **Live Map**             | ✅ Complete | `operations.py` WS                 | `LiveMapApp`              | Poll fallback                            |
| **Diagnostics**          | ✅ Complete | `diagnostics_service`              | System health/tests       |                                          |

---

## Engine Modules (API)

| Engine                 | Status     | Responsibility                                |
| ---------------------- | ---------- | --------------------------------------------- |
| `booking_engine/`      | ✅         | Quote, draft, payment, confirmation, tracking |
| `merchant_engine/`     | ✅         | B2B lifecycle, billing, bulk                  |
| `admin_engine/`        | ✅         | Ops, CRM, finance, claims, RBAC               |
| `fleetbase_engine/`    | ✅         | Sync, webhooks, retry queue                   |
| `driver_engine/`       | ⚠️         | Driver bridge; router too fat                 |
| `billing_engine/`      | ⚠️         | Ledger; refund events partial                 |
| `notification_engine/` | ⚠️         | Templates, delivery; FCM partial              |
| `pricing_engine/`      | ✅         | Bridge to pricing library                     |
| `route_center_engine/` | ❌ Removed | Use Fleetbase routes + Control Tower          |
| `gateway_engine/`      | ✅         | Merchant API key rate limits                  |

---

## Technical Debt by Module

| Module                  | Debt                          | Severity |
| ----------------------- | ----------------------------- | -------- |
| Merchant orders         | Imports `admin_engine`        | High     |
| Driver API              | Business logic in router      | High     |
| Customer tracking       | No embedded map               | Medium   |
| Finance                 | No PDF generation             | Medium   |
| Notifications           | Firebase credentials optional | Medium   |
| Website customer portal | Client-side access gate only  | Medium   |

---

## Module Readiness for Production

| Module                         | Production Ready?                        |
| ------------------------------ | ---------------------------------------- |
| Website booking (with webhook) | ✅ Yes (after Stripe webhook configured) |
| Merchant portal                | ✅ Yes                                   |
| Admin ops                      | ✅ Yes                                   |
| Customer portal                | ⚠️ After tracking map                    |
| Driver (web)                   | ⚠️ After router refactor                 |
| Mobile driver                  | ⚠️ 72% — EAS/Firebase/Clerk prod ops     |
| Mobile customer                | ⚠️ 62% — store assets, EAS, payment UI   |
| Finance PDFs                   | ❌ Not required for MVP dispatch         |

---

_Detailed gaps: `GAP_ANALYSIS.md` · Remediation plan: `ROADMAP.md` · Go/no-go: `PRODUCTION_READINESS_REPORT.md`_
---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
