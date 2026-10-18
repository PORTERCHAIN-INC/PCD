# GA4 weekly funnel (website)

Events are sent only after the visitor accepts analytics cookies (`trackConversion`, PIPEDA / CASL safe). No ad pixels.

| Event                       | Fires when                                                                            | Key params                                               |
| --------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `price_requested`           | Visitor submits two postal codes + a vehicle (home hero or /delivery-cost-calculator) | `vehicle`, `pickup_fsa`, `dropoff_fsa`, `source_section` |
| `calculator_estimate`       | A price is shown                                                                      | `vehicle`, `amount_cents`, `source_section`              |
| `price_out_of_area`         | Pickup or drop-off is outside the 150 km coverage                                     | `reason`, `pickup_fsa`, `dropoff_fsa`                    |
| `book_started`              | "Book" is clicked on a priced trip (hand-off to /book)                                | `vehicle`, `amount_cents`, `source_section`              |
| `calculator_lead_submitted` | Lead form on the calculator page                                                      | `vehicle`, `industry`                                    |
| `cta_click`                 | Any tracked CTA (hero "Get instant price", "Book now")                                | `cta_source`, `cta_label`                                |
| `shopify_cta_click`         | Reserved for the Shopify app CTA once the listing is live                             |                                                          |

## One-time GA4 setup (Ravi, 5 minutes)

1. Admin → Events → mark `calculator_estimate` and `book_started` as key events.
2. Admin → Custom definitions → add event-scoped dimensions `source_section`, `vehicle`, `pickup_fsa`, `reason`.
3. Explore → Funnel: `page_view` (/en) → `price_requested` → `calculator_estimate` → `book_started`. Save as "Weekly price-to-book".

## Weekly review (Monday, 15 minutes)

1. Price-to-book rate: `book_started` / `calculator_estimate`. Move one thing per week (hero line, CTA label, calculator default vehicle) and note the date.
2. `price_out_of_area` by `pickup_fsa`: repeated FSAs are demand outside coverage; decide whether to serve them.
3. Search Console: impressions and clicks for the keyword map in `website-copy-deck.md`.
4. Keep a one-line log: date, change, before/after rate.
