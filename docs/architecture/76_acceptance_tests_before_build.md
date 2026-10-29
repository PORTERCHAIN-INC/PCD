# 76. Acceptance tests before build (Phase 0 gates G19–G21, L35; §13 A-FIN, §14 A-DOC, §15 A-ID, §16 A-VC, §17 A-LC and §18 A-GF/A-PAR and §19 A-PRA inside G19)

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

A-CHA-01 container no. and CAD (ex-B3) transaction no. stored as external refs and searchable · A-CHA-02 dock appointment at a terminal with document pack attached · A-CHA-03 org flagged both shipper and partner sees both menus.

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
- **A-DOC-05:** a customs pack appears only on a CHA/supply-chain order with a cross-border or in-bond leg, and stores CAD (ex-B3)/CARM references without filing.
- **A-DOC-06:** a TDG item from an org without TDG training is refused at quote time.
- **A-DOC-07:** a new business type added as a config row (seeded test type `small_shop:bookstore` reusing existing modules) works end to end with zero code changes.

## 15. Identifiers & milestones (A-ID, inside G19, doc 70 §2.3, doc 79 §6a)

- **A-ID-09:** a 60 kg XL sofa from Toronto to Mississauga gets a BOL; a bakery shipment over 45 kg is rejected with `422 small_shop_weight_cap`.
- **A-ID-01:** a 60 kg inter-municipal warehouse order gets a BOL no. with all O. Reg. 643/05 s. 4(1) fields populated. A 30 kg parcel, or a Toronto-to-Toronto order, gets no mandatory BOL.
- **A-ID-02:** a PRO no. can be saved only on an order with an LTL carrier handoff leg. Otherwise it returns `422 identifier_not_applicable`.
- **A-ID-03:** a trip cannot start without plate, a valid VIN (check digit) and insurance evidence, including a rental. A rental with RGW > 4,500 kg sets `cvor_required` and blocks without a CVOR no.
- **A-ID-04:** an SSCC with a wrong check digit is rejected; a pallet stores gross/tare/net and net = gross − tare.
- **A-ID-05:** a POD noted "short 2" opens an OS&D claim with notice deadline delivered + 60 days and cap max(declared, $4.41/kg).
- **A-ID-06:** Incoterms, CCI, CUSMA COO and CAD refs are hidden for a bakery and a warehouse (UI, API 422, emails). For a CHA cross-border order they are stored as record-only, and no filing call exists.
- **A-ID-07:** ATA/ATD give dwell; OTIF/dwell/OS&D match the 79 §6a worked check (A-FIN-13).
- **A-ID-08:** no AWB/sea-waybill module, no NMFC class field, and no PTA or LIFR field exist; density is computed from dims and weight.

## 16. Vehicle compliance (A-VC, inside G19, doc 80)

- **A-VC-01:** a rental truck with RGW 5,000 kg: the job cannot start until the Schedule 1 DVIR is submitted. A major defect blocks the job; a minor defect is recorded and ops are notified. The DVIR expires after 24 h.
- **A-VC-02:** a Civic or a 4,000 kg van job starts without a DVIR, and the 5-photo walk-around is offered, not forced.
- **A-VC-03:** HOS: warning at 12 h driving; at 13 h driving, 14 h on-duty or 16 h elapsed, no new offers are made.
- **A-VC-04:** a "worked for another operator today" answer of yes removes the 160 km exemption, and the full daily log is required.
- **A-VC-05:** a trip cannot start without plate, VIN, rental agreement (if rental) and insurance evidence. RGW > 4,500 kg requires a CVOR no.
- **A-VC-06:** a quote of 380 kg on a Civic with 350 kg payload returns `422 vehicle_overweight`.
- **A-VC-07:** airplane mode: DVIR, HOS and POD actions queue in `offline.ts`, sync once with the same `client_id`, and the HOS timestamps are unchanged after sync.
- **A-VC-08:** an invoice is finalised only after `order.pod_completed` (existing `invoice_requires_pod_completed`), and DSO counts from the POD date.

## 17. Order lifecycle (A-LC, inside G19, doc 81)

- **A-LC-01:** the same seeded order posted through Shopify, the API, CSV and the portal produces one order with identical stages 2–14 (Idempotency-Key replay returns the same id).
- **A-LC-02:** a quote older than 72 h cannot be booked; a re-quote uses the current rate card version.
- **A-LC-03:** an order without terms acceptance stays `draft` and is never offered to a driver.
- **A-LC-04:** a brokered job's partner share is posted to the trust account, and a payout run cannot pay a partner from the operating account.
- **A-LC-05:** each stage emits the internal event and the public webhook named in 81 §2 (`order.created`, `order.picked_up`, `order.out_for_delivery`, `order.delivered`, `order.failed`, `invoice.issued`, `partner_job.offered`, `claim.opened`, `payout.sent`), signed per doc 74 §4.
- **A-LC-06:** a noted POD opens a claim with the 60-day notice deadline, and the claim pack contains POD, photos, BOL (if any), seal and weights.
- **A-LC-07:** a CHA order stores the CAD, CCI and COO refs and makes no outbound CARM call.

## 18. Guided job flows and driver parity (A-GF, A-PAR, inside G19, doc 82)

- **A-GF-01:** a parcel order's flow spec has no ID, seal or temperature step; a pharmacy order's spec always has seal, ID and signature steps (generated from required_documents and packs).
- **A-GF-02:** every capture in an order's required-documents list appears in the spec, and no step appears that the list or a pack does not ask for (all 7 delivery types and 4 pickup modes).
- **A-GF-03:** a broken or mismatched seal blocks the pharmacy drop and creates a same-day return task; the driver cannot hold the package overnight.
- **A-GF-04:** a temperature reading outside 2–8 °C blocks a silent drop and raises an excursion report.
- **A-GF-05:** 2-person furniture cannot start without the second driver checked in and the before photos taken; B2B dock cannot close when C1 fires without a signed BOL, or when a count is short without an OS&D note.
- **A-GF-06:** in airplane mode a whole pharmacy wizard completes offline from the cached spec; captures sync once with no duplicates, and the seal check is verified again on the server.
- **A-GF-07:** every card shows in EN and FR (no missing keys) and passes axe/WCAG 2.0 AA checks: labels on icons, 44 px targets, large text.
- **A-GF-08 (secrecy):** the driver job payload has no price, rate card, contract, volume or other-customer fields (SpiceDB check denies them server-side). The address and contact return 403 two hours after completion. There is no export action, each contact view writes an audit row, and the watermark is shown.
- **A-GF-09 (Shopify):** the in-admin setup finishes in 5 steps with no login screen (session token). The order page shows the packing guidance for the business type, and a bakery order shows no BOL.
- **A-GF-10 (customer):** the reviewer demo account shows the "what to prepare" card for pharmacy (ID or named agent), signature, and furniture (elevator).
- **A-PAR-01:** the same flow spec gives the same step ids, captures, blocking results and copy keys on driver web and mobile (shared `@porterchain/driver-flows` fixtures).
- **A-PAR-02:** both apps use the one `@porterchain/queue` offline queue; `driver-portal/src/lib/offline-queue.ts` no longer exists.
- **A-PAR-03:** both apps expose the same five areas (Today, Job, Pay, Inbox/Help, Me) and French; the web-only `impersonate` page is reachable only with the ops role.
- **A-PAR-04:** the pharmacy subtype accepts no live order while its Phase 1 flag is off; the sandbox pharmacy wizard passes A-GF-01 to A-GF-06.

## 19. Pricing admin (A-PRA, inside G19, doc 72 §9, doc 75 §4)

- **A-PRA-01:** Standard v1 prices XS $17 / $32 / $47 (Z1/Z2/Z3), and every band's Z2/Z3 is +$15/+$30.
- **A-PRA-02:** publishing a Standard draft needs owner; finance, dispatcher, support and sales get 403 (SpiceDB). Published versions cannot be edited.
- **A-PRA-03:** the preview reports counts and changes without writing anything. After publishing, a quote issued 1 h earlier keeps its price and version until it expires (72 h). New quotes use the new version from `effective_from`.
- **A-PRA-04:** an org set to Custom with a −40 % override is rejected (outside the min/max). A red-margin override saves only with a reason. Expiry falls back to Standard, and the alert goes out 14 days before.
- **A-PRA-05:** Kaylulu is Custom on `contract-kaylulu-2026-09` with a contract link, and K1–K5 still price to the cent (A-PR-08).
- **A-PRA-06:** a dispatcher can lower an order by ≤ 10 % / $25; a larger change becomes an owner request. Finance is capped at ±25 % / $100. Every change writes before/after, actor and reason to the audit log.
- **A-PRA-07:** an increase after acceptance sets `consent_required`, charges nothing until the payer accepts, and keeps the original price on decline. A decrease after payment issues a refund or credit and a notification. `order.price_changed` fires each time.
- **A-PRA-08:** after any adjustment, HST is recomputed on its own line and the total equals the sum of the lines (no drip).
- **A-PRA-09:** a new org is on Standard with no setup. Only the owner can switch it to Custom. Presets −8 % plus −$2/stop plus "S Z1 = $16" give the preview prices, which equal the saved card's quotes to the cent.
- **A-PRA-10:** "send quote now" creates a 72 h quote pinned to the custom card version, emails it and shows it in the portal. A merchant quote request appears in the admin screen.
- **A-PRA-11 (one engine, identical price):** for the same custom merchant, parcel and lanes, the price is identical to the cent in all of these:
  - the Shopify carrier-calculated rate;
  - the Shopify flat-rate fallback (callback forced to time out);
  - `POST /v1/quotes`, the merchant portal and the merchant-api;
  - the invoice line after POD.
    Every price comes from `get_pricing_service`, and the invoice does not re-price.
- **A-PRA-12:** after a custom card change, the Shopify delivery-profile fallback rates are rewritten within 5 minutes and match the engine.
