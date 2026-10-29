# 76. Acceptance tests before build (Phase 0 gates G19–G21, L35; §13 A-FIN and §14 A-DOC inside G19)

Written before code. Each scenario becomes a pytest-bdd / Playwright / Maestro test with the ID below; all run against a sandbox org (PCDC-like) and never touch live data. Gate **G19** = all A-* scenarios green; **G20** = Shopify review-readiness (§10); **G21** = mobile review-readiness (§11). Order follows build order.

## 1. Common journey stages (each type covers all 12)

sign-up · onboarding · integration · first quote · order · label · delivery · issue · ticket · invoice · payment · offboarding.

## 2. Shopify merchant (A-SHP)

- **A-SHP-01 install** Given a dev store, When the merchant installs from the link, Then an org `shopify_merchant` exists with the shop's name, email and address, and the app UI shows inside admin with no login screen.
- **A-SHP-02 onboarding** Given a new org, When the merchant confirms pickup and taps "Looks right" on the profile, Then the checklist is 2/3 and pickup mode is `scheduled_daily` cut-off 14:00.
- **A-SHP-03 carrier rates eligible** Given a store on Advanced, When rates are enabled, Then checkout returns a PorterChain rate within 2 s and the merchant markup rule is applied.
- **A-SHP-04 fallback** Given a Basic store, When the merchant opens Rates, Then the app explains in plain words and offers "Use flat rates" with suggested amounts, and no carrier-service call is attempted.
- **A-SHP-05 first order** When an order is created in Shopify, Then one PorterChain order `PC-YYMM-XXXXXX` exists with `external_ref(order, #1001)`; replaying the webhook 3 times creates no duplicate.
- **A-SHP-06 label** Given label_mode ours, Then a 4x6 PDF and ZPL label with Code128 PC id and QR are downloadable from the app.
- **A-SHP-07 tracking** The tracking page finds the order by `#1001` + postcode and by PC id.
- **A-SHP-08 issue/ticket** When the merchant taps Get help on the order, Then ticket T-… is created with org and order linked and an EN auto-acknowledgement is sent within 1 min.
- **A-SHP-09 invoice/payment** At month end an invoice with HST is issued and an Interac payment with the invoice no. in the message auto-matches.
- **A-SHP-10 offboarding** When the app is uninstalled, Then the integration is disabled, no new orders sync, invoices remain viewable, `shop/redact` deletes customer PII after the window.

## 3. Warehouse / 3PL / storage (A-WH)

A-WH-01 4-field sign-up quotes a pallet in < 2 min · A-WH-02 docks with hours and 30-min appointment slots saved; a booking outside hours is refused with a suggested slot · A-WH-03 CSV upload of 50 rows with their order and SKU keys: valid rows created, invalid rows returned with plain fixes, re-upload is idempotent · A-WH-04 label_mode theirs: driver scans a GS1-128 SSCC and it binds to the PC id · A-WH-05 relabel rule triggers on an unreadable barcode · A-WH-06 multi-location org: each location's pickup mode honoured · A-WH-07 invoice by location cost centre · A-WH-08 the same org switched on as storage partner receives partner jobs.

## 4. Small shops (A-SS)

A-SS-01 pet food 20 kg → band M, price shown upfront · A-SS-02 flowers → billable 14.4 kg M, upright flag on driver job · A-SS-03 cake → food-handling checklist step required before pickup · A-SS-04 pharmacy controlled-substance job (70 §7a) → safe-drop hidden; POD needs seal id + count, ID check and patient/agent signature; every handoff scanned; failed attempt creates a same-day return-to-pharmacy job; loss raises an immediate pharmacy alert · A-SS-05 email-to-order: an email to orders@ with address + item creates a draft for one-tap confirm · A-SS-06 on-demand pickup booked from mobile web in ≤ 5 taps.

## 5. Courier partner (A-CP)

A-CP-01 sign-up then job offer is blocked until COI, HST and Partner Agreement are on file (just-in-time ask shown) · A-CP-02 partner routing: when no own driver is free within the window, the job is offered to the partner whose area covers the FSA; margin band shown to staff (red ≤ 35 % still allowed) · A-CP-03 partner accepts, uploads POD, payout line created · A-CP-04 theirs tracking primary: customer page headline shows partner ref.

## 6. Logistics partner (A-LP)

A-LP-01 CVOR required for > 4,500 kg vehicles · A-LP-02 EDI-lite: SFTP CSV of 20 orders imported, status file returned with picked_up/delivered · A-LP-03 recurring route RRULE generates pickups weekly.

## 7. Supply chain (A-SC)

A-SC-01 lane quote request reaches Ravi's Today page with a booking link · A-SC-02 contract rate card overrides b2b card · A-SC-03 API with OAuth client credentials, scopes enforced (orders:write without labels:read cannot fetch labels: 403 problem+json).

## 8. Import/export / CHA (A-CHA)

A-CHA-01 container no. and B3 transaction no. stored as external refs and searchable · A-CHA-02 dock appointment at a terminal with document pack attached · A-CHA-03 org flagged both shipper and partner sees both menus.

## 8b. Retail and French (A-RT, A-FR)

A-RT-01 retail quote shows all mandatory fees in headline; cancelling before pickup charges $0 · A-RT-02 Stripe payment, no COD option · A-FR-01 with locale fr, sign-up, emails E1–E9, quote explainer, tracking and ticket ack are in French with no English strings (string-coverage test) · A-FR-02 legal links point to FR versions.

## 9. Pricing (A-PR) and operating profile (A-OP)

A-PR-01..05 the five worked examples in 72 §5 price to the cent · A-PR-06 dim weight = max(actual, L×W×H/5000) · A-PR-07 add-ons appear before booking; no charge added after checkout (drip-pricing test: final = shown) · A-PR-08 Kaylulu 90-day golden reprice 0-cent diff · A-PR-09 quote valid 72 h then expires.
A-OP-01 each business type gets its default profile and the wizard needs only "Looks right" · A-OP-02 `(org, ref_type, ref_value)` unique; same ref in two orgs allowed · A-OP-03 PC id and their ref appear on label, email, webhook, tracking · A-OP-04 tracking modes ours/theirs/both render correctly · A-OP-05 barcode whitelist rejects a non-listed symbology with relabel prompt · A-OP-06 profile change versioned; old orders keep their version.

## 10. Shopify review readiness (G20, weeks 1–2)

- A-SHR-01 fresh install on a dev store: no redirect out of admin, no Clerk/Keycloak page, no OTP/CAPTCHA (Playwright asserts frame URL stays on admin.shopify.com and no element matching sign-in/captcha).
- A-SHR-02 session token → token exchange succeeds; API rejects an expired/forged token (401).
- A-SHR-03 reinstall reuses the same org, no duplicate.
- A-SHR-04 uninstall → `app/uninstalled` handled, reinstall works.
- A-SHR-05 compliance webhooks with valid HMAC → 200 and logged; invalid HMAC → 401.
- A-SHR-06 reviewer path: open app → setup → demo rate → 3 demo orders visible in ≤ 4 clicks on PCDC.
- A-SHR-07 requested scopes = scopes used (no unused scope).
- Checklist: review notes + screencast uploaded; app listing privacy/terms links (doc 68); support email; demo data seeded.

## 11. Mobile review readiness (G21, weeks 1–2; Maestro flows in `apps/mobile-*/maestro/review-*.yaml`)

- A-APR-01 customer review account signs in with email + password, no code/CAPTCHA, sees seeded PCDC orders and tracking.
- A-APR-02 driver review account signs in, sees 2 sandbox jobs, completes pickup + POD photo; no real dispatch or payout record created.
- A-APR-03 in-app account deletion in both apps completes and the web deletion page accepts a request.
- A-APR-04 no social login present (else Sign in with Apple test required).
- A-APR-05 sign-in works from a non-Canadian IP (no geo block).
- A-APR-06 Play Console App access credentials match the review account (manual check in release checklist).

## 12. Ops console (A-OPS)

A-OPS-01 every old route in 75 §3 redirects to its new place · A-OPS-02 role `support` cannot open Billing · A-OPS-03 Today shows pickups, live, exceptions and tickets due in one page.

## 13. Business metrics (A-FIN, inside G19, doc 79 §8)

A-FIN-01..12 as listed in 79 §8: EBITDA top-down = bottom-up to the cent; no HST in revenue or cost; 3PL 1.5M / 15 %; AS/RS ROI −70 %, simple return 30 %, payback 3.33 yr; NOPAT 280k / ROIC 14 % / EVA +80k; $77k baseline D&A $19,666.67 and EVA break-even 19.1 stops/day; GTA route contribution $96.75 (49.8 % yellow); Kingman alert at ρ > 0.85; SS 177.7 and EOQ 1,510.4; CCC from seeded invoices and payouts; margin colours same as 72; concurrent MV refresh.

## 14. Documents & capabilities (A-DOC, inside G19, doc 70 §2.2)

- **A-DOC-01:** a bakery org never sees a BOL. No BOL tab or download in the portal, no `bol` field in the API response, `422 capability_not_enabled` if the field is sent, no BOL in emails or webhooks, and the render service refuses.
- **A-DOC-02:** a warehouse parcel order (S band, single consignee) has no BOL. A warehouse pallet order (P band) or LTL/partner-handoff order gets a BOL in `required_documents[]` and the PDF.
- **A-DOC-03:** a warehouse order with 2 pallets gets a pallet manifest; with 1 pallet it does not.
- **A-DOC-04:** a pharmacy controlled-substance order requires the Rx custody log and ID + signature POD. A flowers order shows neither.
- **A-DOC-05:** a customs pack appears only on a CHA/supply-chain order with a cross-border or in-bond leg, and stores B3/CARM references without filing.
- **A-DOC-06:** a TDG item from an org without TDG training is refused at quote time.
- **A-DOC-07:** a new business type added as a config row (seeded test type `small_shop:bookstore` reusing existing modules) works end to end with zero code changes.
