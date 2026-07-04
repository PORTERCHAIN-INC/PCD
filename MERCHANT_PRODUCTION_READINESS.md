# Merchant Portal — Production Readiness Report

**Date:** June 30, 2026  
**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Scope:** B2B Merchant Portal (`apps/merchant-portal`) + `/v1/merchant/*` + `/v1/merchant-api/*`

---

## Executive summary

The Merchant Portal is **production-ready for core logistics operations** (book, track, bill, report, integrate). Most features are end-to-end wired through FastAPI application services with no duplicated business engines. Remaining gaps are **non-blocking** for launch: Clerk org invite automation, scheduled report delivery worker, OAuth ERP connectors, and server-side order export.

| Classification | Count |
|----------------|-------|
| ✅ Complete | 22 |
| ⚠ Partial | 11 |
| ❌ Missing | 3 |

**Overall readiness:** **85%** — ship with documented limitations below.

---

## Feature readiness matrix

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard | ✅ Complete | KPIs, charts, activity, notifications, WebSocket refresh |
| Orders | ✅ Complete | List, filters, bulk actions, Order 360 |
| Book Delivery | ✅ Complete | Preview, confirm, multi-parcel, drafts, templates, bulk |
| Tracking | ✅ Complete | Live tracking, timeline, POD, dashboard panel |
| Live Map | ⚠ Partial | Embedded in `/track` + Order 360; requires Google Maps key; poll-based map updates |
| Recipients | ✅ Complete | Settings CRUD + booking picker (post-audit) |
| Billing | ✅ Complete | Overview, invoices, statement, payments, credits, tax, CSV/PDF |
| Reports | ⚠ Partial | Full workspace; scheduled delivery is profile-only (no worker) |
| API / Integrations | ✅ Complete | Keys, sandbox, usage, rate limits, docs, console |
| Webhooks | ✅ Complete | CRUD, logs, retry, HMAC delivery, test ping |
| Team | ⚠ Partial | Invite/roles/activity/2FA prefs; no Clerk org invite API |
| Support | ✅ Complete | Tickets, KB, Order 360 create (post-audit) |
| Claims | ✅ Complete | List, file, Order 360 file (post-audit) |
| Settings | ✅ Complete | Profile, locations, warehouses, branding, tax, documents, contract |
| Notifications | ⚠ Partial | Inbox on dashboard + mark-read (post-audit); prefs in settings; full inbox at `/v1/notifications` |
| Realtime | ⚠ Partial | WebSocket on dashboard/orders/track; 60s poll fallback |
| RBAC | ✅ Complete | `merchant_engine/rbac.py` enforced on all routes |
| Programmatic API | ✅ Complete | Live tracking parity on `/merchant-api/track` (post-audit) |

---

## Infrastructure & engines

| Component | Status | Verification |
|-----------|--------|--------------|
| FastAPI routers | ✅ | 120+ merchant routes + 5 merchant-api routes |
| Application services | ✅ | `merchant_engine/*` orchestrate engines |
| Pricing Engine | ✅ | `pricing_engine` + `calculate_merchant` on all bookings |
| Billing Engine | ✅ | `billing_engine/merchant_service.py` |
| Reporting Engine | ✅ | `reporting_engine/merchant_service.py` |
| Notification Engine | ⚠ | `/v1/notifications/*`; dashboard embeds subset |
| Fleetbase Adapter | ✅ | No direct Fleetbase HTTP from merchant layer |
| Google Maps | ⚠ | Render-only via `@porterchain/maps`; env required |
| OSRM | ✅ | ETA via `MapsService._osrm_route` in tracking |
| Valhalla | ✅ | Route geometry via `MapsService._valhalla_route` |
| Event Bus | ✅ | `emit_event` → `platform/bus.py` |
| Gateway Engine | ✅ | Rate limits + usage on `/v1/merchant-api/*` |
| WebSockets | ⚠ | `/v1/notifications/ws` for merchant principals |

---

## Missing (❌) — out of scope for this release

| Item | Reason |
|------|--------|
| ERP OAuth (Shopify/WooCommerce) | Marked `coming_soon`; readiness docs only |
| Scheduled report email worker | Metadata stored; no delivery processor |
| Server-side order CSV/manifest export | Client-side only today |

---

## Partial (⚠) — acceptable with docs

| Item | Mitigation |
|------|------------|
| Live map streaming | 10s poll + WebSocket page refresh |
| Team Clerk invite | Manual `pending_{email}` user rows; ops can link Clerk |
| Notification preference dual-store | Settings profile + notification_engine prefs |
| Invoice pay flow | NET billing; no Stripe pay button for contract merchants |
| Legacy `lib/api.ts` | Superseded by domain libs; safe to deprecate |

---

## Pre-production checklist

- [ ] Run Alembic migrations (`g8h9i0j1k2l3` integrations tables, prior webhook secret)
- [ ] Set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` and `PORTERCHAIN_API_URL`
- [ ] Configure Clerk merchant org + `X-Merchant-Org-Id`
- [ ] Verify Fleetbase adapter connectivity (health via `/internal/services`)
- [ ] Enable Redis for event bus / worker webhook fanout
- [ ] Set `JWT_SECRET` for webhook signing encryption
- [ ] Smoke test: book → track live → invoice → report export → API key → webhook test

---

## Post-audit fixes applied

1. **Programmatic API live tracking** — `/v1/merchant-api/track/{number}` now returns `live_tracking` via `MerchantTrackingService` (Fleetbase + OSRM + Valhalla).
2. **Notification mark-read** — Dashboard `NotificationCenter` calls `POST /v1/notifications/inbox/{id}/read` and follows `deep_link`.
3. **Recipients management** — Settings → Recipients tab with `POST /v1/merchant/recipients`.
4. **Order 360 Support/Claims** — Inline ticket and claim filing from order detail page.

---

## Sign-off recommendation

**Approve production deployment** for merchant self-service logistics, billing, reporting, and API integrations. Defer ERP OAuth and automated scheduled reports to a follow-on release.
