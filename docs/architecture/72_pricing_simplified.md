# 72. Pricing, simplified and explainable (Phase 0, L35)

## 1. Honest review of today's pricing (code, 29 Oct 2026)

There are **at least five overlapping price models**:

1. Whole-vehicle distance card `services/pricing-engine/porterchain_pricing/gta_rate.py:35-40`: base $45 (sedan/SUV) to $125 (box), 20 km included, $1.25–3.50/extra km, +$20 pick / +$15 drop; plus optional `weight_cents_per_kg`, `cents_per_10k_cm3` (both default 0).
2. Contract schedule (Kaylulu) `data/kaylulu_schedule_2026_09.json`: $40 pickup + per-stop by FSA tier (T1 GTA $30 / 187 FSAs, T2 $45 / 97, T3 $60 / 37), route minimums $120/$200/$250, handling tiers by lb and inch footprint (+$30, +$60, beyond +$50 more), compact sedan bands $10→$6/stop, 17 "custom quote" FSAs.
3. `price_book.py` (stop price $20 default, retail fixed price + extra parcel).
4. `fsa_card.py` / `pricing_engine/fsa_rate_card.py` and `smart_pricing.py` / `smart_apply.py` (route repricing).
5. Website calculator `marketing_site/estimate_service.py` (FSA centroid, whole-vehicle).

Verdict: **accurate but not easy.** The engine is careful (integer cents, versioned, HST separate), but a merchant cannot predict a price: units mix lb/in (contract) and kg/cm (engine); "tier", "route minimum", "handling_2", "FSA" are internal words shown to merchants (Shopify embed note `shopifyEmbed.ts:86`); there is no dimensional weight, so a light sofa prices like a box; furniture, stairs and 2-person work are not first-class add-ons; and five models can give five answers for the same job. It is _intelligent_ for Kaylulu's contract and _not intelligent_ for odd sizes or new business types.

## 2. Decision D-72-1: one engine, three readable parts

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

- **Add-ons (clear, upfront, toggles with price shown):** 2-person (+$45), stairs per floor without elevator (+$10/floor), assembly/room placement (+$35), white-glove unpack (+$25), time window ≤ 2 h (+$15), same-day/rush (+$20), upright/perishable/food handling (incl. for bakery/flowers, $0, it's a promise), signature/ID (+$3), liftgate (not offered until available, contract `liftgate_available=false`), waiting beyond free time ($30/h per 15 min, B2B only, shown in contract), return to sender on failed attempt (B2B per contract; retail: one free re-attempt). **No retail cancellation fee** (D-68-5).
- **Competition Act drip pricing:** since June 2022 the Competition Act treats a price unattainable because of added mandatory fixed charges as false/misleading (s. 74.01(1.1), s. 52(1.2)); Competition Bureau guidance: https://competition-bureau.canada.ca/how-we-foster-competition/education-and-outreach/drip-pricing. Rule: every mandatory charge (fuel, zone, minimum, handling) is inside the headline price; only taxes and optional add-ons the user chooses are separate. Fuel surcharge becomes part of the zone base (reviewed monthly), not a later line.

Numbers above are **starting values for Ravi's approval** (D-72-2), not final; they must pass the margin check.

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
| Furniture sofa 213×91×86 cm, 60 kg, 2 floors, 2 people | dim 333 kg → over XL by weight → XL + "oversize" handled as XL (longest 213 ≤ 250) | XL 129 + 2-person 45 + stairs 20 | $194  | 1.5 h×2 drivers $90 + 25 km $11 = $101      | 48 % yellow |
| Flowers bouquet in box 40×30×60 cm, 3 kg               | dim 14.4 kg → M                                                                    | M 26 + 2 h window 15             | $41   | multi-stop share 20 min $10 + 5 km $2 = $12 | 71 % green  |
| Cake 2 kg, upright, food handling                      | S                                                                                  | S 18 + food handling 0           | $18   | $9                                          | 50 % green  |
| Pet food 20 kg bag 70×45×12 cm                         | dim 7.6, actual 20 → M                                                             | M 26                             | $26   | $12                                         | 54 % green  |
| Warehouse pallet 120×100×150 cm, 380 kg, dock appt     | P                                                                                  | P 95 + Z2 15                     | $110  | van not enough → box/partner $60 cost       | 45 % yellow |

Note on the sofa: dimensional weight would exceed XL if applied raw; furniture is priced by **item class** (XL) not dim weight above 120 kg billable, because volume is the constraint, not weight. This is the one explicit exception (D-72-3). The flowers row shows why dim weight matters: a light but tall box takes van space. All five run as tests in 76 §9.

## 6. Migration

Phase 0 weeks 6–7: one `pricing_engine.quote()` entry; the five models become rate cards or are deleted (website calculator calls the same engine; `price_book.py` and `fsa_card.py` merged; `kaylulu_template.py` replaced by the contract card). Golden tests: Kaylulu's last 90 days of invoices reprice identically on the contract card (0 cent diff).

## 7. Decisions for Ravi

D-72-1 one engine (recommend yes) · D-72-2 approve starting band and add-on prices · D-72-3 furniture by item class · D-72-4 fuel inside base price, reviewed monthly (recommend yes, Competition Act).
