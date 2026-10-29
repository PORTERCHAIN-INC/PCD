# 41 · UI page specs — Shopify embedded app

Polaris web components (App Bridge + `s-*` elements, Polaris 2025-10+), embedded in Shopify admin; served from `apps/merchant-portal/src/app/shopify-app/route.ts` + `(portal)/shopify/page.tsx`; listing in `integrations/shopify/listing`. Must meet **Built for Shopify**: LCP < 2.5 s, CLS < 0.1, INP < 200 ms, app home uses Polaris, no external redirects for core tasks. Plan: doc 24.

Inherits: Polaris states (`s-spinner`/skeleton, empty `s-empty-state`, `s-banner` critical/warning), Polaris a11y (WCAG 2.2 AA), EN/FR via Shopify locale, responsive inside admin (mobile Shopify app too), light admin theme.

| #   | Screen                  | Purpose                                                                      | Layout / components                            | Key actions                                  | Data (API)                                                                | Validation / errors / states                                                            |
| --- | ----------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 8.1 | Install / OAuth         | Connect store to PorterChain merchant                                        | Full-page loader → `s-page`                    | Approve scopes                               | Shopify OAuth, `/v1/shopify/install`                                      | HMAC fail → "Install link expired, retry from Shopify admin"                            |
| 8.2 | App home (Connected)    | Status, today's deliveries, setup checklist                                  | `s-page`, `s-section`, `s-card`, checklist     | Finish setup, open orders                    | `/v1/shopify/status`, `/v1/merchant/orders/dashboard`                     | Empty: "No PorterChain orders yet"                                                      |
| 8.3 | Orders                  | Shopify orders eligible for PorterChain delivery                             | `s-table` (index table), filters, bulk actions | Send to PorterChain, bulk book, retry failed | `/v1/shopify/orders`, webhooks `orders/create` (idempotent by webhook id) | Duplicate webhook ignored; address outside area → warning badge                         |
| 8.4 | Order detail            | One order's delivery, tracking, POD                                          | `s-page` + timeline + map thumbnail            | Book, cancel, view POD, open claim           | `/v1/merchant/orders/{id}`                                                | —                                                                                       |
| 8.5 | Checkout settings       | Delivery window + rate display at checkout; hide services an order can't use | Form cards, Checkout UI extension preview      | Save rules                                   | Carrier Service / Delivery Customization fn                               | Window must be in service hours                                                         |
| 8.6 | Settings                | Pickup location, default vehicle, notifications, language                    | `s-form`, `s-select`, `s-switch`               | Save, disconnect                             | `/v1/shopify/settings`                                                    | Required pickup address                                                                 |
| 8.7 | Billing                 | Show PorterChain invoices; Interac payment instructions                      | `s-table`, `s-banner`                          | Download PDF                                 | `/v1/merchant/billing/invoices`                                           | **Decision:** Shopify Billing API may be required for app charges vs Interac-only (L10) |
| 8.8 | Help / onboarding       | Guide, support                                                               | `s-card` links                                 | Contact support                              | `/v1/support/tickets`                                                     | —                                                                                       |
| 8.9 | Order-intake agent card | Agent suggestion inside order detail                                         | `s-card` with Approve/Reject                   | Approve                                      | agent approvals API                                                       | Human approval for the six cases                                                        |

Total: 9 screens.

## Trust & Help placement (doc 68)

### S.T1 `/app/help + /app/policies + onboarding step 1`

- **File:** `shopify app embedded routes` (planned, doc 68)
- **Purpose:** Onboarding 'How PorterChain works' (scopes and data use, Interac billing not Shopify, rate rules, service area, prohibited items) + accept MSA/DPA/Shopify App Privacy Policy; Help and Policies pages in Polaris
- **Role:** Shopify merchant (staff with app access)
- **Layout:** PorterChain header, breadcrumb, left section nav (desktop) / section select (phone), article, "Last updated · version" line, related policies, Contact CTA
- **Components:** Polaris Page, Card, Checkbox, Banner, List
- **Key actions:** Accept, read, contact
- **Data (API):** content `GET /v1/trust/help?persona=&locale=` / `GET /v1/trust/policies/:slug?version=` (doc 68 §6)
- **Validation / errors:** Not accepted → app features locked except help
- **States:** onboarding; accepted; re-consent
- **Responsive:** Phone single column with sticky search; tablet 2 col; laptop+ 3 col (nav, article, on-this-page)
- **A11y / i18n / theme:** WCAG 2.2 AA, one `<h1>`, skip link, plain language; EN/FR from `content/trust/` (FR "translation pending" banner until D-68-2); legal text marked DRAFT until lawyer sign-off
