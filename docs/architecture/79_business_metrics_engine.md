# 79. Business metrics engine: our main business formulas (Phase 0)

Written 29 Oct 2026 (America/Toronto). Docs only. This is Ravi's ask of 29 Oct 2026 (pasted finance and operations framework) made into one computed, tested layer. FEATURE_AI=false: the layer is plain SQL plus DBOS jobs, with no AI and no paid services (self-hosted Postgres in the modular monolith).

## 0. Ravi-provided facts (29 Oct 2026) and stated assumptions

| Fact (Ravi, 29 Oct 2026)    | Amount      | Book treatment (assumption)                                                                         | Tax (CCA) treatment (accountant confirms)                                                                                                           |
| --------------------------- | ----------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Software build, capitalised | $50,000     | Straight-line over **3 years**: $16,666.67/yr ($1,388.89/mo). The 5-year alternative is $10,000/yr. | Application software is usually class 12 (100 %, half-year rule in year 1); systems software is class 50 (55 %). Our own build is assumed class 12. |
| Honda Civic sedan           | $22,000     | Straight-line over 5 years to a $7,000 residual: **$3,000/yr** ($250/mo)                            | Class 10, 30 % declining balance (under the class 10.1 passenger-vehicle cost limit); half-year rule gives $3,300 CCA in year 1                     |
| Cash                        | $5,000      | Working capital                                                                                     | —                                                                                                                                                   |
| **Invested capital (IC)**   | **$77,000** | **D&A $19,666.67/yr ($1,638.89/mo)**                                                                | Book and tax depreciation differ. The P&L uses book; the tax return uses CCA. The difference is a timing difference only.                           |

Other assumptions used in this doc, all editable as Settings → Finance parameters:

- **WACC 18 %.** The company is 100 % equity, so WACC = cost of equity. CAPM gives about 11.5 % (Rf ≈ 3.2 % Government of Canada 10-year, β 1.5, market premium 5.5 %). Add a 6.5 % startup/size premium to reach 18 %, inside the 15–20 % range.
- **Tax rate 12.2 %.** This is the Canadian-controlled private corporation small-business rate in Ontario: 9 % federal + 3.2 % Ontario on the first $500k of active business income. NOPAT uses 12.2 %.
- **HST is excluded from revenue and from costs.** It is collected and remitted, so it is a liability and never income. Input tax credits reduce costs net of HST.
- **Civic running cost per km (variable): $0.17.**
  - Fuel is about 7.5 L/100 km in city stop-start driving × $1.50/L = $0.1125.
  - Maintenance and tires are about $0.06.
  - Usage depreciation would be about $0.10/km (($22,000 − $7,000) ÷ 150,000 km). It is **not** added per km, because book depreciation is time-based in D&A; that avoids counting it twice. All-in it is about $0.27/km.
  - **Insurance: TBD.** None is held (G-INS). When it is bound, it is added to monthly fixed cost.
- **Driver time is costed at $30/h**, the same as doc 72, even while Ravi drives the pilot. That is the economic cost; if Ravi takes no pay, cash profit is higher by that amount.
- **Cash fixed cost: ≈ $430/month.**
  - Droplet 8 GB ≈ $70; Oracle A1 free; Ubuntu own hardware.
  - Domains, email and ZeptoMail ≈ $30.
  - Software subscriptions ≈ $50.
  - Accounting/admin ≈ $150.
  - Marketing ≈ $100.
  - Phone/data ≈ $30.
  - Insurance TBD is not included.
- **Working days per month: 22.**

**Does the Civic fit the bands?**

- **XS (≤ 40 cm) and S (≤ 60 cm, ≤ 10 kg): yes.** This is the Kaylulu compact sedan path; about 30–40 S parcels per load with the trunk and folded rear seat.
- **M (≤ 100 cm, ≤ 25 kg): partly.** Items up to about 90 cm long fit with the rear seat folded, a few per load. M jobs over 90 cm, and all L, XL, P and Vehicle jobs, go to a van, rental truck or partner (docs 56, 72).
- The dispatch rule follows from this: the Civic only takes XS/S, and M ≤ 90 cm.

## 1. PorterChain chart of accounts (P&L)

| Code | Line                                   | Source table (domain schema, doc 60 §8)                                |
| ---- | -------------------------------------- | ---------------------------------------------------------------------- |
| 4100 | Delivery fees (bands, routes)          | `billing.invoice_lines` kind=delivery, `ordering.orders`               |
| 4200 | Add-ons (2-person, stairs, assembly …) | `billing.invoice_lines` kind=addon                                     |
| 4300 | B2B contract revenue (e.g. Kaylulu)    | `billing.invoice_lines` with `pricing.rate_cards` type=contract        |
| 4400 | Broker margin (P1 live)                | sell − partner cost, `billing.invoice_lines` + `dispatch.partner_jobs` |
| 4500 | Storage (later)                        | reserved                                                               |
| 5100 | Driver pay                             | `driver.pay_statements` (DPWRA)                                        |
| 5200 | Fuel and tolls                         | `billing.expenses` category=fuel/toll; km from `dispatch.routes`       |
| 5300 | Vehicle rental (Home Depot / U-Haul)   | `billing.expenses` category=rental                                     |
| 5400 | Carrier / partner payouts              | `billing.payouts` (partner)                                            |
| 5500 | Packaging and labels                   | `billing.expenses` category=packaging                                  |
| 5600 | Payment fees (Stripe retail; Interac)  | `billing.payments.fee_cents`                                           |
| 5700 | Cargo claims (net of recoveries)       | `ordering.osd_claims` paid − recovered (§6a)                           |
| 6100 | Hosting (droplet, Oracle)              | `billing.expenses` category=hosting                                    |
| 6200 | Software                               | `billing.expenses` category=software                                   |
| 6300 | Insurance (when bound, G-INS)          | `billing.expenses` category=insurance                                  |
| 6400 | Marketing                              | `billing.expenses` category=marketing (feeds CAC, doc 78)              |
| 6500 | Admin, accounting, phone               | `billing.expenses` category=admin                                      |
| 7100 | Depreciation: Civic, devices           | `billing.fixed_assets` (new table, book schedule + CCA class)          |
| 7200 | Amortisation: capitalised software     | `billing.fixed_assets`                                                 |
| 8100 | Interest                               | `billing.expenses` category=interest                                   |
| 8200 | Income tax                             | `billing.tax_provisions`                                               |

All amounts are integer cents, net of HST (doc 60 naming rule). The new tables are additive: `billing.expenses`, `billing.fixed_assets` and `billing.tax_provisions`.

## 2. Formulas (the engine computes exactly these)

| Metric                      | Formula                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| Revenue                     | Σ 4xxx (net of HST, credit notes subtracted)                                                     |
| Direct costs                | Σ 5xxx                                                                                           |
| Gross profit / contribution | Revenue − direct costs                                                                           |
| EBIT                        | Gross profit − OpEx (6xxx) − D&A (7xxx)                                                          |
| EBITDA, top-down            | EBIT + depreciation + amortisation                                                               |
| EBITDA, bottom-up           | Net income + interest + taxes + depreciation + amortisation (must equal top-down; test A-FIN-01) |
| EBITDA margin               | EBITDA ÷ revenue                                                                                 |
| ROI                         | (gain − cost) ÷ cost                                                                             |
| Simple annual return        | annual gain ÷ cost (labelled differently from ROI)                                               |
| Payback                     | cost ÷ annual gain                                                                               |
| ROA (DuPont)                | asset turnover (revenue ÷ total assets) × operating margin (EBIT ÷ revenue)                      |
| NOPAT                       | EBIT × (1 − tax rate)                                                                            |
| ROIC                        | NOPAT ÷ invested capital                                                                         |
| Cost of equity (CAPM)       | Rf + β (Rm − Rf)                                                                                 |
| WACC                        | E/V × Re + D/V × Rd × (1 − Tc)                                                                   |
| EVA                         | NOPAT − IC × WACC                                                                                |
| EV                          | adjusted EBITDA × multiple (illustrative only; small-business multiples about 3–5×)              |
| CCC                         | DIO + DSO − DPO                                                                                  |
| Little's Law                | I = R × T                                                                                        |
| Kingman (G/G/1)             | Wq ≈ ((Ca² + Cs²)/2) × (ρ/(1 − ρ)) × τ                                                           |
| Safety stock                | SS = Z × √(L σD² + D² σL²)                                                                       |
| EOQ with backorders         | √(2DS/H × (H + B)/B)                                                                             |

## 3. Errors corrected in Ravi's pasted source

1. **AS/RS cost appears as both $500,000 and $50,000.** The ratio shown, 150,000 ÷ 500,000, uses $500,000, so the $50,000 is a typo.
2. **ROI as written is (gain − cost) ÷ cost** = (150,000 − 500,000) ÷ 500,000 = **−70 %** in year 1, not 30 %. The 30 % is gain ÷ cost, the **simple annual return**. **Payback is 500,000 ÷ 150,000 = 3.33 years.** Over 5 years with no other costs, ROI = (750,000 − 500,000) ÷ 500,000 = +50 %.
3. **Verified correct:**
   - 3PL gross profit = 10,000,000 − 7,500,000 = 2,500,000.
   - EBIT = 2,500,000 − 1,000,000 − 400,000 = 1,100,000.
   - EBITDA = 1,500,000, margin **15 %** ✓.
   - Bottom-up check: net income = 1,100,000 − 250,000 = 850,000; + 250,000 + 400,000 = 1,500,000 ✓.
   - Capital project: EBIT = 400,000, **NOPAT 280,000** ✓, **ROIC 14 %** ✓, capital charge 200,000, **EVA +80,000** ✓.
4. Minor issues: the source misspells "variability" and "erodes", and leaves "Taxes & Interest" as one line. The engine keeps them as separate accounts (8100, 8200).

## 4. Baseline economics on Ravi's $77,000

**Typical GTA sedan route (Civic, b2b-std S at $16.20, 12 stops, 3 h including pickup, 45 km):**

- Revenue is $194.40.
- Direct cost is $97.65 (3 h × $30 = $90.00, plus 45 km × $0.17 = $7.65).
- **Contribution per route is $96.75 (49.8 %, yellow)**, which is **$8.06 per stop**.
- Cost per stop is $8.14 and cost per km is $0.17 (vehicle) or $2.17 (all direct).
- Revenue per driver-hour is $64.80; route density is 4 stops/h.
- **At 16 stops in 3.5 h and 55 km:** revenue $259.20, cost $114.35, contribution $144.85 (**55.9 %, green**).
- **Density is the lever** that moves a route from yellow to green.

| Threshold (at $8.06 contribution per stop, 22 days/month)                  | Monthly amount needed | **Stops/day** |
| -------------------------------------------------------------------------- | --------------------- | ------------- |
| Cash break-even (cash fixed $430)                                          | $430                  | **2.4 → 3**   |
| Accounting break-even (EBIT = 0, + D&A $1,638.89)                          | $2,068.89             | **11.7 → 12** |
| EVA break-even (NOPAT ≥ IC × WACC = $13,860/yr, i.e. EBIT ≥ $15,785.88/yr) | $3,384.38             | **19.1 → 20** |

- **Required for ROIC > WACC:** NOPAT > $13,860/yr, so EBIT > $15,785.88/yr and EBITDA > $35,452.54/yr ($2,954.38/month).
- **At 20 stops/day for one year:**
  - Revenue $85,536.
  - Direct cost $42,966; contribution $42,570.
  - Cash OpEx $5,160; EBITDA $37,410 (43.7 % margin).
  - D&A $19,666.67; EBIT $17,743.33.
  - NOPAT $15,578.65; **ROIC 20.2 % > 18 %; EVA +$1,718.65.**
  - EV (illustrative, 4×) ≈ $150,000.

**Payback of $77,000 from monthly EBITDA** (stops/day × 22 × $8.06 − $430):

| Pilot volume            | Monthly EBITDA | Months to payback |
| ----------------------- | -------------- | ----------------- |
| 12 stops/day            | $1,698.50      | 45.3              |
| 20 stops/day            | $3,117.50      | 24.7              |
| 40 stops/day (2 routes) | $6,665.00      | 11.6              |

**Cash conversion cycle:**

- DIO ≈ 0, because we hold no inventory.
- DSO ≈ 30 days: Interac merchant invoices go out monthly, net 15, so the average receivable is about 15 + 15 days.
- DPO ≈ 10 days: driver pay is weekly or biweekly (DPWRA). Partner payouts net 30 come in P1.
- **CCC ≈ +20 days**, so working capital ≈ 20/365 × revenue (about $4,700 at 20 stops/day). The $5,000 cash covers it, with no margin for insurance premiums. Insurance is TBD, so Ravi should keep this in mind.
- Levers: weekly invoicing (DSO → about 15) and Interac auto-deposit.

**ROA (DuPont), year 1 at 20/day:** asset turnover 85,536 ÷ 77,000 = 1.11 × operating margin 20.7 % = **23.0 %**.

## 5. Operations math

- **Little's Law:** 40 parcels/day picked up, average 0.25 day from pickup to POD → about 10 parcels in the network. Alert when I grows while R is flat, because that means T is growing.
- **Kingman (dispatch and drivers):** with Ca² = 1, Cs² = 0.5 and τ = 10 min per job:
  - ρ 0.85 → Wq ≈ 42.5 min.
  - ρ 0.95 → Wq ≈ 142.5 min.
  - **Utilisation cap 85 %.** Insights shows a yellow alert when a driver's or dispatcher's rolling 2-hour ρ is over 0.85, and red over 0.90. Dispatch stops offering new same-day jobs to that driver (the "never blocks" rule still applies to quotes).
- **Safety stock (warehouse and supply-chain partners; broker mode, P1 live):** D = 100/day, σD = 20, L = 4 d, σL = 1 d, Z = 1.65 (95 %) → SS = 1.65 × √(4·400 + 10,000·1) = **177.7 → 178 units**.
- **EOQ with backorders:** annual D = 36,500, S = $50, H = $2/unit/yr, B = $8 → **EOQ ≈ 1,510 units**. Phase 0 builds the calculators and tests; live use is in P1 (warehouse partners and brokered freight).
- **Trilemma: one objective per business type, two constraints.**

| Business type                | Objective               | Constraints                             |
| ---------------------------- | ----------------------- | --------------------------------------- |
| Shopify merchant, small shop | maximise on-time %      | contribution ≥ 50 % (green), ρ ≤ 0.85   |
| Retail                       | maximise on-time %      | price as card, ρ ≤ 0.85                 |
| Warehouse / 3PL              | minimise cost per stop  | on-time ≥ 98 %, dock wait ≤ 30 min      |
| Supply chain / broker (P1)   | minimise inventory (SS) | fill rate ≥ 95 %, cost per stop ≤ card  |
| Courier / logistics partner  | maximise margin         | on-time ≥ 98 %, partner SLA             |
| CHA / import-export          | maximise on-time %      | contribution ≥ 50 %, documents complete |

## 6. Unit economics computed nightly

Contribution margin per stop, route, order and org. Also: cost per stop, cost per km, revenue per driver-hour, route density (stops/h, stops/km), on-time % (vs promised window), failed-delivery cost, CAC, LTV and break-even stops/day.

- **Failed-delivery cost** = driver minutes × $0.50 + km × $0.17 + re-attempt cost − failed-delivery fee recovered.
- **CAC** = marketing (6400) ÷ new paying orgs from `crm.leads` converted (doc 78 attribution).
- **LTV** = average monthly contribution per org × gross margin months, retention from orders.
- **Margin colours are the same as doc 72:** green ≥ 50 %, yellow < 50 %, red ≤ 35 %. They are staff-only and never block.

## 6a. Service and claims metrics (70 §2.3; nightly in `dispatch.mv_service_quality`)

- **OTIF** = orders with ATA ≤ promised window end **and** qty_delivered = qty_ordered on every line, with no POD noted short or damaged ÷ orders delivered. Target ≥ 98 % (warehouse and partner constraint in §5); green ≥ 98 %, yellow 95–98 %, red < 95 %.
- **LIFR** = order lines filled complete ÷ order lines ordered. Only for orgs with line items (C8); otherwise it shows "n/a".
- **Dwell** = ATD − ATA per stop, as p50/p90 per site, org and driver. Free time is 30 min (warehouse constraint in §5). Minutes over free time × the doc 72 waiting rate are billed as an accessorial (revenue 4xxx). Unbilled dwell is reported as **dwell leakage $** = over-free-time minutes × $0.50/min driver cost (doc 79 §6 rate).
- **OS&D:**
  - OS&D rate = PODs noted ÷ PODs.
  - Claims cost = Σ paid claims − Σ recovered (insurer or partner chargeback), capped per claim at max(declared value, $4.41/kg) (O. Reg. 643/05 Sch. 1 art. 9–10).
  - Net claims cost is posted as COGS **5700 Cargo claims (net of recoveries)**, so it lowers contribution and EBITDA.
  - Claims past the 60-day notice deadline are flagged red.
- **Into the financials:** contribution per stop now = revenue + dwell accessorial − (driver, fuel, km) − net OS&D claims. EBITDA, ROIC and EVA pick this up through 5700.
- **Worked check (A-FIN-13):** 200 orders, 194 on time, 3 of those short → OTIF 191/200 = **95.5 % (yellow)**. A stop with ATA 10:00 and ATD 10:52 → dwell 52 min, 22 min over free time → $11.00 driver cost. One damaged claim: 12 kg, no declared value, invoice value $300 → cap $52.92 → 5700 posts $52.92.

## 7. How it is computed

- **Where:** SQL views and materialised views in the existing schemas. There is no new database and no new schema.
  - `billing.mv_pnl_monthly`, `billing.mv_ebitda`, `billing.mv_unit_economics`.
  - `dispatch.mv_route_economics`, `dispatch.mv_utilisation`.
  - `crm.mv_cac_ltv`.
  - `billing.fixed_assets` with book and CCA schedules.
- **When:** a nightly DBOS job `metrics_refresh` at 02:00 America/Toronto runs `REFRESH MATERIALIZED VIEW CONCURRENTLY`. A 5-minute DBOS job updates `dispatch.mv_utilisation` for the Kingman alert.
- **Finance parameters** (WACC, tax rate, $/h, $/km, multiples) are versioned in `platform.settings`, and each view row stores the parameter version.
- **Insights (doc 75 console, `finance` and `owner` roles):**
  - Finance dashboard: P&L, EBITDA top-down = bottom-up, margin, ROIC vs WACC, EVA, CCC, payback.
  - Per-org profitability.
  - Route economics.
  - Utilisation with the Kingman alert.
  - Unit economics and CAC/LTV.
- **Canada:** HST is excluded everywhere (it is a liability). CCA and book depreciation are both stored, and the P&L shows book. The small-business rate is 12.2 % on the first $500k.

## 8. Acceptance tests (inside G19, 76 §13 A-FIN; no new gate, so the 12 weeks are unchanged)

- **A-FIN-01:** EBITDA top-down = bottom-up to the cent on a seeded month.
- **A-FIN-02:** HST never appears in revenue or cost.
- **A-FIN-03:** the 3PL example gives 1,500,000 and 15 %.
- **A-FIN-04:** AS/RS gives ROI −70 %, simple return 30 % and payback 3.33 years.
- **A-FIN-05:** the capital project gives NOPAT 280,000, ROIC 14 % and EVA +80,000.
- **A-FIN-06:** the $77k baseline gives D&A $19,666.67 and EVA break-even 19.1 stops/day.
- **A-FIN-07:** the GTA route gives contribution $96.75, 49.8 %, yellow.
- **A-FIN-08:** a Kingman alert fires at ρ > 0.85.
- **A-FIN-09:** SS 177.7 and EOQ 1,510.4.
- **A-FIN-10:** CCC = DIO + DSO − DPO on seeded invoices and payouts.
- **A-FIN-11:** margin colour thresholds are the same as doc 72.
- **A-FIN-12:** materialised views refresh concurrently with no lock on `ordering.orders`.
- **A-FIN-13:** the §6a worked check gives OTIF 95.5 % yellow, dwell 52 min / $11.00 leakage and claim cap $52.92 posted to 5700.

## 9. Schedule (doc 60)

- **Week 9:** `billing.expenses` / `fixed_assets` / `tax_provisions` tables and the views, alongside the finance merge (A19).
- **Week 10:** Insights finance pages and the utilisation alert.
- **Weeks 10–12:** A-FIN tests green inside G19.

## 10. For Ravi

1. Confirm the assumptions: WACC 18 %, software life 3 years (or 5), Civic 5 years to $7,000, fuel $1.50/L, cash fixed about $430/month.
2. Your accountant confirms the CCA classes (12 vs 50 for the build; class 10 for the Civic).
3. Insurance cost is unknown (G-INS) and will raise every break-even.
4. At the proposed prices, a 12-stop route of S parcels is yellow (49.8 %). You can accept that, or raise density (16 stops = green) or the B2B S price (doc 72 D-72-2).
