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

- Still open: ELD requirement for the leased box truck (legal check); CVOR weight threshold (U-12) vs the leased truck's registered weight; lease wording vs insurance; pilot merchant name; lease cost numbers for the truck price.
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

- D-P0-1..7 all decided (pilot end of Phase 0 human-run; Redpanda P0; box truck + cooler P1; domain schemas; keep `com.porterchain.PCD`; Valhalla + VROOM, OSRM by benchmark; Google Play P1 with D-U-N-S in P0).
- **U-L32-1** Whether Shopify App Review treats PorterChain's off-platform delivery invoices as "app charges" for a public (unlisted) app: no limited-visibility exemptions since March 2026. Ask Shopify Partner Support before Phase 2 public-app work (doc 51).
- **U-L32-2** Pilot merchant's Shopify plan: carrier-calculated rates need Advanced/Plus or Grow with yearly billing or the CCS add-on; Basic falls back to delivery-profile flat rates.
- **U-L32-3** Enough real Toronto+150 km stops for the routing benchmark (target 500; synthetic top-up labelled if short).
- **U-L32-4** VROOM + Valhalla on Oracle A1 arm64 build and RAM fit (with Redpanda mirror + PG replica).
- **U-L32-5** D-U-N-S issue time for Porterchain Inc. (free route can take up to ~30 days).

## L33 Trust & Help Centre (doc 68)

- **U68-1** Whether PorterChain cars/vans are "commercial motor vehicles" so O. Reg. 643/05 conditions and the $4.41/kg limit apply (lawyer).
- **U68-2** Insurer requirements for drivers and cargo cover limit (sets the declared-value cap).
- **U68-3** Employee count for AODA thresholds (20+ report, 50+ WCAG duty).
- **U68-4** Claims deadlines (60 days notice / 9 months) to confirm against the regulation text.
- **U68-5** CPA 2023 proclamation date; Bill C-36 progress.
- **U68-6** Decisions D-68-1..7 (doc 68 §11).
