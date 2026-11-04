# 16 — PLANNED admin + super-admin information architecture

> **SUPERSEDED (kept for history, not deleted).** This pre-Phase-0 plan is replaced by 75 (ops console IA, D-75-1). Start at [00_PHASE0_MASTER.md](00_PHASE0_MASTER.md); where this file disagrees, the master and its locked decisions (L1–L36) win.

```mermaid
flowchart LR
  subgraph ADMIN[Admin - daily ops]
    T[Today: queue, exceptions, approvals inbox]
    D[Dispatch: plan, live, fleet, box truck, cooler runs]
    O[Orders + Claims]
    A[Accounts: merchants, customers, duplicates]
    S[Sales: booking drafts, leads, today, pipeline, calendar, attribution, lead agent, WhatsApp inbox]
    F[Finance: cash, invoices, credit notes, payments, driver pay, GST/HST, reports]
    SP[Support: tickets]
    CO[Content + comms: blog, blog authors, notifications, notification delivery]
  end
  subgraph SUPER[Super-admin - platform]
    SY[System: health, services, diagnostics]
    AG[Agents: runs, autonomy ladder, kill switch]
    CP[Compliance: retention, privacy requests, breach log, consent, CVOR/insurance expiry]
    ST[Settings: margin bands (50 % / 35 %), spend caps, approval caps, tax registration]
    US[Staff + roles (SpiceDB)]
    IN[Insights: investor/visitor metrics]
  end
```

Rules: one nav source generated from `schema.zed` permissions; every page appears in exactly one group; no redirect stubs (301 at Caddy); finance sub-pages promoted into the group; approvals are one inbox for the six human cases (L15–L17).

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
