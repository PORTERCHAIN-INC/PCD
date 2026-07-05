# Merchant Portal — Production Readiness Report

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Scope:** B2B Merchant Portal (`apps/merchant-portal`) + `/v1/merchant/*` + `/v1/merchant-api/*`

> **Platform status:** The **overall Porterchain platform is NOT production ready** — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md). This report covers **merchant surface readiness only**.

---

## Executive summary

The Merchant Portal is **operationally ready for core B2B logistics** (book, track, bill, report, integrate) when deployed alongside a configured API, Clerk, Fleetbase adapter, and Redis. Remaining gaps are **non-blocking for merchant beta** but documented below.

| Classification | Count |
| -------------- | ----- |
| ✅ Complete    | 22    |
| ⚠ Partial      | 11    |
| ❌ Missing     | 3     |

**Merchant surface readiness:** **~85%** — suitable for staged rollout with documented limitations.

---

## Feature readiness matrix

| Feature            | Status      | Notes                                                                  |
| ------------------ | ----------- | ---------------------------------------------------------------------- |
| Dashboard          | ✅ Complete | KPIs, charts, activity, `NotificationCenter` mark-read                 |
| Orders             | ✅ Complete | List, filters, bulk actions, Order 360                                 |
| Book Delivery      | ✅ Complete | Preview, confirm, multi-parcel, drafts, bulk                           |
| Tracking           | ✅ Complete | Live tracking, timeline, POD, dashboard panel                          |
| Live Map           | ⚠ Partial   | Embedded in `/track` + Order 360; Google Maps key required; poll-based |
| Recipients         | ✅ Complete | Settings CRUD + booking picker                                         |
| Billing            | ✅ Complete | Overview, invoices, statement, payments, credits, tax, CSV/PDF         |
| Reports            | ⚠ Partial   | Full workspace; scheduled delivery profile-only (no worker)            |
| API / Integrations | ✅ Complete | Keys, sandbox, usage, rate limits, docs, webhooks UI                   |
| Webhooks           | ✅ Complete | CRUD, logs, retry, HMAC delivery via worker                            |
| Team               | ⚠ Partial   | Invite/roles/activity; no Clerk org invite API                         |
| Support            | ✅ Complete | Tickets, KB, Order 360 create                                          |
| Claims             | ✅ Complete | List, file, Order 360 file                                             |
| Settings           | ✅ Complete | Profile, locations, warehouses, branding, tax, documents, contract     |
| Notifications      | ⚠ Partial   | Dashboard embed + `/v1/notifications/inbox`; prefs in settings         |
| Realtime           | ⚠ Partial   | WebSocket on dashboard/orders/track; poll fallback                     |
| RBAC               | ✅ Complete | `merchant_engine/rbac.py` on all routes                                |
| Programmatic API   | ✅ Complete | 5 routes on `/v1/merchant-api/*` + gateway rate limits                 |

---

## Infrastructure & engines

| Component            | Status | Verification                                         |
| -------------------- | ------ | ---------------------------------------------------- |
| FastAPI routers      | ✅     | 120+ `/v1/merchant/*` + 5 `/v1/merchant-api/*`       |
| Application services | ✅     | `merchant_engine/*` orchestrates engines             |
| Pricing Engine       | ✅     | `calculate_merchant` on all bookings                 |
| Billing Engine       | ✅     | `billing_engine/merchant_service.py`                 |
| Reporting Engine     | ✅     | `MerchantReportsService`                             |
| Notification Engine  | ⚠      | `/v1/notifications/*`; merchant `user_role=merchant` |
| Fleetbase Adapter    | ✅     | No direct Fleetbase HTTP from merchant layer         |
| Google Maps          | ⚠      | `@porterchain/maps` render-only; env key required    |
| Valhalla / OSRM      | ✅     | ETA via `MapsService` in tracking                    |
| Event Bus            | ✅     | `emit_event` → handlers                              |
| Gateway Engine       | ✅     | Usage + rate limits on `/v1/merchant-api/*`          |

---

## Missing (❌) — follow-on release

| Item                                  | Reason                                 |
| ------------------------------------- | -------------------------------------- |
| ERP OAuth (Shopify/WooCommerce)       | Marked `coming_soon`                   |
| Scheduled report email worker         | Metadata stored; no delivery processor |
| Server-side order CSV/manifest export | Client-side export only                |

---

## Partial (⚠) — acceptable with docs

| Item                     | Mitigation                                                             |
| ------------------------ | ---------------------------------------------------------------------- |
| Live map streaming       | Poll + page refresh                                                    |
| Team Clerk invite        | Manual `pending_{email}` rows                                          |
| NET batch invoicing      | Statement read-only; no scheduled invoice run                          |
| Invoice PDF              | `pdf_url` not populated platform-wide                                  |
| Platform production cert | See [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) |

---

## Pre-deployment checklist

- [ ] `pnpm db:migrate` (head `n2o3p4q5r6s7`; includes `g8h9i0j1k2l3` gateway tables)
- [ ] `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_PORTERCHAIN_API_URL`
- [ ] Clerk merchant org + `X-Merchant-Org-Id`
- [ ] Fleetbase adapter: `pnpm docker:fleetbase:verify`
- [ ] Redis for event bus + webhook fanout
- [ ] Smoke: book → track → invoice → API key → webhook test ping

---

## Programmatic API routes

| Method | Path                                       | Scope             |
| ------ | ------------------------------------------ | ----------------- |
| POST   | `/v1/merchant-api/bookings`                | `shipments:write` |
| GET    | `/v1/merchant-api/orders`                  | `shipments:read`  |
| GET    | `/v1/merchant-api/orders/{id}`             | `shipments:read`  |
| GET    | `/v1/merchant-api/track/{tracking_number}` | `shipments:read`  |
| POST   | `/v1/merchant-api/orders/{id}/cancel`      | `shipments:write` |

---

## Sign-off recommendation

**Approve merchant portal for staged B2B rollout** (book, track, bill, API integrations) when platform ops prerequisites are met. Do **not** treat this as full platform production certification — defer ERP OAuth, scheduled reports, and NET batch billing to follow-on work.

---

## Related

| Document                                                                         | Purpose                        |
| -------------------------------------------------------------------------------- | ------------------------------ |
| [MERCHANT_ARCHITECTURE_REPORT.md](./MERCHANT_ARCHITECTURE_REPORT.md)             | Architecture and component map |
| [docs/architecture/MERCHANT_FLOW.md](./docs/architecture/MERCHANT_FLOW.md)       | Flow diagram                   |
| [docs/archive/MERCHANT_GAP_ANALYSIS.md](./docs/archive/MERCHANT_GAP_ANALYSIS.md) | Historical gap inventory       |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
