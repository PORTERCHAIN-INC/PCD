# 00 — PorterChain Phase 0 master plan (single entry point)

Updated 29 Oct 2026 (America/Toronto). This file is the one place to start. It summarises every decision and points to the doc that holds the detail. Where any doc (00–83, 98) or Page disagrees with this file, this file and the locked decisions in §2 win, and the other text gets fixed (change rule, §2 end).

Mirrored on the Page "PorterChain Phase 0 + Phase 1: the strict plan" in the same section order.

## 1. Goal and scope freeze

- **Goal:** in 12 weeks, refine the existing PCD system until it is precise, clean, free/self-hosted and store-approved, with no agentic mode (`FEATURE_AI=false`). Then the pilot merchant runs live, human-run (L31, L32, D-P0-1).
- **In scope (frozen):**
  - vendor replacements (Clerk → Keycloak, Doppler → SOPS, Sentry → GlitchTip, Twilio → push + email + TOTP, Google Maps → MapLibre + PMTiles + Photon);
  - merchants on Interac only, with Stripe kept for retail customers;
  - routing (Valhalla + VROOM) and the ops console rebuild;
  - database reorganisation;
  - dead-code removal and the S1 fixes;
  - hybrid deployment;
  - the Trust & Help Centre;
  - the business-ready model for every business type (L35);
  - guided driver flows (doc 82), pricing admin (72 §9), the core model (doc 83) and login (L36);
  - both iOS apps in the App Store, and the Shopify custom app on the pilot store.
- **Out of scope (Phase 1 or later):** local LLMs and agents, Langfuse, RAG, the WhatsApp agent, the box truck build and BOL (A09), cooler runs, the pharmacy niche going live, partners (broker model), and the Google Play release. Phase 2 covers Zapier, NetSuite, owned fleet and heavy trucks.
- **Freeze rule:** nothing enters scope unless it passes the six-check gate ([NEW_ADDITION_GATE.md](NEW_ADDITION_GATE.md)) and Ravi adds an L-number.

## 2. Locked decisions

The full wording is on the strict plan Page, section 2. The table below is the short form; the "Detail" column points to the doc.

| #   | Decision (short)                                                                                                                                          | Detail             |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| L1  | Service area Toronto + 150 km                                                                                                                             | 72                 |
| L2  | Margin 50 % target, warn-only bands: green ≥ 50 %, yellow < 50 %, red ≤ 35 %; quotes are never blocked                                                    | 72 §8              |
| L3  | Medical cooler runs in Phase 1. Excluded: all dangerous goods incl. UN3373, and white-glove. Controlled substances only via the pharmacy profile (D-70-4) | 70 §7a, 20         |
| L4  | Drivers are contractors first, employees later                                                                                                            | 49, 54             |
| L5  | Box truck with a public price. Amended by L30/L34: short-term rental, prep pack behind `FEATURE_BOX_TRUCK=false`                                          | 56                 |
| L6  | WhatsApp orders in Phase 1, amended by L27 (free app only)                                                                                                | 27                 |
| L7  | 21 department agents under 3 core agents (Phase 1)                                                                                                        | 18, 43             |
| L8  | Legal name Porterchain Inc.                                                                                                                               | 49                 |
| L9  | Evolve PCD; keep Python; Keycloak (L26/L36)                                                                                                               | 60                 |
| L10 | No COD. Merchants pay by Interac; retail and guests pay by Stripe                                                                                         | 60 §13.5           |
| L11 | Ontario and CRA rules apply                                                                                                                               | 20, 68             |
| L12 | Six-check new-addition gate                                                                                                                               | NEW_ADDITION_GATE  |
| L13 | Full local rehearsal before anything goes live                                                                                                            | 60 G17             |
| L14 | PydanticAI inside DBOS; DSPy offline; self-hosted Langfuse (Phase 1)                                                                                      | 43, 27             |
| L15 | Three core agents: Goal, Orchestration, Task                                                                                                              | 18                 |
| L16 | Department agents as typed roles; one framework                                                                                                           | 18                 |
| L17 | Autonomy by default; human approval in six cases only                                                                                                     | Page, Phase 1 ref  |
| L18 | DBOS is the only durable store                                                                                                                            | 60                 |
| L19 | Redpanda + Postgres outbox (Phase 0, D-P0-2)                                                                                                              | 60, 83 §1.3        |
| L20 | All 22 polling sweeps move to DBOS or Kafka (Phase 0 weeks 7–8)                                                                                           | 31, 60             |
| L21 | All S1 audit fixes before the pilot                                                                                                                       | 60 G16             |
| L22 | $100 auto-refund/match cap                                                                                                                                | 73                 |
| L23 | Autonomy bar 99 % over 500 jobs; box truck only after BOL, CVOR and insurance                                                                             | 56, 80             |
| L24 | Schedule superseded by L31/L32: Phase 0 is 12 weeks, then Phase 1 is 8 build + 8 proven weeks                                                             | §11                |
| L25 | No paid AI; open-weight models in-house (Phase 1)                                                                                                         | 27                 |
| L26 | Nothing paid except the allowed list (Apple, DigitalOcean, ZeptoMail, Shopify, payment fees, registrations, Play, domains)                                | 30                 |
| L27 | Free WhatsApp Business app only; a human sends                                                                                                            | 27                 |
| L28 | Hybrid deployment: droplet is the source of truth for business users; Ubuntu for admin and AI; Oracle as fallback                                         | 28, 62             |
| L29 | Interac by bank-email parsing; phone GPS; drivers' own phones; PC-YYMM-XXXXXX IDs; modular monolith                                                       | 29, 33, 55         |
| L30 | Manual checks; SOPS; unlisted Shopify app; free pen testing; Ravi is on-call (backup named privately); rentals; 10+ drivers                               | 56                 |
| L31 | Phase 0 before Phase 1, gates G1–G21 plus G-INS                                                                                                           | 60                 |
| L32 | Pilot at the end of Phase 0; Valhalla + VROOM; Play in Phase 1; Shopify carrier rates, no Shopify Billing                                                 | 60 §12–13          |
| L33 | Trust & Help Centre (G18), EN/FR, policy versions and consent records                                                                                     | 68                 |
| L34 | No insurance yet, hard gate G-INS; box truck as a prep pack; broker model built in Phase 1; no retail cancellation fee                                    | 56, 20             |
| L35 | Business-ready Phase 0: one Organisation model plus operating profile, one pricing engine, tickets, integrations, ops IA, G19–G21                         | 70–76              |
| L36 | Login: self-hosted Keycloak with Google, Sign in with Apple, email+password and passkeys (details in §7)                                                  | 74 §2–3, 60 wk 1–2 |

Further decisions recorded:

- D-72-2 is decided: rate card v1, XS GTA $17 (Z2 +$15, Z3 +$30). See 72 §8.
- Pricing admin: Standard is the default and Custom is set per merchant. See 72 §9.
- Interim decisions I82-1..6 are in 82 §0.
- D-P0-1..7 are in 60 §12.
- D-70-1..4, D-72-1/3/4 and D-75-1 are in 77.

**Change rule:** any text that disagrees with this table is wrong and gets fixed.

## 3. Segments and phases

| Segment                                           | Phase                                                              | Doc        |
| ------------------------------------------------- | ------------------------------------------------------------------ | ---------- |
| Shopify merchants                                 | P0 pilot (Kaylulu; PCDC is the test store)                         | 24, 74 §2  |
| Local shops (bakery, florist, gift, pet, candles) | P0 pilot                                                           | 70, 81     |
| Retail customers (web + iOS)                      | P0                                                                 | 25, 74 §3  |
| Pharmacy                                          | First Phase 1 niche: designed and tested in P0, live in P1 (I82-2) | 70 §7a, 82 |
| Warehouse / 3PL                                   | Parcels P1, pallets P2                                             | 70, 74     |
| Courier / logistics partners                      | P1, with insurance certificates (L34, I82-5)                       | 56, 74     |
| Import/export / CHA                               | Released goods only, domestic leg (I82-4)                          | 70 §2.3    |
| Heavy trucks (> 4,500 kg)                         | Not until CVOR (I82-3)                                             | 80         |

Phases: **Phase 0** runs 12 weeks (§11). **Phase 1** runs 8 build weeks plus an 8-week proven window (Page, Phase 1 reference). **Phase 2+** follows.

## 4. Core model

Canonical source: [83](83_core_model_and_ux_blueprint.md) §1, with the ER diagram rendered in `rendered_l35/83_0.svg`.

- **Profile architecture:** organisation + business type + operating profile + capability/compliance packs + credentials (70, I82-6).
- **One order:** `ordering.orders` with `public_id` PC-YYMM-XXXXXX (check digit). The customer's own keys go in `platform.external_refs`, unique on (org_id, kind, value), with idempotent upserts.
- **One timeline:** `platform.events` is append-only and is the single source. The outbox relays it to Redpanda.
- **Fixes and rules:** 83 §1.5 resolves eleven duplicates and naming clashes (for example `osd_claims` becomes `ordering.claims`). Soft delete, audit and privacy rules are in 83 §1.4.
- **Lifecycle:** 14 stages per business type are in 81. Documents and capabilities per type are in 70 §2.2, and identifiers in 70 §2.3.

## 5. Personas and UX

- **Roles:** super admin, admin/ops, finance, merchant owner/staff, Shopify merchant, retail customer, driver, partner (P1). The screen map per role, with the top 5 flows and their tap counts, is in 83 §3.
- **UX principles:** in 83 §2. Examples: just-in-time asks, a 4-field sign-up, a quote in under 2 minutes, EN/FR, and WCAG 2.2 AA (G8, doc 53).
- **Driver:** one persona on web and mobile. It has five areas (Today, Job, Pay, Inbox/Help, Me). Server-driven wizards come from required documents plus packs, and there is one offline queue. Driver data is kept secret: need-to-know payloads, in-app chat or an audited phone release per tap, and expiry 2 h after the job. See 82.
- **Ops console IA (D-75-1):** Today, Orders, Dispatch, Network, Customers & Orgs, Billing, Support, Insights, Settings. See 75.
- **Onboarding:** progressive (71). Support works through tickets with P1–P4 targets (73).

## 6. Pricing

- **One engine:** `pricing_engine.get_pricing_service()`. Price = zone + size band on dimensional weight (L×W×H/5000) + upfront add-ons. There is no drip pricing, and margin bands follow L2 (72).
- **Standard rate card v1 (D-72-2):**

  | Band | Price |
  | ---- | ----- |
  | XS   | $17   |
  | S    | $18   |
  | M    | $26   |
  | L    | $49   |
  | XL   | $129  |
  | P    | $95   |
  - Zone surcharges: Z2 +$15, Z3 +$30 (so XS is $32 in Z2 and $47 in Z3).
  - 2-person add-on: $60.
  - Kaylulu's contract is unchanged.

- **Pricing admin (72 §9, 75 §4):**
  - Standard is the default until an admin switches a merchant to Custom.
  - Custom is one screen with presets, a live price and margin preview, and "send quote now" (72 h quote).
  - Every change is versioned, has guardrails and is audited.
  - Per-order adjustment requires a reason.
- **Same price on every channel:** Shopify carrier rates (plus the flat-rate fallback, which is a code gap to fill), the website, the API, the portal and invoices (the pinned quote price) must match to the cent (A-PRA-11).
- **Economics:** doc 79 (break-even 3/12/20 stops a day).

## 7. Login (L36)

- **Customers and merchants (web):** self-hosted Keycloak with Google, Sign in with Apple, email+password and passkeys.
- **Shopify embedded app:** session token only; no login, OTP or CAPTCHA in the iframe (74 §2, G20).
- **iOS apps:**
  - Sign in with Apple is **mandatory** (guideline 4.8) whenever Google is offered.
  - In-app account deletion.
  - A permanent reviewer account with no OTP or CAPTCHA (74 §3, G21).
- **Drivers:** invite-only accounts, plus a reviewer demo driver with sandbox jobs.
- **Admin and super admin:** TOTP is required. There is no OTP or CAPTCHA in normal login.
- **Bot defence:** Cloudflare Turnstile is invisible and shown only on risk signals, together with rate limits and Keycloak brute-force protection.
- **Schedule:** a minimal Keycloak customer/driver realm goes live in weeks 1–2. The web cut-over follows in weeks 4–5, and Clerk is removed in week 6 (60 §4).

## 8. Compliance and legal

- **Rulebook:** 20. Trust & Help, policies and rules R-01..R-21 are in 68. Legal drafts are in 49; they need lawyer review in weeks 5–6 and French legal review in weeks 7–8. They are not legal advice.
- **Identifiers and documents (70 §2.3):** a BOL is required under O. Reg. 643/05 when a shipment is over 45 kg and leaves the municipality. Proof of cargo insurance must be carried in the vehicle. Released goods are recorded via the CAD.
- **Vehicles (80):** DVIR on rentals over 4,500 kg; a phone HOS log; no ELD for rentals of 30 days or less; CVOR before any heavy truck.
- **Pharmacy (70 §7a):** the controlled-substance handling profile, per Health Canada CS-GD-022.
- **Privacy:** PIPEDA and CASL. The privacy officer is Ravi Chauhan (privacy@porterchain.com).
- **G-INS:** no paid delivery, including the Kaylulu pilot, until commercial auto (or courier cover), hired/non-owned auto, cargo and CGL are bound and the certificates are in admin.

## 9. Ops and lifecycle

- Order lifecycle: 81. Guided pickup and delivery flows: 82. Vehicle compliance: 80.
- Runbooks: 52. Incidents: 39. Monitoring: 36. Backups and DR: 35. Secrets: 37 (SOPS).
- On-call: Ravi is primary, with quiet hours 22:00–07:00 and safe mode after 30 minutes. A backup is named, and their contact is held privately by Ravi.
- Routing: Valhalla + VROOM. The fallback chain is Oracle, then haversine ×1.35 flagged as an estimate (60 §13).

## 10. Metrics

| Metric                   | Target / rule                    | Doc      |
| ------------------------ | -------------------------------- | -------- |
| On-time                  | 98 %                             | Page §10 |
| Mis-delivery             | ≤ 1 per 10,000                   | Page §10 |
| Proof of delivery        | 100 %                            | 82       |
| Margin                   | 50 % target, warn-only bands     | 72       |
| Route contribution (GTA) | $96.75/day (49.8 %)              | 79       |
| Break-even               | 3 / 12 / 20 stops/day            | 79       |
| Ticket targets           | P1–P4 response and resolve times | 73       |
| Engineering              | G1–G13 numbers in CI             | 60 §2    |

The DSO target is open (§13).

## 11. Schedule: 12 weeks, gates G1–G21 + G-INS

| Wk  | Main work (detail: 60 §4)                                                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Top priority: Shopify review fix and the L36 Keycloak customer/driver realm; reviewer accounts; Turnstile on risk only. Also CI baseline scans, SOPS, and dead modules batch 1 |
| 2   | Enums + CHECKs, S1 fixes, margin bands, Alembic baseline, 72 h quote TTL; review fixes finished                                                                                |
| 3   | GlitchTip; FEATURE_AI=false; MapLibre + PMTiles + Photon; organisation model starts (weeks 3–5)                                                                                |
| 4   | Keycloak staff/merchant realms; outbox + relay; Redpanda + DBOS                                                                                                                |
| 5   | Keycloak web cut-over; Twilio → push + email + TOTP; lawyer review                                                                                                             |
| 6   | Keycloak apps finalised and Clerk removed; merchants on Interac only; DBOS workflows; pricing and pricing admin (weeks 6–8)                                                    |
| 7   | Sweeps batch 1; routing benchmark + service; French legal review                                                                                                               |
| 8   | Sweeps batch 2; ops console rebuilt (weeks 8–9); support + integrations                                                                                                        |
| 9   | Domain schemas, CRM merge, admin IA, Leads, metrics tables                                                                                                                     |
| 10  | Hybrid deployment; WCAG fixes; TestFlight beta; acceptance suite (weeks 10–12)                                                                                                 |
| 11  | App Store review; Play organisation account; Shopify custom app; failover drills; load test                                                                                    |
| 12  | G1–G21 in one CI run; full rehearsal; pilot merchant live, human-run (only after G-INS for paid runs); exit review                                                             |

**Gates (60 §2):**

| Gate(s)   | What it checks                      |
| --------- | ----------------------------------- |
| G1–G3     | Dead code and duplication           |
| G4–G6     | Lint, types, tests and API contract |
| G7        | Performance                         |
| G8        | Accessibility                       |
| G9        | Security                            |
| G10       | Vendor removal                      |
| G11       | Payments split                      |
| G12       | Polling                             |
| G13       | Database                            |
| G14       | Store approval                      |
| G15       | Failover drills                     |
| G16       | Audit                               |
| G17       | Rehearsal                           |
| G18       | Trust & Help                        |
| G19       | Business journeys                   |
| G20       | Shopify review                      |
| G21       | Mobile review                       |
| **G-INS** | Insurance, before any paid delivery |

A red gate extends Phase 0. Phase 1 never starts on a red gate.

## 12. Tests index (doc 76)

| §    | IDs                                                    | Area                                                   |
| ---- | ------------------------------------------------------ | ------------------------------------------------------ |
| 2–8b | A-SHP, A-WH, A-SS, A-CP, A-LP, A-SC, A-CHA, A-RT, A-FR | Journeys per business type                             |
| 9    | A-PR, A-OP                                             | Pricing, operating profile                             |
| 10   | A-SHR-01..07                                           | Shopify review (G20)                                   |
| 11   | A-APR-01..08                                           | Mobile review incl. Sign in with Apple, deletion (G21) |
| 12   | A-OPS                                                  | Ops console                                            |
| 13   | A-FIN                                                  | Business metrics (79)                                  |
| 14   | A-DOC                                                  | Documents & capabilities                               |
| 15   | A-ID                                                   | Identifiers & milestones                               |
| 16   | A-VC                                                   | Vehicle compliance                                     |
| 17   | A-LC                                                   | Order lifecycle                                        |
| 18   | A-GF-01..10, A-PAR-01..04                              | Guided job flows, driver web/mobile parity             |
| 19   | A-PRA-01..12                                           | Pricing admin, identical price on every channel        |
| 20   | A-CM-01..06, A-UX-01..04                               | Core model, UX                                         |

Engineering gates are measured in CI (60 §2). Traceability of every Ravi ask is in 77.

## 13. Needed from Ravi

1. **Insurance quotes (pilot blocker, G-INS):** commercial auto or courier cover, hired/non-owned auto, cargo and CGL, from a licensed broker.
2. **Lawyer pack:**
   - docs 49 and 68 drafts;
   - contractor status;
   - Partner Agreement (subcontracting, non-solicitation U82-1);
   - pharmacy delivery agreement (U-70-1);
   - rental commercial-use terms;
   - carrier-vs-broker status;
   - B2B cancellation clause.
3. **Kaylulu:** pilot start date and expected daily volume. Also their Shopify plan (carrier-calculated rates need Advanced/Plus or the add-on).
4. **Accountant:** chart of accounts and the HST/CRA records setup (79), the T4A process for contractors, and the DSO target.
5. **WhatsApp:** the business number for the free WhatsApp Business app (L27).
6. **Social keys:** Meta (Facebook/Instagram) and YouTube app credentials for Leads (78), held in SOPS and never in docs.
7. **Repo and code go-ahead:** approval to start Phase 0 code changes (weeks count from it), plus the one-time CI runner token.

## 14. Risks

| Risk                                | Control                                                            | Doc        |
| ----------------------------------- | ------------------------------------------------------------------ | ---------- |
| Keycloak cut-over touches 583 files | Portal-by-portal flags, identity map, dual-run                     | 60 §11, 34 |
| Apple or Shopify rejection          | L36 login; reviewer accounts; G20/G21 tests; TestFlight in week 10 | 74         |
| No insurance                        | G-INS hard gate; unpaid PCDC test runs only                        | 20, 56     |
| Solo on-call                        | Quiet hours, safe mode, private backup contact                     | 52         |
| Gates never all green               | Numeric gates; exceptions only as written L-numbers                | 60         |
| Contractor misclassification        | Lawyer review before pilot                                         | 49         |
| Pharmacy custody failure            | P1 only, after P0 tests; custody log, lockbox, training            | 70 §7a     |
| Driver data leak                    | Need-to-know payloads, audited release, SpiceDB field checks       | 82 §3      |

## 15. Doc index

| Range            | Content                                                                                                     | Status                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 00               | Drawing-set index                                                                                           | Current (index)                               |
| 00_PHASE0_MASTER | This file                                                                                                   | **Entry point**                               |
| 01–11            | As-built system (now)                                                                                       | Current (as-built reference)                  |
| 12–18, 21–23     | Pre-Phase-0 planned designs                                                                                 | **Superseded**, banners point to replacements |
| 19–20            | Compliance layer, operational/legal rulebook                                                                | Current                                       |
| 24–26            | Shopify app, customer mobile, driver mobile                                                                 | Current (amended by L36)                      |
| 27–28            | In-house LLM (P1), hybrid deployment                                                                        | Current                                       |
| 29–39            | Coverage, readiness, sweeps, scripts, item decisions, cutover, DR, monitoring, secrets, security, incidents | Current                                       |
| 40–45            | Design system, page specs, UX flows, agent framework, API/data, IoT                                         | Current                                       |
| 48–56            | Onboarding, legal, store release, Shopify review, runbooks, a11y/French, support, decisions, L30            | Current                                       |
| 60–67            | Phase 0 plan and diagrams                                                                                   | Current                                       |
| 68               | Trust & Help Centre                                                                                         | Current                                       |
| 70–76            | Business model, onboarding, pricing, support, integrations, ops console, acceptance tests                   | Current                                       |
| 77               | Traceability of Ravi's asks                                                                                 | Current                                       |
| 78–83            | Leads/CRM, metrics, vehicle compliance, lifecycle, guided job flows, core model + UX                        | Current                                       |
| 98               | Unknowns                                                                                                    | Current                                       |
