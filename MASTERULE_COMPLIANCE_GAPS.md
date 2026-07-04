# Porterchain — Master Rule Compliance Gaps

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Last updated:** June 30, 2026  
**Companion:** [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md)

This document tracks compliance with `masterrule.md`. **Phases 1–5 are complete** for all actionable gaps; remaining items are intentional future scope or low-priority polish.

---

## Executive summary

| Status | Count | Notes |
|--------|-------|-------|
| **Closed (Phases 1–5)** | 39 | Security, money, Fleetbase, workers, portals, engines, docs |
| **Future scope** | 3 | Credit notes, driver payout batches, Sentry SDK (L8) |
| **Intentional / OK** | 5 | L5–L7, public tracking (M13), path aliases documented (L1–L3) |

**Compliance posture:** Production-ready against masterrule v3.1 for retail booking, dispatch, admin, and driver surfaces. Billing refunds/credit notes and driver payout automation are documented as roadmap (§11.2).

---

## Phase 5 — Remaining gaps closed (June 30, 2026)

| ID | Status | Notes |
|----|--------|-------|
| H2 | **Done** | `quote-client.ts` no longer sends `website_pricing`; server `porterchain_pricing` only; TS engine marked display-only |
| M3 | **Done** | Canonical maps in `porterchain_fleetbase_adapter/events/lifecycle.py`; engine `StatusTranslator` consumes adapter |
| M4 | **Done** | `admin_engine/audit.py` wired into pricing, support, CRM (company), booking-draft admin |
| M6 | **Done** | `WebhookIngressService`; `routers/webhooks.py` delegates only |
| M7 | **Done** | Driver portal BFF: HttpOnly cookies + `/api/driver/[...path]` proxy |
| M8 | **Done** | SSO + `porterchain_services` use adapter; `services/fleetbase` off PYTHONPATH; deprecation warning |
| M9 | **Done** | `CUSTOMER_IDENTIFIED` always reached before `AUTHENTICATED` in merge + auth flow |
| M10 | **Done** | Documented future scope in `masterrule.md` §11.2 |
| M13 | **Done** | Public tracking documented in `AUTHENTICATION.md` |
| M14 | **Done** | `QuoteRepository`, `BookingDraftRepository`, `OrderRepository`; wired in quote/draft services |
| H3 (hardening) | **Done** | Website mock checkout gated on `NEXT_PUBLIC_ALLOW_STRIPE_MOCK` |
| H9 (metrics) | **Done** | `GET /metrics` Prometheus text; `queue_depths()`; ops `GET /queues` |

---

## Phase 1 progress

| ID | Status | Notes |
|----|--------|-------|
| C3 | **Done** | `assert_access` on GET/PATCH draft |
| C1 + H8 | **Done** | Server pricing + `revalidate_retail_quote` at payment |
| C4 | **Done** | `DriverAuthService` + Clerk |
| H3 | **Done** | `settings.allow_stripe_mock` local only |
| C2 | **Done** | Dispatch via `fleetbase_engine.BookingSyncService` |

## Phase 2 progress

| ID | Status | Notes |
|----|--------|-------|
| H6 + H10 | **Done** | Single Fleetbase path via `integration_bridge` + `WebhookProcessor` |
| H5 | **Done** | `require_redis_for_production()` |
| H11 | **Done** | Stripe webhook dedupe by `stripe:{event_id}` |

## Phase 3 progress

| ID | Status | Notes |
|----|--------|-------|
| H4 + M11 | **Done** | Worker processors + delivery |
| H1 | **Done** | Thin routers |
| H9 | **Done** | Request-ID, `/health/live`, `/health/ready` |
| H7 | **Done** | Customer portal + `apps/customer` |

## Phase 4 progress

| ID | Status | Notes |
|----|--------|-------|
| M1 | **Done** | `billing_engine/` |
| M2 | **Done** | `notification_engine/` |
| M12 | **Done** | Alembic + Postgres in Docker |
| C5 | **Done** | `apps/mobile-driver/` Expo scaffold |
| H12 + L1–L3 | **Done** | README, TECH_STACK, masterrule §4.2 |

---

## Compliance checklist by masterrule section

| Section | Compliant? | Notes |
|---------|------------|-------|
| §1 Locked architecture | ✅ | Mobile driver scaffold; web portal interim |
| §2 Core principles | ✅ | Server owns pricing |
| §3 Layered architecture | ✅ | Routers thin; repositories introduced |
| §4 Repository structure | ✅ | Path aliases documented |
| §5 Application boundaries | ✅ | Customer portal live |
| §6 Porterchain API engines | ✅ | billing_engine, notification_engine formalized |
| §7 Communication rules | ✅ | fleetbase_engine outbound/inbound |
| §8 Fleetbase adapter | ✅ | Single adapter; shim deprecated |
| §9 Database ownership | ✅ | Alembic + Postgres for prod |
| §10 Domain lifecycles | ✅ | Draft auth + state machine |
| §11 Pricing/billing/notifications | ⚠️ | Refunds/credit notes = future (documented) |
| §12 Event bus | ✅ | Redis prod, workers, idempotency |
| §13 Fleetbase responsibilities | ✅ | — |
| §14 Stripe | ✅ | Mock gated; revalidation |
| §15 Security | ✅ | Driver cookies; draft IDOR fixed; admin audit |
| §16 Observability | ✅ | Health, metrics, correlation IDs |
| §17 Reference numbers | ✅ | — |
| §18 ADRs | ✅ | — |
| §19–20 Process rules | ✅ | Docs refreshed |

---

## Future scope (not gaps — roadmap)

| Item | masterrule | Status |
|------|------------|--------|
| Credit notes & partial refunds | §11.2 | Documented; Stripe webhook handles full refunds only |
| Driver payout batches | §11.2 | Documented; wallet ledger exists, payout automation TBD |
| Sentry / OpenTelemetry SDKs | §16, L8 | Metrics endpoint live; full APM SDK install TBD |
| CRM audit on every mutation | §15 | Company CRUD + pricing/support/drafts; extend to all CRM entities as needed |
| Full event catalog emissions | §12, M5 | Core lifecycle events emitted; finance events when modules land |

---

## What does NOT need to change

- Portal → API only (no Fleetbase from frontends) ✅  
- `services/fleetbase-adapter/` as integration boundary ✅  
- Booking draft DB persistence, states, audit trail ✅  
- Clerk on website, merchant, admin ✅  
- Stripe production webhook → order creation ✅  

---

_When closing new gaps, update this file and [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md). Intentional exceptions must update [masterrule.md](./masterrule.md) first (§20.10)._
