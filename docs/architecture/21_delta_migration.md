# 21 — NOW vs PLANNED delta + migration order

| Layer       | NOW (as-built, files 01–10)                   | PLANNED (12–20)                                                | Step  |
| ----------- | --------------------------------------------- | -------------------------------------------------------------- | ----- |
| Context     | portals, Shopify, Stripe, Interac             | + WhatsApp, cooler logger, agents                              | 6     |
| Containers  | api, worker, Redis lists + Streams, no outbox | outbox → Kafka (Redpanda); PydanticAI agents in DBOS workflows | 2, 5  |
| Data        | 04 ER; POD 365 d; no BOL/temp/approvals       | 14 additions; POD ≥ 6 y                                        | 1, 3  |
| Modules/API | 06 drift (20 handlers not in snapshot)        | regenerate OpenAPI; new endpoints (15)                         | 2     |
| Interface   | 07, 20 redirect stubs                         | 16 IA, approvals inbox                                         | 7     |
| States      | free-string offer/route status                | enums + maps (17)                                              | 3     |
| Authz       | staff roles only                              | agent identities + approve_* (17)                              | 5     |
| Async       | 22 sweeps, 4 unused events                    | workflow timers; outbox                                        | 4     |
| Compliance  | 19 table                                      | all B                                                          | 1 → 8 |

Order (each step passes the six-check gate, `NEW_ADDITION_GATE.md`, and local rehearsal L13):

1. **Legal blockers first:** POD retention ≥ 6 y (A01), DG hard refuse (L3), BN RT validation (A07), claims deadlines, declared-value disclosure.
2. Regenerate OpenAPI snapshot; local Redpanda (29092) + DBOS (week 1); `event_outbox` + relay to Kafka topics (week 4).
3. Enums/transition maps; `temp_readings`, `contract_of_carriage` (BOL), `vehicle_compliance_docs`, `driver_pay_statements`, `driver_access_notices`.
4. Replace all 22 sweeps with DBOS scheduled workflows / Kafka consumers in weeks 6–7 (L18, L20); delete the worker polling loop.
5. Agent identities in SpiceDB; approvals table; PydanticAI agent runtime (in DBOS) at autonomy rung 0.
6. WhatsApp webhook + CASL consent gate.
7. Admin/super-admin IA reorg; delete redirect stubs.
8. Box truck go-live only after CVOR + cargo insurance + BOL done; DPWRA features before contractor scale-up.

Schedule (L24): 14 build + 8 proven weeks, a 2-week slip from 12 + 8 caused by Kafka (L19, about 1 week: broker, outbox relay, topics, consumers, week-13 hardening) and moving all 22 sweeps (L20, about 1 week). All 11 S1 fixes by week 6 (L21); sweeps weeks 6–7; Kafka hardening week 13; rehearsal + pilot week 14; proven window weeks 15–22. Box truck price from Ravi by week 3; truck runs only after BOL, CVOR and cargo insurance (L23).

## Existing features kept (as-built features the plan must not drop)

Added after the now-vs-planned removal review. Each row is working or wired today and stays in Phase 1 unless Ravi decides otherwise. Weeks follow the 14 + 8 schedule (L24).

| #   | Feature (users)                                                                                                                                       | Evidence                                                            | Planned home                                                                                                                                                                       | Week                         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| 1   | Native driver app, Expo/React Native, iOS build 22 + Android (driver)                                                                                 | `apps/mobile-driver/app.json`, `App.tsx`                            | Kept; GPS → Redis live feed unchanged (not via Kafka, L19); push via existing FCM/APNs config; job/stop events from `pc.dispatch.v1` consumer; EAS releases gated by L13 rehearsal | 6–7 (consumer), 14 (release) |
| 2   | Native customer app, Expo, 8 screens (customer)                                                                                                       | `apps/mobile-customer/src/screens/*`                                | Kept; book/track/alerts read the same quote API and `pc.notifications.out.v1`                                                                                                      | 7, 14                        |
| 3   | Driver web portal: timesheets, wallet, training, emergency, shift, performance, monitoring policy, communications, earnings (driver)                  | `apps/driver-portal/src/app/*` (07)                                 | Kept; earnings/wallet show DPWRA pay statements (A10); monitoring policy is the ESA notice                                                                                         | 5–6                          |
| 4   | Merchant portal: API keys (`/api`), referrals, team, reports, CSV upload (`/routes?tab=csv`), track, onboarding, how-we-price (merchant)              | `apps/merchant-portal/src/app/*` (07)                               | Kept; how-we-price and rate-card tab read the new rate card versions; API keys/OAuth unchanged                                                                                     | 2 (pricing), else unchanged  |
| 5   | Customer web: send/book, invoices, tracking (customer, guest)                                                                                         | `apps/customer/src/app/*`                                           | Kept; quotes show margin band (L2 amended, warn-only); Stripe for retail (L10)                                                                                                     | 2                            |
| 6   | Admin pages missing from first draft of 16: blog, blog authors, booking drafts, leads calendar/attribution/agent/today, notification delivery (admin) | `apps/admin/src/app/(ops)/*`                                        | Added to 16 menu (Sales; Content + comms)                                                                                                                                          | 11                           |
| 7   | Impersonation of merchant/customer/driver (super-admin)                                                                                               | `routers/admin/impersonation.py:26,54`; `/impersonate` in 3 portals | Kept for humans only; guard in 17                                                                                                                                                  | 8                            |
| 8   | Website: delivery cost calculator, `/rates`, quote, track + manage, developer docs, careers, vehicle partner, 72 pages (public, website)              | `website/src/app/[locale]/*`                                        | Kept; calculator, `/rates`, quote read the live `rate_card_versions` via the public quote API, no hard-coded prices                                                                | 2–3                          |
| 9   | Promotions / promo codes (customer, merchant)                                                                                                         | `admin_models.py:194`; `booking_drafts.promo_code`                  | Kept; in 14/15 with max_uses, scope, margin band                                                                                                                                   | 2                            |

Merchant card payment (checked in code 2026-10-28): merchants **cannot start a card payment today**. No merchant checkout endpoint or Pay-by-card UI exists; only remnants: `stripe_receipt_url` display (`schemas_merchant.py:248`, `merchant-portal/src/lib/billing.ts:90`), a stale comment claiming Stripe Checkout from the invoice page (`merchant_engine/invoice_reminder.py:129`), Stripe ledger webhook (`billing_engine/settlement_service.py:82`) and method label (`merchant_engine/billing_views.py:40`). L10 (merchants pay by Interac) removes nothing; clean the remnants with A26. Not a Ravi decision.

## Margin rule change (Ravi, 2026-10-28; amends L2, replaces the hard floor in A06)

Quotes are never blocked for margin. Margin ≥ 50 % = green; < 50 % = yellow warning; ≤ 35 % = red: alert to admin, shown on the quote, admin pricing and Today views, and logged. A06 fix becomes "compute and show margin band on every quote, alert on red", week 2. `REFUSED` stays only for outside 150 km and the goods gate (L1, L3).
