> **DRAFT for lawyer review — verify every DPA is actually signed and each region setting is correct before publishing.**

# PorterChain Subprocessor List

| Subprocessor         | What it does for us                                                            | Data involved                                                   | Location                                | DPA                             |
| -------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------- | --------------------------------------- | ------------------------------- |
| DigitalOcean         | Hosting: API, database, Redis, self-hosted Valhalla/OSRM maps                  | All service data                                                | Canada (Toronto); EU option (Frankfurt) | Standard DPA — confirm accepted |
| Clerk                | Sign-in, user accounts                                                         | Name, email, phone, sign-in metadata                            | USA                                     | Confirm                         |
| Stripe               | Card payments, payouts                                                         | Billing name, email, payment details (card data held by Stripe) | USA / Ireland                           | Stripe DPA (auto)               |
| ZeptoMail (Zoho)     | Transactional and opt-in email                                                 | Name, email, message content                                    | Account region — confirm (US/EU/IN)     | Confirm                         |
| Twilio               | SMS alerts (only when enabled)                                                 | Phone, message content                                          | USA                                     | Confirm                         |
| Shopify              | Merchant store integration (Shopify is an independent controller of shop data) | Order and recipient details the merchant shares                 | Canada / USA                            | Shopify Partner terms           |
| Sentry               | Error monitoring                                                               | Technical data; personal data may appear incidentally in errors | USA                                     | Confirm; enable data scrubbing  |
| Cloudflare           | DNS; R2 storage for blog media                                                 | Public media; IP addresses                                      | Global                                  | Confirm                         |
| Google Maps Platform | Address lookup fallback (only if a key is set)                                 | Address text                                                    | USA                                     | Google terms                    |
| Expo (EAS)           | Driver app builds, push notifications                                          | Push tokens                                                     | USA                                     | Confirm                         |
| Doppler              | Secrets management                                                             | No customer data (credentials only)                             | USA                                     | Confirm                         |

Not subprocessors (run on our own servers): Valhalla and OSRM routing, map-matching, isochrones, OpenStreetMap data, and VROOM/OR-Tools route optimisation.
Removed: NVIDIA (no longer used).

_Last reviewed: [date] — DRAFT_
