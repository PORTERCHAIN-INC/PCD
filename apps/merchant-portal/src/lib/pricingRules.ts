/** Plain-English pricing rules for contract (Schedule of Rates) merchants. */
export const PRICING_RULES: { title: string; body: string }[] = [
  {
    title: "A stop is one delivery address",
    body: "Everything going to the same address on one route is one stop. Two drop-offs entered for the same address are merged.",
  },
  {
    title: "One parcel can be several boxes",
    body: 'When one item ships in several boxes, we add the boxes together: total weight, and their combined size and volume. That combined parcel is priced once. Separate parcels (different items) to the same address are each charged as a stop, as in your Schedule of Rates (A3). Small parcels up to 12" × 12" share a stop, up to 3 per stop.',
  },
  {
    title: "Location rate (by postal code)",
    body: "Van: GTA Tier 1 $30 per stop, Regional Tier 2 $45, Extended Tier 3 $60. The first three characters of the postal code (FSA) decide the tier.",
  },
  {
    title: "Heavy or large parcels",
    body: 'Judged on the combined parcel, by the higher of weight or footprint: Standard up to 100 lb / 70" × 45" — no extra. Tier 1 up to 125 lb / 80" × 45" — +$30. Tier 2 up to 150 lb / 90" × 50" — +$60. Tier 3 above that — Tier 2 charge + $50 (+$110), priced automatically.',
  },
  {
    title: "Pickup and route minimum",
    body: "Van routes add $40 for the Milton pickup, once per route. If pickup + stops + heavy charges is below the route minimum ($120 Tier 1, $200 Tier 2, $250 Tier 3 — the highest tier on the route), you pay the minimum. Sedan/SUV (compact) routes: $10 per stop (fewer than 5 stops, $10 pickup) or $6 per stop (5 or more), $50 minimum.",
  },
  {
    title: "Extras and tax",
    body: "Waiting beyond the included time and enhanced coverage are added only when used. HST is extra. The price shown when you book is locked.",
  },
  {
    title: "Driver safety",
    body: 'Drivers lift each box on its own: a box over 50 lb is flagged for two-person handling, and a box over 65 lb or 36" × 36" needs handling equipment at pickup (Term 05). This does not change the price.',
  },
];

export const PRICING_EXAMPLE =
  "Example: 1 parcel in 2 boxes (18 kg total) to Oakville L6H → 1 stop × $30 + $40 pickup = $70, below the $120 Tier 1 minimum → $120 + HST.";
