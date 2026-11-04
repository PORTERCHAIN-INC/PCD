# 98 — Unknowns (not verified; nothing here is drawn as fact)

| ID   | Unknown                                                                                                      | How to resolve                                                |
| ---- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| U-01 | Live DB schema vs migrations (local 55632 not compared for every table)                                      | read-only diff on 55632                                       |
| U-02 | OpenAPI for 20 handlers missing from snapshot                                                                | regenerate offline                                            |
| U-03 | Where the 50 % / 35 % margin bands are computed in code (warn-only)                                          | grep pricing engine; add test                                 |
| U-04 | Prod deployment topology beyond compose/Caddy                                                                | ops confirm                                                   |
| U-05 | Driver status transitions (no map)                                                                           | define in 17                                                  |
| U-06 | Outbox: confirmed absent; event delivery guarantees unknown                                                  | design step 2                                                 |
| U-07 | Shopify embedded app UI scope                                                                                | product decision                                              |
| U-08 | DBOS vs LangGraph-only durability                                                                            | RESOLVED L18 + L14 rev.: DBOS + PydanticAI agents inside DBOS |
| U-09 | Whether `lead_consent` storage can serve CASL proof for all channels                                         | review schema                                                 |
| U-10 | PCI SAQ type (Stripe hosted fields assumed)                                                                  | confirm frontend integration                                  |
| U-11 | Staff MFA enforcement in IdP                                                                                 | check IdP config                                              |
| U-12 | CVOR weight threshold for the box truck                                                                      | read ontario.ca CVOR page/HTA                                 |
| U-13 | GUI-0069 exact URL and transport/temperature record requirements                                             | fetch Health Canada page                                      |
| U-14 | Whether O. Reg. 643/05 s.2 local-municipality exemption covers in-Toronto runs                               | legal review                                                  |
| U-15 | Retention period for driver documents and police-check/abstract results (Checkr only if insurer requires)    | legal review                                                  |
| U-16 | PIPEDA breach-record retention period                                                                        | read OPC guidance                                             |
| U-17 | CPA 2002 internet-agreement section numbers (not read)                                                       | read statute                                                  |
| U-18 | Unread official pages marked ○ in 19/20 (ETA, ITA, CPA, PIPEDA, CASL, ESA, HTA, TDG, AODA, ECA, CRA records) | open each link                                                |
| U-19 | Kafka need                                                                                                   | RESOLVED L19: Kafka via Redpanda + outbox                     |
| U-20 | Rendering SVG/PNG: mmdc install blocked by safety check                                                      | render on approval                                            |

Resolved Oct 28 2026: live GPS path verified as Redis hash/GEO + Pub/Sub `porterchain:ops:live`, not Redis Streams (evidence in 12).

## Hybrid deployment (file 28)

- U28-1 Ubuntu `wg0` 10.66.0.1/24 peers unknown (`/etc/wireguard` permission denied).
- U28-2 Real droplet size and RAM use today (only `bootstrap-droplet.sh:34` "4GB" comment).
- U28-3 Oracle A1 capacity in ca-toronto-1. **Partly resolved 29 Oct (L30-15):** account in Toronto; capacity confirmed when the A1 instance is created.
- U28-4 Valhalla arm64 image tag for Oracle.

Resolved Oct 28 2026 (Ravi, file 28 §16): D-SZ1 droplet 8 GB (~$48/mo); D-LB1 "please retry" message during failover, no queued bookings; D-PR1 Cloudflare DNS-only (proxy can be enabled later); D-BK1 monthly offline USB archive copy; D-BK2 no paid DO backups; D-RAM Ubuntu 32 GB now, 64 GB before fine-tuning. U28-2 still open (the planned size is 8 GB, but actual use today is unverified). D-OCI RESOLVED 29 Oct: Oracle signed up, Toronto home region.

## L30 (29 Oct 2026, doc 56)

- Updated 29 Oct 2026: box truck is a **short-term rental** (Home Depot Canada, U-Haul backup; doc 56). ELD exempt (rental ≤ 30 days; 160 km). CVOR needed for any rented truck over 4,500 kg RGW/actual, Porterchain Inc. as operator. Pilot merchant = Kaylulu; test merchant = PCDC. Still open: Home Depot store rate sheet; rental commercial-use terms (lawyer).
- Resolved: Checkr route, Doppler, Shopify listing type, pen test, French scope, Zapier/NetSuite, Meta tier, on-call, lawyer, GPU, insurance, Oracle signup.

## Phase 0 (doc 60–67, 29 Oct 2026)

- U60-1 mypy `--strict` error count on billing/pricing/domain/dispatch (not run).
- U60-2 Test line coverage % (not measured; pytest 3,636 pass / 2 fail / 23 skip on 28 Oct).
- U60-3 Performance baseline (API p95/p99, LCP/INP/CLS, 50-stop optimise time).
- U60-4 Whether live holds any merchant Stripe customers/cards (live DB not read).
- U60-5 Whether `stripe_payouts` serves retail flows.
- U60-6 Customer-app in-app account deletion completeness (`AccountScreen.tsx` references deletion; flow not traced).
- U63-1 `interac_transfers` → `invoices` link (no FK found).
- U63-2 How `dispatch_routes` links to `stops` today.
- U66-1 `IN_TRANSIT → DAMAGED` edge (ops confirm).
- U66-2 Invoice enum values vs `billing_engine/models.py:140`.
- U67-1 Which of `app.toml` / `shopify.app.custom.toml` is authoritative.
- U-20 partly resolved: diagrams 61–67 rendered with mermaid-cli on the agent box (`rendered_p0/`); the older 01–28 diagrams are not rendered yet.

## L32 decisions recorded (Ravi, 29 Oct 2026; doc 60 §12–13)

- D-P0-1..7 all decided (pilot end of Phase 0 human-run; Redpanda P0; box truck + cooler P1; domain schemas; keep `com.porterchain.PCD`; Valhalla + VROOM, OSRM by benchmark; Google Play P1; D-U-N-S 243332549 issued).
- **U-L32-1** Whether Shopify App Review treats PorterChain's off-platform delivery invoices as "app charges" for a public (unlisted) app: no limited-visibility exemptions since March 2026. Ask Shopify Partner Support before Phase 2 public-app work (doc 51).
- **U-L32-2** Pilot merchant's Shopify plan: carrier-calculated rates need Advanced/Plus or Grow with yearly billing or the CCS add-on; Basic falls back to delivery-profile flat rates.
- **U-L32-3** Enough real Toronto+150 km stops for the routing benchmark (target 500; synthetic top-up labelled if short).
- **U-L32-4** VROOM + Valhalla on Oracle A1 arm64 build and RAM fit (with Redpanda mirror + PG replica).
- **U-L32-5 RESOLVED** (29 Oct 2026): Porterchain Inc. D-U-N-S 243332549 issued; used to create the Google Play organisation account (Phase 0 week 11).

## L33 Trust & Help Centre (doc 68)

- **U68-1** Whether PorterChain cars/vans are "commercial motor vehicles" so O. Reg. 643/05 conditions and the $4.41/kg limit apply (lawyer).
- **U68-2** Insurer requirements for drivers and cargo cover limit (sets the declared-value cap).
- **U68-3** Employee count for AODA thresholds (20+ report, 50+ WCAG duty).
- **U68-4** Claims deadlines (60 days notice / 9 months) to confirm against the regulation text.
- **U68-5** CPA 2023 proclamation date; Bill C-36 progress.
- **U68-6** Resolved: D-68-1..7 decided 29 Oct 2026 (68 §11); D-68-5 amounts are proposed and await confirmation.
- **U68-2 (pending from Ravi)** cargo policy per-shipment and per-kg limits; declared value above them not offered until the insurer confirms.
- **U68-3** resolved: 1–19 employees, AODA small-organisation duties (68 §8.1).
- **U68-7 resolved** Retail: no cancellation fees; B2B fee amounts per contract (D-68-5).

- privacy@porterchain.com mailbox exists (D-68-6 done, 29 Oct 2026).

## Updates 29 Oct 2026 (Ravi)

- **U-INS-1** Cargo insurance **not in place**: Ravi buys it before the first paid delivery (G-INS); declared value stays off until then. Commercial auto / HNOA / CGL: none held (round 2); bound before the first paid delivery (G-INS). Home Depot requires the renter's own non-owned-auto liability (sells none); U-Haul business accounts need a COI or SafeMove.
- **U-TRK-1** Home Depot Canada rates are not published online; get the store's rate sheet (and whether any GTA store has a box truck). U-Haul per-km rates vary by dealer ($0.49–0.99/km seen).
- **U-TRK-2** (lawyer) Do Home Depot / U-Haul rental terms allow paid courier use; operator status when a contractor drives a Porterchain-rented truck; 160 km exemption on edge-of-area days.
- **U-QT-1** Quote validity 72 h vs code 30 min (`config.py:51`, `settings_service.py:130`, Shopify `QUOTE_TTL`): change in Phase 0 week 2.
- Pilot merchant resolved: Kaylulu; test merchant PCDC.
- Backup on-call resolved: named, contact held privately by Ravi.

## Updates 29 Oct 2026, round 2 (Ravi)

- **U-INS-2 (pilot blocker)** No commercial auto, HNOA, cargo or CGL insurance. Gate G-INS: bind all before the first paid delivery incl. Kaylulu; get quotes from a licensed insurance broker before week 12. Replaces U-INS-1's "confirm commercial insurance" (answer: none).
- **U-TRK-1 updated** Home Depot rates not on any static page; homedepot.ca blocks scripted fetches; Ravi checks the vehicle page with a GTA store set, or calls. U-Haul Toronto per-km only in the reservation quote; plan $0.69–1.09/km.
- **U-BRK-1** Broker model: open a separate trust account (HTA s.191.0.1) before the first brokered job; buy contingent cargo/broker liability; lawyer: carrier-vs-broker status when Porterchain issues the BOL, Partner Agreement clauses, non-solicitation.
- **U-CXL-1 resolved** Retail: no cancellation fees; merchants/partners per contract (D-68-5). Lawyer reviews the B2B fee clause.
- **Box truck** downgraded: prep pack behind a flag; no open action until an order arrives. Ravi is the driver of rented vehicles.
- PCDC = test development store created by Ravi in Shopify Partners.

## Traceability (doc 77, 29 Oct 2026)

- **U77-1** Ravi's 28 Oct message text was traced from decision records (main-chat transcript not readable by this job); any 28 Oct ask not recorded as an L-decision may be missing. Verify by Ravi skim of 77 §1.
- **U77-2** "wether" in t100u read as "whether"; weather rule (77 §2.3) added anyway.
- Shopify Partner Support message drafted (77 §3), not sent.

## L35 (29 Oct 2026, docs 70–76)

- **U-70-1** (lawyer) **Pharmacy delivery agreement** (D-70-4 changed: all medicine types incl. controlled substances; 70 §7a). Covers PorterChain as the pharmacy's delivery agent, custody and records, loss/theft notice duties (the pharmacy reports to Health Canada), PHIPA, insurance and audit. Also: confirm OCP/NSAA conditions, and track when CSR SOR/2025-242 comes into force.
- **U-72-1 resolved:** D-72-2 decided 29 Oct 2026 (72 §8 approved, XS $17/$32/$47). D-72-1/3/4 decided yes 29 Oct 2026.
- **U-74-1 resolved (L36, 29 Oct 2026):** Ravi confirmed the Shopify rejection reason: reviewers cannot log in through Clerk.
- **U-74-2 resolved (L36):** same reason for Apple. The fix is Keycloak with Google + Sign in with Apple + password + passkeys, a reviewer account and in-app deletion.
- **U-74-3** WhatsApp business number for click-to-chat (73 §1).
- **U-75-1 resolved** D-75-1 decided yes 29 Oct 2026.
- Decisions (29 Oct 2026): D-70-1/2/3, D-72-1/3/4 and D-75-1 decided yes. D-70-4 decided with changed scope (70 §7a). **D-72-2 decided** 29 Oct 2026 (72 §8 approved, XS $17).
- **U79-1..4** (doc 79 §10): confirm WACC 18 %, software life 3 yr, Civic 5 yr to $7k, fuel $1.50/L, cash fixed ≈ $430/mo; accountant confirms CCA classes (12 vs 50; class 10); insurance cost unknown (G-INS) raises every break-even; 12-stop S route is yellow at the proposed price.
- **U78-1..3** Meta App Review timing; whether paid ads run (`lead_capi`); untracked `lead_channel_adapters.py` (doc 78).
- **U82-1** Non-solicitation / non-circumvention clause in the driver/contractor agreement (wording, 12-month term, enforceability for independent contractors in Ontario; lawyer). **I82-1..6** interim decisions in doc 82 §0 until Ravi answers.
