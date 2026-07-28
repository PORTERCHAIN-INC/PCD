# Analytics Event Taxonomy

**Module:** `website/src/lib/seo/analytics.ts`  
**Attribution:** `website/src/lib/seo/attribution.ts`  
**Architecture:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md)

---

## Pipeline

```
User action
  → track(ANALYTICS_EVENTS.*, { sourceSection, … })
  → merge getStoredAttribution()
  → provider (gtag / GA4) or queue until flushQueuedAnalyticsEvents()
```

Set provider in layout/client bootstrap via `setAnalyticsProvider()`.

---

## Event catalog

All event names are lowercase snake_case strings in `ANALYTICS_EVENTS`:

| Constant                            | Event name                          | Typical trigger                    |
| ----------------------------------- | ----------------------------------- | ---------------------------------- |
| `CTA_CLICK`                         | `cta_click`                         | Navbar/footer/book CTAs            |
| `MERCHANT_WIZARD_STEP_VIEW`         | `merchant_wizard_step_view`         | Business onboarding wizard         |
| `MERCHANT_WIZARD_SUBMIT_SUCCESS`    | `merchant_wizard_submit_success`    | Wizard complete                    |
| `MERCHANT_WIZARD_SUBMIT_ERROR`      | `merchant_wizard_submit_error`      | Wizard validation/API error        |
| `DRIVER_APPLICATION_STEP_VIEW`      | `driver_application_step_view`      | Drive/vehicle partner flow         |
| `DRIVER_APPLICATION_SUBMIT_SUCCESS` | `driver_application_submit_success` | Application sent                   |
| `DRIVER_APPLICATION_SUBMIT_ERROR`   | `driver_application_submit_error`   | Application error                  |
| `TRACKING_LOOKUP`                   | `tracking_lookup`                   | Track page search                  |
| `TRACKING_LOOKUP_SUCCESS`           | `tracking_lookup_success`           | Order found                        |
| `TRACKING_LOOKUP_NOT_FOUND`         | `tracking_lookup_not_found`         | Unknown tracking ID                |
| `TRACKING_LOOKUP_ERROR`             | `tracking_lookup_error`             | API error                          |
| `SUPPORT_ISSUE_SUBMIT_SUCCESS`      | `support_issue_submit_success`      | Support form                       |
| `SUPPORT_ISSUE_SUBMIT_ERROR`        | `support_issue_submit_error`        | Support form error                 |
| `CONTACT_FORM_SUBMIT_SUCCESS`       | `contact_form_submit_success`       | Contact page                       |
| `CONTACT_FORM_SUBMIT_ERROR`         | `contact_form_submit_error`         | Contact form error                 |
| `DEMO_REQUEST`                      | `demo_request`                      | Legacy demo CTAs                   |
| `QUOTE_REQUEST`                     | `quote_request`                     | Quote CTAs                         |
| `SEO_BRIDGE_CLICK`                  | `seo_bridge_click`                  | Lane B → platform bridge           |
| `PLATFORM_EXPLORE`                  | `platform_explore`                  | Platform exploration from SEO page |
| `BOOKING_QUOTE_REQUEST`             | `booking_quote_request`             | Booking widget quote start         |
| `BOOKING_QUOTE_SUCCESS`             | `booking_quote_success`             | Quote returned                     |
| `BOOKING_CONTINUE`                  | `booking_continue`                  | Proceed to checkout                |
| `BUSINESS_INQUIRY_SUBMIT`           | `business_inquiry_submit`           | Business page form                 |
| `DRIVER_PARTNER_INQUIRY_SUBMIT`     | `driver_partner_inquiry_submit`     | Vehicle partner form               |
| `ZOHO_CHAT_READY`                   | `zoho_chat_ready`                   | SalesIQ loaded                     |
| `ZOHO_CHAT_OPEN`                    | `zoho_chat_open`                    | Chat opened                        |
| `GBP_PROFILE_CLICK`                 | `gbp_profile_click`                 | Google Business Profile link       |
| `GBP_REVIEW_CLICK`                  | `gbp_review_click`                  | Leave a review link                |
| `WEB_VITAL`                         | `web_vital`                         | CWV RUM sample                     |
| `WEB_VITAL_BUDGET_EXCEEDED`         | `web_vital_budget_exceeded`         | Over perf budget                   |
| `WHATSAPP_QUOTE_CLICK`              | `whatsapp_quote_click`              | Pre-filled WhatsApp quote          |
| `WHATSAPP_CHAT_CLICK`               | `whatsapp_chat_click`               | Mobile WhatsApp FAB                |

---

## GA4 conversions

Mark these in **GA4 Admin → Events → Mark as conversion** (`GA4_CONVERSION_EVENTS`):

| Event                           | Business meaning         |
| ------------------------------- | ------------------------ |
| `contact_form_submit_success`   | Direct lead              |
| `demo_request`                  | Sales-qualified interest |
| `quote_request`                 | Capacity request         |
| `business_inquiry_submit`       | B2B pipeline             |
| `driver_partner_inquiry_submit` | Supply-side lead         |
| `booking_quote_success`         | Retail quote             |
| `booking_continue`              | Checkout intent          |
| `zoho_chat_open`                | Live chat engagement     |
| `whatsapp_chat_click`           | Mobile chat engagement   |
| `gbp_review_click`              | Reputation / local       |

Non-conversion events still inform funnel analysis (wizard steps, tracking lookups, SEO bridge).

---

## Attribution properties

Auto-merged on every `track()` call from `attribution.ts`:

| Property         | Source                                                         |
| ---------------- | -------------------------------------------------------------- |
| `sourcePage`     | Pathname minus locale (e.g. `industry/construction-materials`) |
| `sourceSection`  | Optional — passed by component (hero, footer, bridge)          |
| `from`           | Last-touch `?from=` query param                                |
| `locale`         | `en` / `fr`                                                    |
| `market`         | Optional market segment                                        |
| `landingPageUrl` | First page in session                                          |
| `referrer`       | `document.referrer`                                            |
| `utm_source`     | UTM params                                                     |
| `utm_medium`     | UTM params                                                     |
| `utm_campaign`   | UTM params                                                     |
| `utm_term`       | UTM params                                                     |
| `utm_content`    | UTM params                                                     |

Storage: `sessionStorage` key `porterchain_attribution`.

### CRM / API mapping

`attributionToBackend()` maps to snake_case for API payloads:

- `sourcePage` → `source_page`
- `from`, `locale`, `market` unchanged keys

`resolveLeadSource()` — explicit `from` wins, then stored `from`, then `sourcePage`.

### Zoho

`zoho-attribution.ts` extends attribution for SalesIQ handoff where configured.

---

## Spec → implementation map

| Product spec event    | `ANALYTICS_EVENTS` constant              | Notes                              |
| --------------------- | ---------------------------------------- | ---------------------------------- |
| CTA click (any)       | `CTA_CLICK`                              | Pass `label`, `href` in properties |
| Get quote             | `QUOTE_REQUEST`                          | Navbar, hero, pricing              |
| Contact form success  | `CONTACT_FORM_SUBMIT_SUCCESS`            | `/contact`                         |
| Business inquiry      | `BUSINESS_INQUIRY_SUBMIT`                | `/business`                        |
| Booking quote         | `BOOKING_QUOTE_SUCCESS`                  | Widget on home/book                |
| Platform bridge (SEO) | `SEO_BRIDGE_CLICK`                       | `PlatformBridgeSection.tsx`        |
| Chat open             | `ZOHO_CHAT_OPEN` / `WHATSAPP_CHAT_CLICK` | Device-dependent                   |
| Core Web Vitals       | `WEB_VITAL`                              | `web-vitals-report.ts`             |

## Hub from= attribution values

Use on CTAs after the Merchants/Drivers IA:

| `from` value    | Meaning                            |
| --------------- | ---------------------------------- |
| `chooser`       | Homepage Merchants/Drivers chooser |
| `merchants-hub` | `/business` Merchants hub          |
| `drivers-hub`   | `/vehicle-partner` Drivers hub     |

Constant source: `website/src/lib/marketing/config.ts` → `HUB_FROM`.

---

## Component emitters (reference)

| Component                       | Events                     |
| ------------------------------- | -------------------------- |
| `LinkButton.tsx`                | `cta_click`                |
| `ContactInquiryForm.tsx`        | contact form success/error |
| `Business/InquiryForm.tsx`      | `business_inquiry_submit`  |
| `BookingWidget.tsx`             | booking quote/continue     |
| `PlatformBridgeSection.tsx`     | `seo_bridge_click`         |
| `WhatsAppQuoteLink.tsx`         | `whatsapp_quote_click`     |
| `MobileWhatsAppChat.tsx`        | `whatsapp_chat_click`      |
| `GoogleBusinessProfileLink.tsx` | GBP clicks                 |
| `ZohoSalesIQ.tsx`               | zoho chat events           |
| `web-vitals-report.ts`          | web vital events           |

---

## Development behavior

When no provider is set:

- Events queue in memory
- `console.debug("[analytics]", …)` in development
- Call `flushQueuedAnalyticsEvents()` after gtag loads

---

## Privacy

- No PII in event names
- Form success events should not include email/phone in properties
- Attribution stored session-scoped only
- Cookie policy / CMP deferred — [DEFERRED_AND_OWNER_INPUT_REQUIRED.md](./DEFERRED_AND_OWNER_INPUT_REQUIRED.md)

---

## Verification

1. GA4 DebugView — trigger each conversion event on staging with test property
2. Confirm attribution props on `business_inquiry_submit` after landing with UTM
3. `pnpm validate:product-vision` — includes marketing/analytics guards where applicable
