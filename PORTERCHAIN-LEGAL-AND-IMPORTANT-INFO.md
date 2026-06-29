# Porterchain — Legal, Policy & Important Information

**Compiled from the Porterchain public website (`apps/website`) and related platform configuration.**  
**Last updated:** June 29, 2026

> **Note:** The live website does **not** yet have dedicated `/terms`, `/privacy`, `/cookies`, or `/knowledge-center` routes. This document consolidates all Porterchain-related legal, policy, compliance, and help content that **currently exists** in the website and platform, plus technical disclosures implied by integrations.

---

## 1. Company identity

| Field | Value |
|-------|-------|
| **Legal name** | PORTERCHAIN INC. |
| **Brand / short name** | Porterchain |
| **Tagline** | Commercial logistics partner for local businesses |
| **Website** | https://porterchain.com |
| **Primary email** | peter@porterchain.com |
| **Operations email** | ops@porterchain.com |
| **Phone** | +1 (647) 619-7951 |
| **WhatsApp** | +1 (647) 619-7951 |
| **Head office** | 100 King Street West, Toronto, ON M5X 1A9, Canada |
| **Locale** | en-CA |

### What Porterchain does

Porterchain is a professional commercial logistics company helping local businesses move goods across the GTA and Ontario. Services include same-day and scheduled delivery, route optimization, live tracking, and proof of delivery with compliance and insurance.

Porterchain is **not** an ad-hoc local driver marketplace. It is a structured logistics company built for business-critical delivery, with dispatch controls, compliance procedures, insurance coverage, and accountable shipment workflows.

### Mission, vision & goal

- **Mission:** Help local businesses grow without building their own logistics department.
- **Vision:** Build the most trusted local-business logistics platform in Canada.
- **Goal:** Deliver every shipment safely, on time, and with complete operational visibility.

---

## 2. Social media links

| Platform | URL | Label |
|----------|-----|-------|
| **LinkedIn** | https://www.linkedin.com/company/porterchain | Porterchain Inc. on LinkedIn |
| **Instagram** | https://www.instagram.com/porterchain/ | Porterchain on Instagram |
| **Facebook** | https://www.facebook.com/profile.php?id=61568324733884 | Porterchain on Facebook |
| **YouTube** | https://www.youtube.com/@porterchain | Porterchain on YouTube |
| **WhatsApp** | https://wa.me/16476197951 | Porterchain on WhatsApp |

Social links appear in the site footer and in structured data (`sameAs` in Organization schema).

**Twitter/X handle (SEO metadata):** `@porterchain`

---

## 3. Trust, compliance & operating standards

### Trust badges (published on site)

- WSIB registered
- Commercially insured operations
- Compliance-first dispatch controls
- Route optimization for fuel efficiency
- Driver partner operating model

### Compliance statement

Porterchain maintains WSIB registration, commercial insurance coverage, and operational compliance procedures. Commercial operations are coordinated with documented processes so local businesses can trust every shipment.

### Quality controls

Every shipment is checked through:

- Address validation before dispatch
- Vehicle-class and capacity checks
- Pre-departure dispatch verification
- Delivery proof verification workflow

Proof on each shipment includes **photo, signature, GPS, shipment references, and audit-ready status history**.

### Sustainability

Porterchain reduces fuel use, emissions, and idle time through route optimization, better load matching, and fewer empty miles.

### Driver partner model

Drivers are business partners in the network. Porterchain focuses on predictable work, fair payouts, clear dispatch instructions, and operational support to maintain service quality.

### Driver partner operating principles

- Predictable workflow and dispatch communication
- Clear trip expectations and completion criteria
- Proof-of-delivery standards for each job
- Operational support during active routes

### Operational benchmarks (vs. ad-hoc delivery)

| KPI | Before | After | Impact |
|-----|--------|-------|--------|
| On-time delivery | Manual dispatch with frequent delays | Managed dispatch with SLA-based execution | Improved delivery reliability |
| Exception handling | Reactive issue resolution | Pre-dispatch checks and controlled escalations | Fewer avoidable exceptions |
| Fuel & route efficiency | Unoptimized routing and empty miles | Route and load optimization on each lane | Lower fuel use and emissions |
| Proof & billing readiness | Incomplete handoff documentation | Photo, signature, GPS, and reference audit trail | Faster reconciliation and fewer disputes |

**Website pages:** `/standards`, `/about`, `/for-business`, `/driver-partner`

---

## 4. Merchant agreement & billing policies

### Merchant onboarding agreement (website portal)

When a business completes merchant onboarding at `/portal/merchant/onboarding`, the contract step states:

> **By accepting, you agree to Porterchain commercial shipping terms, billing policies, and service-level commitments for merchant accounts.**

Acceptance records:

- `contract_status` → `signed`
- `contract_signed_at` → timestamp
- `contract_expires_at` → one year from acceptance

**Required onboarding steps:**

1. Company profile (name, contact, billing email, tax/HST numbers, insurance details, addresses)
2. Business documents (registration, insurance, tax documents)
3. Merchant agreement acceptance
4. Admin review before account activation (`ACTIVE` status)

**Business booking notice (website):**

> Business accounts require merchant onboarding and admin approval before dashboard access. You will complete company profile, documents, and contract acceptance after sign-in.

### Payment terms (merchant billing)

| Term ID | Label |
|---------|-------|
| `stripe` | Stripe |
| `credit_card` | Credit Card |
| `net_30` | Net 30 (default) |
| `net_45` | Net 45 |

Additional merchant payment constants in the API: `immediate`, `net_7`, `net_14`, `custom`.

**Merchant portal billing features:** Stripe checkout, credit card, Net 30/45 terms, monthly statements, invoice PDFs.

### Retail (website) billing

Retail customers booking through the public website can pay after delivery via Stripe on the tracking page (`/track/{tracking_number}`).

### Invoice & billing operations

- Invoices include payment terms on PDFs
- Overdue invoice reminders are sent by the billing engine
- Billing contact: `ops@porterchain.com` (platform default)

---

## 5. Knowledge center (help & informational content)

The website does not have a `/knowledge-center` page. The following published pages serve as the public knowledge base:

### Support hub — `/support`

**Hours:** Monday–Friday 7:00–19:00 ET · Saturday 8:00–17:00 ET

**Topics:**

| Topic | Path |
|-------|------|
| Track a shipment | `/track` |
| Request a quote | `/contact` |
| FAQ | `/faq` |
| Live chat | Zoho SalesIQ widget (see Section 8) |
| For Business programs | `/for-business` |

### FAQ — `/faq`

**Q: What exactly does Porterchain do?**  
Porterchain runs professional commercial logistics for local businesses. We coordinate same-day and scheduled delivery, route planning, dispatch execution, tracking, and proof of delivery.

**Q: How is Porterchain different from local driver services?**  
We are not an ad-hoc driver marketplace. Porterchain is a structured logistics company with dispatch controls, compliance procedures, insurance coverage, and accountable shipment workflows.

**Q: Do you support same-day and scheduled delivery?**  
Yes. We support both urgent same-day delivery and scheduled recurring routes for local businesses across the GTA and nearby Ontario markets.

**Q: What proof and visibility do you provide?**  
Each shipment includes live tracking and a complete proof set: photo, signature, GPS, shipment references, and audit-ready status history.

**Q: Are you compliant and insured?**  
Yes. Porterchain maintains WSIB registration, insurance coverage, and compliance procedures for professional commercial operations.

**Q: How do you reduce delivery errors?**  
We use multiple checks including address validation, vehicle matching, dispatch verification, and proof verification before a shipment is marked complete.

**Q: What is your sustainability approach?**  
We reduce fuel use and emissions through route optimization, smarter load matching, and lower empty-mile travel across our service lanes.

**Q: How do you work with drivers?**  
Drivers are business partners in our network. We focus on fair payout structure, clear dispatch instructions, and operational support to maintain service quality.

### Blog / articles — `/blog`

| Slug | Title | Published |
|------|-------|-----------|
| `gta-commercial-logistics-guide` | Professional Logistics vs Ad-Hoc Delivery in the GTA | 2026-06-01 |
| `same-day-vs-scheduled-freight-gta` | Same Day vs Scheduled Freight in the GTA | 2026-05-15 |
| `proof-of-delivery-commercial-shipments` | Why Proof of Delivery Matters for Commercial Shipments | 2026-04-28 |

### API integrations — `/api-integrations`

- Shipment creation from ERP/store/internal systems
- Tracking lifecycle events
- Proof data (signature, photo, GPS)
- Webhook delivery for dispatch and completion updates

Request API access via `/contact`.

### Service areas

**Primary cities:** Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington, Oshawa, Kitchener-Waterloo, London, St. Catharines, Niagara, Cambridge, Guelph, Hamilton, Ajax, Pickering

**Supplementary areas:** Richmond Hill, Scarborough, North York, Etobicoke, Whitby

**Index:** `/service-areas` and `/service-areas/{city-slug}`

### Vehicle classes

Sedan, SUV, Minivan, Cargo Van, Sprinter, 16ft Box Truck, 20ft Box Truck

### Industries served

- Same Day Delivery — `/industries/same-day-delivery`
- Multi Stop Distribution — `/industries/multi-stop-distribution`
- Furniture Delivery — `/industries/furniture-delivery`
- Construction Delivery — `/industries/construction-delivery`
- Coffee Roaster Delivery — `/industries/coffee-roaster-delivery`
- Electrical Supply Delivery — `/industries/electrical-supply-delivery`
- Beauty Product Delivery — `/industries/beauty-product-delivery`

### Careers — `/careers`

| Role | Department | Location | Type |
|------|------------|----------|------|
| Commercial Dispatcher — Toronto | Operations | Toronto, ON (GTA) | Full-time |
| Box Truck Driver — GTA | Driver Network | Greater Toronto Area | Full-time / Contract |
| Merchant Success Manager | Commercial | Toronto, ON | Full-time |

Apply via `/contact`.

---

## 6. Terms & conditions (status)

**Status: Not published as a standalone page on the website.**

The following binding references exist today:

1. **Merchant agreement** — acceptance in the merchant onboarding wizard (Section 4)
2. **Implied commercial terms** — quotes, bookings, and shipments are governed by Porterchain's commercial shipping and service-level practices described on `/standards`, `/faq`, and `/for-business`
3. **PC-CRM knowledge base** — internal CRM module (`/knowledge_base`) can host articles; content is database-driven and not in the website repo

**Recommended next step:** Publish a formal Terms of Service at `/terms` covering booking, liability, prohibited goods, cancellation, and dispute resolution under Ontario/Canadian law.

---

## 7. Privacy policy (status)

**Status: Not published as a standalone page on the website.**

### Data collected (based on platform behavior)

| Data type | Purpose | Systems |
|-----------|---------|---------|
| Name, email, phone | Account creation, booking OTP, shipment contact | Clerk, Supabase Auth, Porterchain API |
| Company profile & tax/insurance details | Merchant onboarding & compliance | Porterchain API |
| Pickup/delivery addresses | Routing, dispatch, tracking | Porterchain API, Google Maps / OSRM / Valhalla |
| Shipment details (weight, dimensions, photos) | Quoting, capacity matching, POD | Porterchain API |
| Payment information | Invoicing and checkout | Stripe (card data handled by Stripe) |
| Location/GPS | Proof of delivery, driver tracking | Porterchain API, Fleetbase |
| Chat messages | Customer support | Zoho SalesIQ |
| Auth session cookies | Login state | Clerk, Supabase, Fleetbase session (control tower) |

### Authentication providers

- **Clerk** — merchant and driver identity (JWT)
- **Supabase** — website booking OTP (email for business, SMS for personal via Twilio)
- **Stripe** — payment processing

### Contact for privacy inquiries

**Email:** peter@porterchain.com  
**Operations:** ops@porterchain.com

**Recommended next step:** Publish a Privacy Policy at `/privacy` compliant with PIPEDA (Canada) covering collection, use, retention, third-party processors, and user rights.

---

## 8. Cookies & third-party services

**Status: No cookie consent banner or Cookie Policy page on the website.**

### Third-party scripts and services loaded by the website

| Service | Purpose | Domain / provider |
|---------|---------|-------------------|
| **Zoho SalesIQ** | Live chat widget | `salesiq.zohopublic.ca` |
| **Clerk** | Authentication (merchant/driver sign-in) | Clerk hosted |
| **Supabase** | Booking OTP auth | `*.supabase.co` |
| **Google Maps** | Address autocomplete, maps | `maps.googleapis.com` |
| **Stripe** | Payment checkout (tracking/retail pay) | `stripe.com` |

### Cookies likely set

- **Clerk** — session and authentication cookies
- **Supabase** — auth session cookies (server-side cookie handling in Next.js)
- **Zoho SalesIQ** — chat session and analytics cookies
- **Stripe** — payment session cookies during checkout

### Environment-configurable social URLs

Social links can be overridden via:

- `NEXT_PUBLIC_SOCIAL_LINKEDIN`
- `NEXT_PUBLIC_SOCIAL_INSTAGRAM`
- `NEXT_PUBLIC_SOCIAL_FACEBOOK`
- `NEXT_PUBLIC_SOCIAL_YOUTUBE`
- `NEXT_PUBLIC_SOCIAL_WHATSAPP`

**Recommended next step:** Publish a Cookie Policy at `/cookies` and add a consent mechanism if required for Zoho/analytics cookies.

---

## 9. Important website pages index

| Page | URL | Purpose |
|------|-----|---------|
| Home | `/` | Main marketing & booking entry |
| Quote engine | `/quote` | Instant commercial quotes |
| Track shipment | `/track` | Public tracking & retail payment |
| About | `/about` | Company overview |
| Standards | `/standards` | Mission, compliance, sustainability |
| FAQ | `/faq` | Common questions |
| Support | `/support` | Help hub & contact hours |
| Contact | `/contact` | Quote requests |
| For Business | `/for-business` | B2B logistics programs |
| Driver Partner | `/driver-partner` | Driver program info |
| API Integrations | `/api-integrations` | Developer/integration info |
| Services | `/services` | Service overview |
| Industries | `/industries` | Industry-specific pages |
| Service Areas | `/service-areas` | Geographic coverage |
| Blog | `/blog` | Articles |
| Careers | `/careers` | Open positions |
| Merchant portal | `/portal/merchant` | Business account dashboard |
| Merchant onboarding | `/portal/merchant/onboarding` | Profile, documents, contract |
| Sign in / Sign up | `/sign-in`, `/sign-up` | Account access |

**SEO / technical:** `/sitemap.xml`, `/robots.txt`, `/manifest.json`

---

## 10. Copyright & branding

- **Copyright:** © {year} PORTERCHAIN INC.
- **Footer tagline:** Commercial transportation across the GTA
- **PWA manifest name:** PORTERCHAIN INC. / Porterchain
- **Theme color:** `#091B1C`
- **Primary brand color:** `#091B1C`

---

## 11. Gaps & recommended legal pages

| Item | Current state | Recommended action |
|------|---------------|-------------------|
| Terms & Conditions | Referenced in merchant onboarding only | Create `/terms` page; link in footer |
| Privacy Policy | Not published | Create `/privacy` page; link in footer |
| Cookie Policy | Not published | Create `/cookies` page + consent banner |
| Knowledge Center | FAQ + Support + Blog serve this role | Optionally unify at `/knowledge-center` or `/help` |
| GDPR page | Exists in PC-CRM admin only | Not applicable to public site unless EU traffic targeted |

---

## 12. Source files (for maintainers)

| Content | Source |
|---------|--------|
| Company info, social links, nav | `apps/website/src/lib/site.ts` |
| FAQ, blog, careers | `apps/website/src/lib/content.ts` |
| Footer & social icons | `apps/website/src/components/layout/Footer.tsx` |
| Merchant agreement text | `apps/website/src/components/merchant-onboarding/MerchantOnboardingWizard.tsx` |
| Support hours & topics | `apps/website/src/app/support/page.tsx` |
| Standards page | `apps/website/src/app/standards/page.tsx` |
| Billing payment terms | `api/app/Models/Porterchain/BillingRecord.php` |
| Contract acceptance logic | `api/app/Services/Porterchain/MerchantOnboardingService.php` |
| Zoho chat widget | `apps/website/src/components/support/ZohoSalesIQ.tsx` |

---

*This document is an internal compilation for reference. It is not legal advice. Formal Terms, Privacy, and Cookie policies should be reviewed by qualified counsel before publication.*
