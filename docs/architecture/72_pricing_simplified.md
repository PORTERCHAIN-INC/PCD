# 72. Pricing, simplified and explainable (Phase 0, L35)

## 1. Honest review of today's pricing (code, 29 Oct 2026)

There are **at least five overlapping price models**:

1. Whole-vehicle distance card `services/pricing-engine/porterchain_pricing/gta_rate.py:35-40`: base $45 (sedan/SUV) to $125 (box), 20 km included, $1.25–3.50/extra km, +$20 pick / +$15 drop; plus optional `weight_cents_per_kg`, `cents_per_10k_cm3` (both default 0).
2. Contract schedule (Kaylulu) `data/kaylulu_schedule_2026_09.json`: $40 pickup + per-stop by FSA tier (T1 GTA $30 / 187 FSAs, T2 $45 / 97, T3 $60 / 37), route minimums $120/$200/$250, handling tiers by lb and inch footprint (+$30, +$60, beyond +$50 more), compact sedan bands $10→$6/stop, 17 "custom quote" FSAs.
3. `price_book.py` (stop price $20 default, retail fixed price + extra parcel).
4. `fsa_card.py` / `pricing_engine/fsa_rate_card.py` and `smart_pricing.py` / `smart_apply.py` (route repricing).
5. Website calculator `marketing_site/estimate_service.py` (FSA centroid, whole-vehicle).

Verdict: **accurate but not easy.** The engine is careful (integer cents, versioned, HST separate), but a merchant cannot predict a price: units mix lb/in (contract) and kg/cm (engine); "tier", "route minimum", "handling_2", "FSA" are internal words shown to merchants (Shopify embed note `shopifyEmbed.ts:86`); there is no dimensional weight, so a light sofa prices like a box; furniture, stairs and 2-person work are not first-class add-ons; and five models can give five answers for the same job. It is _intelligent_ for Kaylulu's contract and _not intelligent_ for odd sizes or new business types.

## 2. Decision D-72-1 (decided yes, Ravi 29 Oct 2026): one engine, three readable parts

**Price = Zone base + Size band + Add-ons (all shown before booking) + HST.** Route minimums and multi-stop discounts are applied by the engine and shown as one line ("Multi-stop saving −$X" or "Minimum charge").

- **Zone** (from postal code, hidden as "Toronto", "Near GTA", "Regional"): Z1 GTA, Z2 regional, Z3 extended to 150 km; outside → manual quote.
- **Size band** on **billable weight = max(actual kg, L×W×H cm / 5000)** (industry dim factor 5000 cm³/kg; one rule, metric in the UI, inches accepted and converted):

| Band              | Billable weight      | Longest side | Examples                            |
| ----------------- | -------------------- | ------------ | ----------------------------------- |
| XS Envelope/small | ≤ 2 kg               | ≤ 40 cm      | documents, Rx bag                   |
| S Parcel          | ≤ 10 kg              | ≤ 60 cm      | flowers, gift, candles              |
| M Large parcel    | ≤ 25 kg              | ≤ 100 cm     | 20 kg pet food                      |
| L Bulky           | ≤ 50 kg              | ≤ 180 cm     | flat-pack, chair                    |
| XL Furniture      | ≤ 120 kg             | ≤ 250 cm     | sofa, mattress, dresser             |
| P Pallet          | ≤ 500 kg, 120×100 cm | —            | warehouse pallet (GS1 SSCC)         |
| Vehicle           | whole van/truck      | —            | moves, multi-pallet (gta_rate card) |

- **Add-ons (clear, upfront, toggles with price shown; approved values in §8):** 2-person (+$60), stairs per floor without elevator (+$10/floor), assembly simple (+$35) or standard (+$65), white-glove unpack (+$25), time window ≤ 2 h (+$15), same-day/rush (+$20), upright/perishable/food handling (incl. for bakery/flowers, $0, it's a promise), signature/ID (+$3), liftgate (not offered until available, contract `liftgate_available=false`), waiting beyond free time ($30/h per 15 min, B2B only, shown in contract), return to sender on failed attempt (B2B per contract; retail: one free re-attempt). **No retail cancellation fee** (D-68-5).
- **Competition Act drip pricing:** since June 2022 the Competition Act treats a price unattainable because of added mandatory fixed charges as false/misleading (s. 74.01(1.1), s. 52(1.2)); Competition Bureau guidance: https://competition-bureau.canada.ca/how-we-foster-competition/education-and-outreach/drip-pricing. Rule: every mandatory charge (fuel, zone, minimum, handling) is inside the headline price; only taxes and optional add-ons the user chooses are separate. Fuel surcharge becomes part of the zone base (reviewed monthly), not a later line.

Numbers above are the **approved starting rate card** (D-72-2 decided by Ravi on 29 Oct 2026, §8). §8 shows each margin. The yellow items are B2B S at low density and pallet; XS moved to $17 and is now green.

## 3. Rate card per business type

| Card             | Audience                                                                | Notes                                         |
| ---------------- | ----------------------------------------------------------------------- | --------------------------------------------- |
| `retail-std`     | retail customers                                                        | Stripe; card prices incl. all mandatory fees  |
| `b2b-std`        | Shopify merchants, small shops                                          | Interac monthly; −10 % vs retail on S/M bands |
| `b2b-volume`     | warehouses, supply chain                                                | route/pallet pricing, dock appointments       |
| `contract-*`     | Kaylulu (`kaylulu-2026-09` imported as contract card), future contracts | contract overrides everything                 |
| `partner-cost-*` | couriers/logistics (what we pay them)                                   | margin computed vs sell card (doc 56)         |

Margin colour bands (never block): green ≥ 50 %, yellow < 50 %, red ≤ 35 %; shown to staff on every quote/rate-card edit, never to customers.

## 4. Quote explainer UI

```
Sofa · 1 item · XL Furniture (billable 96 kg)      $129.00
 Toronto → Mississauga (Zone GTA)                  included
 2-person delivery                                  +$45.00
 Stairs: 2 floors, no elevator                      +$20.00
Total before tax                                    $194.00
HST 13%                                              $25.22
Total                                               $219.22   Valid 72 h
[Why this price?] → "Size is the bigger of weight and space it takes in the van…"
```

Shopify checkout shows one line ("PorterChain Local Delivery · $X") and the merchant's own markup/flat rule (doc 60 §13.5).

## 5. Worked examples (illustrative, Z1 GTA, before HST; Ravi to approve base prices)

Approved Z1 band bases (D-72-2): XS $17, S $18, M $26, L $49, XL $129, P $95/pallet. Z2 +$15, Z3 +$30.

| Case                                                   | Billable                                                                           | Lines                            | Price | Est. cost (driver $30/h + van $0.45/km)     | Margin      |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------------------------------- | ----- | ------------------------------------------- | ----------- |
| Furniture sofa 213×91×86 cm, 60 kg, 2 floors, 2 people | dim 333 kg → over XL by weight → XL + "oversize" handled as XL (longest 213 ≤ 250) | XL 129 + 2-person 60 + stairs 20 | $209  | 1.5 h×2 drivers $90 + 25 km $11 = $101      | 52 % green  |
| Flowers bouquet in box 40×30×60 cm, 3 kg               | dim 14.4 kg → M                                                                    | M 26 + 2 h window 15             | $41   | multi-stop share 20 min $10 + 5 km $2 = $12 | 71 % green  |
| Cake 2 kg, upright, food handling                      | S                                                                                  | S 18 + food handling 0           | $18   | $9                                          | 50 % green  |
| Pet food 20 kg bag 70×45×12 cm                         | dim 7.6, actual 20 → M                                                             | M 26                             | $26   | $12                                         | 54 % green  |
| Warehouse pallet 120×100×150 cm, 380 kg, dock appt     | P                                                                                  | P 95 + Z2 15                     | $110  | van not enough → box/partner $60 cost       | 45 % yellow |

Note on the sofa: dimensional weight would exceed XL if applied raw; furniture is priced by **item class** (XL) not dim weight above 120 kg billable, because volume is the constraint, not weight. This is the one explicit exception (D-72-3, decided yes 29 Oct 2026; item classes in §8.3). The flowers row shows why dim weight matters: a light but tall box takes van space. All five run as tests in 76 §9.

Note: the §5 examples use van costs and single-job shares. Doc 79 §4 is the baseline route model (Civic, 15 min per stop all-in); margins in §8 use it.

## 6. Migration

Phase 0 weeks 6–7: one `pricing_engine.quote()` entry; the five models become rate cards or are deleted (website calculator calls the same engine; `price_book.py` and `fsa_card.py` merged; `kaylulu_template.py` replaced by the contract card). Golden tests: Kaylulu's last 90 days of invoices reprice identically on the contract card (0 cent diff).

## 7. Decisions

- **D-72-1 decided yes** (Ravi, 29 Oct 2026): one engine.
- **D-72-2 decided** (Ravi, 29 Oct 2026): the §8 rate card was approved as recommended, with XS GTA raised to $17. Z2 and Z3 are +$15 and +$30 on every band, so XS is $32 and $47. Editing prices later goes through §9.
- **D-72-3 decided yes** (29 Oct 2026): furniture priced by item class (§8.3).
- **D-72-4 decided yes** (29 Oct 2026): fuel is inside the base price, reviewed monthly (Competition Act).

## 8. PorterChain Standard rate card v1 (D-72-2 decided, Ravi 29 Oct 2026)

**Status: DECIDED (v1, effective at Phase 0 launch).** All prices are CAD, before HST. HST 13 % (Ontario) is always shown on its own line. Every mandatory charge is inside the price shown (drip-pricing rule, §2). Cost model: driver $30/h; Civic sedan $0.17/km variable for XS/S/M ≤ 90 cm (doc 79 §0); van $0.45/km for L/XL/P (§5). Margin = (price − cost) ÷ price, with colours green ≥ 50 %, yellow < 50 %, red ≤ 35 % (staff only, never blocks).

### 8.1 Public GTA competitor prices checked 29 Oct 2026 (before HST)

| Source (URL)                                                              | Published price                                                                                                                                                                                              |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cargaroo https://cargaroo.ca/cheap-delivery-toronto                       | $5 (0–5 km), $10 (≤10 km), $25 (≤25 km), $38 (≤40 km), $55 (≤60 km); 22 lb included; Large +$12, XL +$24, heavy > 50 lb +$18; > 100 lb 2-person = delivery rate again ($60 min); waiting $1/min after 10 min |
| 1Courier https://www.1courier.com/rates.php                               | Same-day < 10 km $9.75; 2-hour $14.75; 90-min $18.75; +$0.55/km after 10 km; +$0.15/lb after the first lb                                                                                                    |
| Topping Courier https://toppingcourier.ca/services/same-day/              | From $13.99 (City ≤ 20 km); multi-drop −10 % to −20 %; charge for cancelling after the courier is on the way                                                                                                 |
| RoadRunners https://www.runtheroad.ca/furniture-assembly-and-delivery     | Furniture delivery from $135/h, 2 movers + truck, 1.5 h min ($202.50); assembly from $65/h, 1.5 h min                                                                                                        |
| Eupen Furniture https://eupen.ca/pages/shipping                           | White-glove delivery + assembly: Toronto/Mississauga/Vaughan $195; Oakville/Brampton/Markham/Scarborough $235                                                                                                |
| InStyle Home https://instylehome.ca/pages/delivery-rates                  | Same service: $295 / $325                                                                                                                                                                                    |
| Rustic Classics https://www.rusticclassics.ca/pages/shipping-and-delivery | Room-of-choice includes 2 flights; +$35 per extra flight                                                                                                                                                     |

Read: parcels sell for $10–$25 inside Toronto, so XS/S/M stay in that range. Furniture with 2 people sells for $195–$295, so XL plus 2-person ($189) sits at the low end.

### 8.2 Size bands × zones

| Band              | Z1 GTA                                                                | Z2 Regional | Z3 Extended | Z1 cost (assumption)                               | Z1 margin   |
| ----------------- | --------------------------------------------------------------------- | ----------- | ----------- | -------------------------------------------------- | ----------- |
| XS Envelope/small | $17                                                                   | $32         | $47         | Civic route stop 15 min + 3.75 km = $8.14 (79 §4)  | 52 % green  |
| S Parcel          | $18                                                                   | $33         | $48         | $8.14                                              | 55 % green  |
| M Large parcel    | $26                                                                   | $41         | $56         | Civic 18 min + 3.75 km = $9.64 (≤ 90 cm; else van) | 63 % green  |
| L Bulky           | $49                                                                   | $64         | $79         | 30 min + 10 km = $19.50                            | 60 % green  |
| XL Furniture      | $129                                                                  | $144        | $159        | 1 person 60 min + 25 km = $41.25                   | 68 % green  |
| P Pallet          | $95                                                                   | $110        | $125        | box/partner $60                                    | 37 % yellow |
| Vehicle           | `gta_rate` card unchanged ($45 sedan/SUV to $125 box, 20 km included) |             |             |                                                    |             |

Z2 adds about 20 km + 20 min ($19 cost) for $15, and Z3 adds about $30 cost for $30. A single XS or S job in Z2/Z3 shows yellow or red, so route minimums keep those jobs whole. Route minimums for `b2b-std`: $60 Z1, $90 Z2, $120 Z3 (approved). `b2b-std` takes −10 % on S/M (§3), so B2B S is $16.20 (49.8 %, yellow at 12 stops per 3 h; green from 16 stops, 79 §4) and M is $23.40 (59 %). XS is $17 Z1 (52 %, green, on the doc 79 sedan route model). Z2 and Z3 keep the same +$15 and +$30 as every band, giving $32 and $47 (D-72-2 decided).

### 8.3 Furniture item classes (D-72-3)

| Class         | Examples                                                        | Z1 price                            | Cost                     | Margin     |
| ------------- | --------------------------------------------------------------- | ----------------------------------- | ------------------------ | ---------- |
| F1 Small item | chair, nightstand, side table, lamp                             | $49                                 | $19.50                   | 60 % green |
| F2 Medium     | dresser, armchair, TV stand, desk, single/double mattress       | $89                                 | 45 min + 20 km = $31.50  | 65 % green |
| F3 Large      | 3-seat sofa, queen/king mattress + base, wardrobe, dining table | $129                                | $41.25 (1 person)        | 68 % green |
| F4 Oversize   | sectional (≤ 3 pieces), sofa bed, recliner sofa                 | $229 (2-person included, mandatory) | 1.5 h × 2 + 25 km = $101 | 56 % green |

Extra items to the same address cost 50 % of their class price. Pianos, safes and anything over 120 kg per item get a manual quote. Z2/Z3 add +$15/+$30.

### 8.4 Add-ons (optional, chosen by the customer, shown before booking)

| Add-on                              | Price                    | Cost basis              | Margin              | Competitor check                     |
| ----------------------------------- | ------------------------ | ----------------------- | ------------------- | ------------------------------------ |
| 2-person                            | +$60                     | 2nd person 1 h $30      | 50 % green          | Cargaroo $60 min; RoadRunners $135/h |
| Stairs, per floor without elevator  | +$10                     | 2 × 5 min = $5          | 50 % green          | Rustic Classics $35/flight over 2    |
| Assembly simple (≤ 30 min)          | +$35                     | $15                     | 57 % green          | RoadRunners $65/h, 1.5 h min         |
| Assembly standard (≤ 60 min)        | +$65                     | $30                     | 54 % green          | same                                 |
| White-glove unpack + packaging away | +$25                     | 10 min $5 + disposal $5 | 60 % green          | included in Eupen $195               |
| Time window ≤ 2 h                   | +$15                     | routing loss ~$6        | 60 % green          | 1Courier 2-hour $14.75               |
| Same-day rush                       | +$20                     | ~$8                     | 60 % green          | Cargaroo +40 % ($10 min)             |
| Signature / ID check                | +$3                      | 1 min                   | green               | —                                    |
| Waiting beyond free time (B2B)      | $7.50 per 15 min ($30/h) | $30/h                   | 0 % (cost recovery) | Cargaroo $1/min                      |
| Food / upright / perishable         | $0 (a promise)           | —                       | —                   | —                                    |

### 8.5 B2B cancellation fees (merchants and partners only; retail has none, D-68-5)

| When the B2B customer cancels                                                    | Fee                                                                       |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Before 18:00 the business day before (scheduled), or before dispatch (on-demand) | $0                                                                        |
| After dispatch, before the driver reaches pickup                                 | 25 % of the job price, min $15                                            |
| Driver at pickup, or goods already loaded                                        | 50 % of the job price (same as Kaylulu failed delivery), no route minimum |
| Failed delivery / return to sender                                               | per contract; `b2b-std` 50 %, re-attempt at 50 %                          |

The lawyer reviews this clause (98 U-CXL-1). Contracts override it. The Kaylulu contract has no cancellation clause, so none applies to Kaylulu without a signed amendment.

### 8.6 Kaylulu reprice to the cent (contract card `contract-kaylulu-2026-09`)

The contract card overrides every Standard number above. Every value is imported unchanged from `services/pricing-engine/porterchain_pricing/data/kaylulu_schedule_2026_09.json`: pickup $40.00; T1 $30.00 / T2 $45.00 / T3 $60.00 per stop; route minimums $120 / $200 / $250 applied to the whole bill (top-up line, `engine/__init__.py:_apply_route_minimum`); handling +$30 / +$60, beyond +$50 more; compact bands $10 → $6 per stop, $50 compact minimum; waiting $30/h in 15-min steps after 45 min pickup and 15 min stop; failed delivery 50 % (compact min $15), with no pickup, route minimum or handling inside the 50 %. Same-parcel boxes are consolidated (owner rule 2026-10-14).

| Case (van)                       | Lines                                                | Before HST | HST 13 % | Total   |
| -------------------------------- | ---------------------------------------------------- | ---------- | -------- | ------- |
| K1 5 stops T1, standard          | 40.00 + 5 × 30.00                                    | $190.00    | $24.70   | $214.70 |
| K2 2 stops T1                    | 40.00 + 60.00 = 100.00, minimum top-up 20.00         | $120.00    | $15.60   | $135.60 |
| K3 3 stops T2, one at handling_1 | 40.00 + 135.00 + 30.00                               | $205.00    | $26.65   | $231.65 |
| K4 1 stop T3 at handling_2       | 40.00 + 60.00 + 60.00 = 160.00, minimum top-up 90.00 | $250.00    | $32.50   | $282.50 |
| K5 failed delivery on a T1 stop  | 50 % × 30.00                                         | $15.00     | $1.95    | $16.95  |

K5 assumes the 50 % applies to the failed stop's line. The golden test confirms the exact base used.

Acceptance: A-PR-08. The golden test reprices Kaylulu's last 90 days of invoices on the contract card with a 0-cent difference, and K1–K5 become fixed unit tests. Compact-path cases come from the golden test, not from hand examples.

## 9. Pricing admin (Ravi, 29 Oct 2026; console screens in 75 §4)

### 9.1 Standard rate card editing (super admin only)

- The **PorterChain Standard** card holds bands × zones, add-ons, furniture classes and B2B fees (§8.2–§8.5), stored as versions.
- A draft version is edited, previewed, then published with an **effective date and time**. Published versions are immutable. A rollback publishes a copy of an older version.
- **Impact preview before publishing:** it re-prices the last 30 days of orders and every open quote on the draft. It shows the count, the average and maximum change per band and zone, and how many lines change margin colour.
- **Issued quotes are honoured:** a quote keeps the version it was priced on until its 72 h validity ends. A-LC-02 and 98 U-QT-1 cover the 30 min in code today.
- Every edit, publish and rollback writes an audit row (who, when, version, field diff, reason).

### 9.2 Pricing mode per organisation (Ravi UX refinement, 29 Oct 2026)

- **Default = PorterChain Standard.** Every organisation is on Standard (plus its business-type card from §3) and stays there until an admin switches it to Custom. Nothing else needs setting.
- **Custom is one simple screen** (75 §4). It has three quick presets that can be combined:
  1. **% off / % on all lines**, e.g. −8 %.
  2. **+/− $ per stop**, e.g. −$2.00 on every stop.
  3. **Per-band override**: a fixed price for one band or zone, e.g. S Z1 = $16.
- **Advanced** (collapsed by default): a full custom card (Kaylulu = the custom contract card `contract-kaylulu-2026-09`, §8.6) or per-line overrides (fixed price or %) on add-ons, furniture classes and fees.
- **Live preview** on the same screen shows a sample basket (one order per band in Z1, plus a 12-stop route). For each it gives Standard price → custom price, the HST line, and the margin colour on the doc 79 route model: green ≥ 50 %, yellow 35–50 %, red < 35 %.
- **Guardrails:**
  - Each line has a min/max, −30 % to +50 % of Standard, unless the super admin widens it.
  - Yellow warns. **Red needs a written reason** before saving.
  - Effective and expiry dates are set. On expiry the org falls back to Standard, with an alert 14 days before.
  - A **contract link** to the signed document in Documents is required to save.
- **Send quote now:** a button on the same screen, also usable on the merchant's request. It instantly creates a **72 h quote** on the custom card for the lanes and bands chosen, sends it to the merchant (email plus portal) as the §4 explainer PDF, and pins the card version.
- **One pricing engine everywhere:** the existing `pricing_engine.get_pricing_service()` (porterchain_pricing) resolves `org_pricing` → card version → overrides. Every channel calls only that service:

| Channel                             | Today (code, 29 Oct 2026)                                                                                                  | Rule                                                                                                                                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Shopify carrier-calculated rates    | `POST /v1/integrations/shopify/carrier-service/rates` → `integrations/shopify_carrier_rates.py` → `get_pricing_service`    | Same service, org resolved from the shop. The rate shown at checkout is stored as the quote (`ShopifyRateQuote`) with the card version                                                                                   |
| Shopify flat-rate fallback          | **Not in the code** (gap)                                                                                                  | Build: on publish, or on a mode or override change, write the merchant's zone × band prices from the engine into a Shopify delivery profile (Admin GraphQL). Checkout shows them only if the callback fails or times out |
| Website quote, merchant portal, API | `routers/quotes.py`, `merchant_engine/booking_service.py`, `import_quote.py` → `get_pricing_service`                       | Same service; the merchant-api uses the merchant's org pricing                                                                                                                                                           |
| Admin simulate                      | `POST /v1/pricing/simulate` (`routers/pricing_admin.py`)                                                                   | Becomes the live preview backend                                                                                                                                                                                         |
| Invoice                             | `InvoiceService.finalize_after_pod` uses the stored order price + contract accessorials (`billing_engine/accessorials.py`) | Invoice line = the accepted quote price at its pinned version (plus any consented §9.3 adjustment). The invoice never re-prices                                                                                          |

### 9.3 Manual price change on one quote or order

- **Who:** an admin, as limited by the §9.4 role rules.
- **What:** an increase or a decrease, as a new amount or a %, with a reason picked from a list plus free text. It writes an audit row with before/after, user and time.
- **Before acceptance** (quote, or order not yet accepted): the new price replaces the quote, and the customer or merchant is notified by email/in-app with the explainer (§4).
- **After acceptance:**
  - A decrease applies straight away and is notified; a refund or credit goes out if already paid.
  - An **increase needs the payer's consent**: an accept link, with nothing charged until they accept. If declined, the original price stands, or ops can cancel with no cancellation fee.
- HST is always recomputed on its own line; no drip pricing (§2).

### 9.4 Who can change prices (SpiceDB, 75 §2 roles)

| Action                                     | owner / super admin | finance         | dispatcher / support           | sales                                |
| ------------------------------------------ | ------------------- | --------------- | ------------------------------ | ------------------------------------ |
| Edit/publish the Standard card             | yes                 | no (view)       | no                             | no                                   |
| Create/edit a custom card or org overrides | yes                 | no (view)       | no                             | propose only (draft, owner approves) |
| Change the pricing mode on an org          | yes                 | no              | no                             | no                                   |
| Per-order adjustment                       | any amount          | ±25 %, max $100 | ±10 %, max $25; decreases only | no                                   |

The limits are config values on `platform`. A change outside your limit becomes a request to the owner.

### 9.5 Data model (schema `pricing`)

```text
rate_cards(id, code, kind[standard|business_type|custom], org_id NULL, contract_document_id NULL, created_by, created_at)
rate_card_versions(id, rate_card_id, version, status[draft|published|retired], effective_from, effective_to NULL,
                   lines JSONB  -- bands×zones, add_ons, furniture_classes, b2b_fees
                   , published_by, published_at, notes)
org_pricing(org_id PK, mode[standard|custom] DEFAULT standard, preset_pct NULL, preset_per_stop_cents NULL, rate_card_id NULL, effective_from, expires_at NULL, updated_by, updated_at)
price_overrides(id, org_id, rate_card_version_id, line_key, kind[fixed|pct], value, min_value, max_value,
                margin_colour, reason NULL, effective_from, expires_at NULL, created_by)
price_adjustments(id, quote_id NULL, order_id NULL, before_cents, after_cents, direction, reason_code, reason_text,
                  consent_status[n/a|pending|accepted|declined], actor_id, created_at)
pricing_audit(id, entity, entity_id, action, diff JSONB, actor_id, reason, created_at)
quotes.rate_card_version_id  -- pins the version for the 72 h validity
```

### 9.6 API

Existing admin pricing prefix is `/v1/pricing` (`routers/pricing_admin.py`); the new routes extend it.

- `GET/POST /v1/pricing/rate-cards`, `GET /v1/pricing/rate-cards/{id}/versions`
- `POST /v1/pricing/rate-cards/{id}/versions` (create a draft) · `PATCH .../versions/{v}` (edit the draft)
- `POST .../versions/{v}/preview` (impact report) · `POST .../versions/{v}/publish` with `effective_from` · `POST .../versions/{v}/rollback`
- `GET/PUT /v1/pricing/orgs/{org_id}` (mode, presets, card, dates) · `GET/POST/DELETE /v1/pricing/orgs/{org_id}/overrides` · `POST /v1/pricing/orgs/{org_id}/preview` (live preview) · `POST /v1/pricing/orgs/{org_id}/send-quote` (72 h quote now)
- `POST /v1/admin/quotes/{quote_id}/adjust` · `POST /v1/admin/orders/{order_id}/adjust` (returns `consent_required`)
- `GET /v1/pricing/audit?entity=&from=&to=`
- Merchant request: `POST /v1/merchant/quote-requests` (the request lands in the admin's Custom screen; the reply is "send quote now")
- Consent link for the merchant or customer: `POST /v1/merchant/orders/{order_id}/price-change/{adjustment_id}/accept|decline`
- Webhook: `order.price_changed` (doc 74 §4)

Tests: 76 §19 (A-PRA).
