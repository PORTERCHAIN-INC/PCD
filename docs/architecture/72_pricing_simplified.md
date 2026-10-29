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

- **Add-ons (clear, upfront, toggles with price shown; proposed values in §8):** 2-person (+$60), stairs per floor without elevator (+$10/floor), assembly simple (+$35) or standard (+$65), white-glove unpack (+$25), time window ≤ 2 h (+$15), same-day/rush (+$20), upright/perishable/food handling (incl. for bakery/flowers, $0, it's a promise), signature/ID (+$3), liftgate (not offered until available, contract `liftgate_available=false`), waiting beyond free time ($30/h per 15 min, B2B only, shown in contract), return to sender on failed attempt (B2B per contract; retail: one free re-attempt). **No retail cancellation fee** (D-68-5).
- **Competition Act drip pricing:** since June 2022 the Competition Act treats a price unattainable because of added mandatory fixed charges as false/misleading (s. 74.01(1.1), s. 52(1.2)); Competition Bureau guidance: https://competition-bureau.canada.ca/how-we-foster-competition/education-and-outreach/drip-pricing. Rule: every mandatory charge (fuel, zone, minimum, handling) is inside the headline price; only taxes and optional add-ons the user chooses are separate. Fuel surcharge becomes part of the zone base (reviewed monthly), not a later line.

Numbers above are **PROPOSED starting values for Ravi's review** (D-72-2, §8), not final; each passes the margin check in §8.

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

Proposed Z1 band bases: XS $14, S $18, M $26, L $49, XL $129, P $95/pallet. Z2 +$15, Z3 +$30.

| Case                                                   | Billable                                                                           | Lines                            | Price | Est. cost (driver $30/h + van $0.45/km)     | Margin      |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------------------------------- | ----- | ------------------------------------------- | ----------- |
| Furniture sofa 213×91×86 cm, 60 kg, 2 floors, 2 people | dim 333 kg → over XL by weight → XL + "oversize" handled as XL (longest 213 ≤ 250) | XL 129 + 2-person 60 + stairs 20 | $209  | 1.5 h×2 drivers $90 + 25 km $11 = $101      | 52 % green  |
| Flowers bouquet in box 40×30×60 cm, 3 kg               | dim 14.4 kg → M                                                                    | M 26 + 2 h window 15             | $41   | multi-stop share 20 min $10 + 5 km $2 = $12 | 71 % green  |
| Cake 2 kg, upright, food handling                      | S                                                                                  | S 18 + food handling 0           | $18   | $9                                          | 50 % green  |
| Pet food 20 kg bag 70×45×12 cm                         | dim 7.6, actual 20 → M                                                             | M 26                             | $26   | $12                                         | 54 % green  |
| Warehouse pallet 120×100×150 cm, 380 kg, dock appt     | P                                                                                  | P 95 + Z2 15                     | $110  | van not enough → box/partner $60 cost       | 45 % yellow |

Note on the sofa: dimensional weight would exceed XL if applied raw; furniture is priced by **item class** (XL) not dim weight above 120 kg billable, because volume is the constraint, not weight. This is the one explicit exception (D-72-3, decided yes 29 Oct 2026; item classes in §8.3). The flowers row shows why dim weight matters: a light but tall box takes van space. All five run as tests in 76 §9.

## 6. Migration

Phase 0 weeks 6–7: one `pricing_engine.quote()` entry; the five models become rate cards or are deleted (website calculator calls the same engine; `price_book.py` and `fsa_card.py` merged; `kaylulu_template.py` replaced by the contract card). Golden tests: Kaylulu's last 90 days of invoices reprice identically on the contract card (0 cent diff).

## 7. Decisions

- **D-72-1 decided yes** (Ravi, 29 Oct 2026): one engine.
- **D-72-2 PROPOSED, for Ravi's review:** Ravi said "you propose prices, I'll review". The proposed rate card is in §8. Nothing in it is final until Ravi approves.
- **D-72-3 decided yes** (29 Oct 2026): furniture priced by item class (§8.3).
- **D-72-4 decided yes** (29 Oct 2026): fuel is inside the base price, reviewed monthly (Competition Act).

## 8. PROPOSED starting rate card (D-72-2, for Ravi's review, 29 Oct 2026)

**Status: PROPOSED.** All prices are CAD, before HST. HST 13 % (Ontario) is always shown on its own line. Every mandatory charge is inside the price shown (drip-pricing rule, §2). Cost model (§5): driver $30/h, van $0.45/km. Margin = (price − cost) ÷ price, with colours green ≥ 50 %, yellow < 50 %, red ≤ 35 % (staff only, never blocks).

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

| Band              | Z1 GTA                                                                | Z2 Regional | Z3 Extended | Z1 cost (assumption)             | Z1 margin   |
| ----------------- | --------------------------------------------------------------------- | ----------- | ----------- | -------------------------------- | ----------- |
| XS Envelope/small | $14                                                                   | $29         | $44         | route stop 10 min + 3 km = $6.35 | 55 % green  |
| S Parcel          | $18                                                                   | $33         | $48         | $6.35                            | 65 % green  |
| M Large parcel    | $26                                                                   | $41         | $56         | 15 min + 3 km = $8.85            | 66 % green  |
| L Bulky           | $49                                                                   | $64         | $79         | 30 min + 10 km = $19.50          | 60 % green  |
| XL Furniture      | $129                                                                  | $144        | $159        | 1 person 60 min + 25 km = $41.25 | 68 % green  |
| P Pallet          | $95                                                                   | $110        | $125        | box/partner $60                  | 37 % yellow |
| Vehicle           | `gta_rate` card unchanged ($45 sedan/SUV to $125 box, 20 km included) |             |             |                                  |             |

Z2 adds about 20 km + 20 min ($19 cost) for $15, and Z3 adds about $30 cost for $30. A single XS or S job in Z2/Z3 shows yellow or red, so route minimums keep those jobs whole. Route minimums for `b2b-std`: $60 Z1, $90 Z2, $120 Z3 (proposed). `b2b-std` takes −10 % on S/M (§3), so B2B S is $16.20 (61 %) and M is $23.40 (62 %).

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

The contract card overrides every proposed number above. Every value is imported unchanged from `services/pricing-engine/porterchain_pricing/data/kaylulu_schedule_2026_09.json`: pickup $40.00; T1 $30.00 / T2 $45.00 / T3 $60.00 per stop; route minimums $120 / $200 / $250 applied to the whole bill (top-up line, `engine/__init__.py:_apply_route_minimum`); handling +$30 / +$60, beyond +$50 more; compact bands $10 → $6 per stop, $50 compact minimum; waiting $30/h in 15-min steps after 45 min pickup and 15 min stop; failed delivery 50 % (compact min $15), with no pickup, route minimum or handling inside the 50 %. Same-parcel boxes are consolidated (owner rule 2026-10-14).

| Case (van)                       | Lines                                                | Before HST | HST 13 % | Total   |
| -------------------------------- | ---------------------------------------------------- | ---------- | -------- | ------- |
| K1 5 stops T1, standard          | 40.00 + 5 × 30.00                                    | $190.00    | $24.70   | $214.70 |
| K2 2 stops T1                    | 40.00 + 60.00 = 100.00, minimum top-up 20.00         | $120.00    | $15.60   | $135.60 |
| K3 3 stops T2, one at handling_1 | 40.00 + 135.00 + 30.00                               | $205.00    | $26.65   | $231.65 |
| K4 1 stop T3 at handling_2       | 40.00 + 60.00 + 60.00 = 160.00, minimum top-up 90.00 | $250.00    | $32.50   | $282.50 |
| K5 failed delivery on a T1 stop  | 50 % × 30.00                                         | $15.00     | $1.95    | $16.95  |

K5 assumes the 50 % applies to the failed stop's line. The golden test confirms the exact base used.

Acceptance: A-PR-08. The golden test reprices Kaylulu's last 90 days of invoices on the contract card with a 0-cent difference, and K1–K5 become fixed unit tests. Compact-path cases come from the golden test, not from hand examples.
