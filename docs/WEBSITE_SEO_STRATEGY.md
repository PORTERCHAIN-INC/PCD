# Porterchain Website SEO Strategy

**Last updated:** 2026-07-09  
**Scope:** **`website/` only** — marketing site, SEO pages, blog, i18n, and public Next.js routes. Deploy env vars and `.github/workflows/deploy-website.yml` are referenced where they affect production SEO/analytics.  
**Checklist cross-ref:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md) §1.1 (product vision), §6.1 (brand/i18n), §7.1.6 (developers)  
**Primary vertical focus:** Construction materials, electrical distribution, plumbing supply, and jobsite delivery across the GTA and Ontario  
**Positioning (canonical):** **Logistics technology platform** — not a courier operator (§1.1.1–1.1.3)  
**Production canonical:** `https://porterchain.com` (Caddy redirects `www` → apex)

This document is the single source of truth for website marketing SEO **and sales discovery**: what shipped in PCD, how the programmatic engine works, how platform pages and long-tail SEO work together, production configuration, and the remaining backlog.

---

## Executive summary

| Layer                    | June 2026 backup                                               | PCD `website/` (July 2026 — live)                                                |
| ------------------------ | -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Positioning**          | Courier / local delivery                                       | **Platform-first** — dispatch OS, orchestration, API (§1.1)                      |
| SEO framework            | Mature programmatic engine                                     | **Extended** — city×industry, city×vehicle, city×delivery-intent                 |
| **Platform pages**       | Redirected to `/business`                                      | **`/platform`**, **`/solutions`**, **4 verticals**, **`/developers`** live       |
| Indexable URLs (sitemap) | Partial (~100)                                                 | **~737 URLs** (`/sitemap.xml` — incl. platform + solutions after 2026-07-09)     |
| Site navigation          | Minimal (2 links)                                              | **Full IA** — Platform, Solutions ▾, Business, Pricing, Company ▾, Resources ▾   |
| Footer IA                | Duplicates, partial coverage                                   | **5 columns** — Platform, Business, Industries, Company & resources, Legal       |
| `robots.txt`             | Not in source                                                  | ✅ Root `/robots.txt`                                                            |
| JSON-LD                  | Organization, LocalBusiness, Service, FAQPage, Article, Review | ✅ Same + **DeliveryService** LocalBusiness, GBP `sameAs` when configured        |
| hreflang                 | `en` + `fr-CA` + `x-default`                                   | `en` + `fr` + `x-default`                                                        |
| URL prefix               | `/ca/en/...`, `/ca/fr-ca/...`                                  | `/en/...`, `/fr/...` + 301 from `/ca/*`                                          |
| Industry niches          | 5 legacy                                                       | **9** — 3 construction trades + ecommerce + 5 legacy                             |
| City programmatic        | 11×5 industry only                                             | **11×9 industry** + **11×6 vehicle** + **11×6 delivery-intent**                  |
| i18n guards              | None                                                           | **`verify_i18n_parity.py`** — 5 EN/FR pairs + **EN landing locale-purity** guard |
| Attribution / GA4        | UTM capture; analytics stub                                    | UTM + **GA4 live** (`G-VWMZWJ4W4M`) + conversion events                          |
| Live chat                | —                                                              | **Zoho SalesIQ** (prod build-arg)                                                |
| GSC                      | —                                                              | **Domain verified**; sitemap submitted                                           |

**Bottom line:** Porterchain runs a **dual-lane** website: (1) **platform/SaaS discovery** for investors, enterprise buyers, and integrators; (2) **programmatic SEO** for construction trades and GTA long-tail. Both lanes must stay linked via nav, footer, and internal links — not siloed.

`pnpm --filter @porterchain/website build` passes. Static sitemap (`force-static`, 24h revalidate).

---

## Alignment with Silicon Valley Readiness Checklist

| Checklist item   | Website implication                                                                     | Status                                                        |
| ---------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **§1.1.1–1.1.3** | Homepage hero = platform; no `BookingWidget` above fold; book → customer portal `:3004` | ✅ `corporate.home.hero`, `Hero.tsx`                          |
| **§1.1.5**       | `/platform` live, indexed, in nav + footer                                              | ✅ sitemap 2026-07-09                                         |
| **§1.1.6**       | `/solutions` + 4 verticals live                                                         | ✅ wholesale, medical, food-beverage, construction            |
| **§1.1.7**       | Footer + nav links resolve                                                              | ✅ `footer-navigation.ts`, `navbar-navigation.ts`             |
| **§1.1.10**      | Blog = SLA/dispatch narrative, not marketplace courier                                  | ✅ construction + platform posts                              |
| **§6.1.5**       | FR/EN parity on marketing message files                                                 | ✅ 5 pairs; `en.json`/`fr.json` root [~] 428 keys gap on `fr` |
| **§6.2.1**       | Book CTA externalized; platform CTAs primary                                            | ✅                                                            |
| **§7.1.6**       | `/developers` — OpenAPI, Postman, API keys path                                         | ✅ in nav Resources + footer Platform                         |

**CI guards (run before website deploy):**

```bash
pnpm validate:product-vision   # §1.1 pages, hero, footer, book redirect
pnpm validate:design           # includes verify_i18n_parity.py
```

---

## Dual-lane growth: platform SEO + programmatic SEO

### Lane A — Platform & enterprise sales (high ACV)

**Audience:** Ops leaders, CTOs, integrators, investors  
**Intent:** “logistics software”, “dispatch platform”, “API delivery orchestration”

| Stage         | Pages                                                               | Primary CTA                      |
| ------------- | ------------------------------------------------------------------- | -------------------------------- |
| Awareness     | `/`, `/platform`, `/solutions`, blog (platform posts)               | Explore platform · Get a demo    |
| Consideration | `/solutions/{vertical}`, `/integrations`, `/developers`, `/pricing` | Talk to sales · OpenAPI          |
| Conversion    | `/business`, `/enterprise`, `/contact`                              | Business inquiry · Schedule call |

**Sales motion:** Demo-led. UTM → `/contact` or `/business?from=…`. Developer path → `/developers` → merchant API keys.

### Lane B — Programmatic & trades SEO (high volume, local)

**Audience:** Construction distributors, electrical/plumbing wholesalers, site supers  
**Intent:** “construction material delivery Toronto”, “jobsite delivery GTA”, “electrical distributor delivery”

| Stage         | Pages                                                                   | Primary CTA                |
| ------------- | ----------------------------------------------------------------------- | -------------------------- |
| Awareness     | `/industry/{niche}`, `/en/{city}/{segment}`, FAQ, blog (trades)         | Talk to us                 |
| Consideration | `/campaigns/{slug}` (paid/outbound), `/compare/*`, `/success-stories/*` | Contact · Business inquiry |
| Conversion    | `/business`, Zoho chat, GBP                                             | Business inquiry form      |

**Sales motion:** Inbound SEO + paid exact-match → **campaign LPs** (`/en/campaigns/construction-materials`, etc.). Attribution via `lib/seo/attribution.ts`.

### Lane bridge (required — do not silo)

Every Lane B money page should link **up** to Lane A where relevant:

- Industry LPs → `/platform` or `/solutions/construction` (construction trades)
- `/business` inquiry captures both lanes (`?from=` path preserved)
- Footer **Platform** column surfaces `/developers` and `/integrations` from all SEO landings
- Homepage industry cards → `/industry/{slug}`; hero secondary → `/platform`

---

## Site navigation & discoverability (July 2026)

**SSOT:** `website/src/data/navbar-navigation.ts`, `website/src/data/footer-navigation.ts`  
**Labels:** `corporate.nav` (navbar), `siteFooter.sections` (footer)

### Navbar (desktop dropdowns + mobile accordions)

| Item            | Destinations                                       |
| --------------- | -------------------------------------------------- |
| **Platform**    | `/platform`                                        |
| **Solutions** ▾ | Hub, 4 verticals, `/industry`, `/service-areas`    |
| **Business**    | `/business`                                        |
| **Pricing**     | `/pricing`                                         |
| **Company** ▾   | About, careers, contact, vehicle partners          |
| **Resources** ▾ | Developers, blog, FAQ, guides, track, how it works |
| **Book Now**    | Customer portal `:3004/book` (retail — external)   |

### Footer (5 columns)

| Column                  | Purpose                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| **Platform**            | Platform, solutions, how it works, integrations, developers, track                         |
| **Business**            | Business, enterprise, pricing, book, quote, my orders                                      |
| **Industries & areas**  | Industry hub, top 3 trades, service areas, local/van delivery                              |
| **Company & resources** | About, contact, careers, partners, blog, FAQ, guides, compare, success stories, onboarding |
| **Legal**               | Privacy, terms, cookies                                                                    |

**SEO impact:** Crawlers and users can reach all Tier-0/1 pages within 2 clicks from any page. Previously platform/solutions were footer-only or missing from nav.

---

## Production status (July 2026)

### Shipped to `porterchain.com`

| Area                                     | Status      | Notes                                                        |
| ---------------------------------------- | ----------- | ------------------------------------------------------------ |
| Website deploy                           | ✅ Live     | GitHub `Deploy Website` workflow → GHCR → droplet            |
| Platform-first homepage                  | ✅ Live     | §1.1.3 — corporate hero, platform CTAs                       |
| `/platform`, `/solutions`, `/developers` | ✅ Live     | §1.1.5, §1.1.6, §7.1.6                                       |
| Full nav + footer IA                     | ✅ Live     | 2026-07-09 `navbar-navigation.ts`                            |
| GA4                                      | ✅ Live     | Stream `porterchain` · ID `G-VWMZWJ4W4M`                     |
| Zoho SalesIQ                             | ✅ Live     | `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED=true`                      |
| Google Search Console                    | ✅ Verified | DNS/domain property; sitemap submitted                       |
| EN locale purity (trades LPs)            | ✅ Fixed    | `en.json` `nicheLanding` + `campaignLanding` — no FR leakage |
| Sitemap: platform + solutions            | ✅ Code     | `sitemap-entries.ts` 2026-07-09 — redeploy to prod           |
| CTA analytics                            | ✅ Partial  | `LinkButton` `outlineOnDark`; key flows tracked              |

### Env vars (website production)

| Variable                                  | Purpose             | Status                        |
| ----------------------------------------- | ------------------- | ----------------------------- |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID`           | GA4                 | ✅ `G-VWMZWJ4W4M`             |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED`        | Live chat           | ✅ `true`                     |
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE`    | Zoho widget         | ✅ Secret                     |
| `NEXT_PUBLIC_SITE_URL`                    | Canonical / sitemap | ✅ `https://porterchain.com`  |
| `NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL` | GBP footer + schema | ⏳ Set after claiming profile |
| `NEXT_PUBLIC_CONTACT_PHONE`               | NAP / schema        | ✅ `+16476197951`             |

Local template: `env/website.env.example`

---

## Programmatic SEO engine (current)

### Industry niches — `/[locale]/industry/[slug]`

**SSOT:** `website/src/lib/seo/niche-landing.ts`  
**Copy:** `messages/en.json` + `messages/fr.json` → `nicheLanding.*`

| Slug                                      | Vertical                         | Priority    |
| ----------------------------------------- | -------------------------------- | ----------- |
| `construction-materials`                  | Building supply, lumber, drywall | **Primary** |
| `electrical-distribution`                 | Electrical wholesalers           | **Primary** |
| `plumbing-supply`                         | Plumbing wholesalers             | **Primary** |
| `ecommerce`                               | D2C / fulfillment / last mile    | Secondary   |
| `coffee-roasters` … `lab-sample-delivery` | Legacy niches                    | Long-tail   |

**9 niches × 2 locales = 18 industry LP URLs** (+ `/industry` hub × 2)

### Platform solutions — `/[locale]/solutions/[vertical]`

**SSOT:** `website/src/lib/solutions-verticals.ts`  
**Copy:** `messages/corporate-*.json` → `corporate.solutions`

| Slug            | Maps to industry niche |
| --------------- | ---------------------- |
| `wholesale`     | ecommerce              |
| `medical`       | pharmacy-medical       |
| `food-beverage` | coffee-roasters        |
| `construction`  | construction-materials |

**4 verticals × 2 locales = 8 URLs** (+ `/solutions` hub × 2) — **Lane A** pages; cross-link to Lane B industry LPs.

### Service areas — `/[locale]/service-areas/[slug]`

**17 cities** (see `service-areas.ts`)

### City × segment — `/[locale]/[city]/[segmentSlug]`

**SSOT:** `city-industry-seo.ts`, `city-segment-seo.ts`, `city-local-segment-content.ts`

**11 URL cities** × (9 industry + 6 vehicle + 6 delivery-intent) = **231 segment URLs/locale**

**FR note:** City×vehicle and city×delivery-intent copy falls back to EN when `cityLocalSegment` keys missing in `fr.json` (~428 root keys behind EN — P1 backlog).

### Vehicle pillar pages — 6 slugs

`sedan-delivery` … `cargo-van-delivery`, `medium-truck` — construction cross-links via `vehicle-construction-links.ts`

### Content clusters

| Cluster                | Count/locale | Path                             |
| ---------------------- | ------------ | -------------------------------- |
| FAQ                    | 18           | `/faq/[slug]`                    |
| Guides                 | 5            | `/guides/[slug]`                 |
| Compare                | 4            | `/compare/[slug]`                |
| Onboarding education   | 6            | `/onboarding-education/[slug]`   |
| Integrations education | 4            | `/integrations-education/[slug]` |
| Success stories        | 4            | `/success-stories/[slug]`        |
| Campaigns              | 7            | `/campaigns/[slug]`              |

**Construction campaigns (Lane B paid):** `construction-materials`, `electrical-distribution`, `plumbing-supply`

### Blog

**16 EN + 16 FR** posts · **11 categories** · construction/trades + platform narrative

### Pillar / corporate pages (Lane A + shared)

| Page                                                    | Lane   | Sitemap priority                               |
| ------------------------------------------------------- | ------ | ---------------------------------------------- |
| `/platform`                                             | A      | 0.95                                           |
| `/solutions`, `/solutions/{vertical}`                   | A      | 0.9 / 0.85                                     |
| `/developers`                                           | A      | 0.75                                           |
| `/business`, `/enterprise`, `/pricing`, `/integrations` | A      | 0.85–0.95                                      |
| `/how-porterchain-works`, `/local-delivery`             | Both   | 0.9                                            |
| `/industry/*`, city segments, campaigns                 | B      | 0.72–0.8                                       |
| `/track` (hub)                                          | Shared | 0.8 — index hub only; `/track/[id]` disallowed |

### Ravi contact card

`/ravi` — executive contact (no locale prefix)

---

## URL architecture (live)

```
/en/                                    Home — platform hero (Lane A)
/en/platform                             Platform overview (Lane A) ★
/en/solutions                            Solutions hub (Lane A) ★
/en/solutions/{vertical}                 4 vertical LPs (Lane A) ★
/en/developers                           API / developer portal (Lane A)
/en/business                             B2B hub + inquiry (conversion)
/en/industry/{niche}                     9 niche LPs (Lane B)
/en/{city}/{segmentSlug}                 City×industry + vehicle + intent (Lane B)
/en/campaigns/{slug}                     7 campaign LPs (Lane B paid)
/en/faq/{cluster} … /en/blog/{slug}       Content clusters
/sitemap.xml                             Root (static)
/robots.txt                              Root
```

★ Added to sitemap 2026-07-09 (previously live but not in `STATIC_PATHS`).

**Do not index:** `/login`, `/book/continue`, `/book/success`, `/track/[tracking]`

Legacy: `/ca/en/*` → `/en/*` via `next.config.ts`

---

## Technical SEO

### Per-page requirements

| Requirement                                    | Status                                                    |
| ---------------------------------------------- | --------------------------------------------------------- |
| Unique title + meta description                | ✅ SEO landings via `buildPageMetadata`                   |
| Canonical + hreflang (`en`, `fr`, `x-default`) | ✅ SEO landings                                           |
| Locale-specific `metadata.keywords`            | ✅ `en.json` / `fr.json` — not mixed in layout            |
| Open Graph + Twitter                           | ✅ Shareable pages                                        |
| JSON-LD by page type                           | ✅ Organization, LocalBusiness, Service, FAQPage, Article |
| Sitemap inclusion                              | ✅ SSOT arrays; platform/solutions added 2026-07-09       |
| CTA `track()` events                           | ⚠️ Wired on key flows; extend to all hub CTAs             |

### i18n governance

| Rule                                                             | Enforcement                                                         |
| ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| User-facing copy in both EN + FR for corporate/site-footer pairs | `verify_i18n_parity.py` (5 pairs)                                   |
| No French in `en.json` landing namespaces                        | `verify_i18n_parity.py` — `nicheLanding`, `campaignLanding` markers |
| ICU paths not in JSON (API routes with `{vars}`)                 | Constants in page TSX (e.g. `FLOW_PATHS` on developers)             |
| `corporate.nav` + `siteFooter` drive nav/footer labels           | `navbar-navigation.ts`, `footer-navigation.ts`                      |

### Internal linking

**SSOT:** `internal-linking.ts`, `industry-home-links.ts`, `navbar-navigation.ts`, `footer-navigation.ts`

1. **Nav/footer** — every Tier-0 page ≤2 clicks
2. Industry LP → city delivery + local delivery links
3. Solutions vertical → related industry LP (`solutions/[vertical]/page.tsx`)
4. FAQ / guides / compare → industry + `/business` CTAs
5. Blog → `buildBlogInternalLinks()`
6. Homepage industry cards → `/industry/{slug}`
7. Merchant CTAs with `?from={path}` — `lib/seo/attribution.ts`

### Attribution & analytics

| Feature           | Location                 | Status                 |
| ----------------- | ------------------------ | ---------------------- |
| UTM capture       | `lib/seo/attribution.ts` | ✅                     |
| GA4 page views    | `GoogleAnalytics.tsx`    | ✅ Prod                |
| Conversion events | `lib/seo/analytics.ts`   | ✅ — mark in GA4 Admin |

**GA4 conversion events** (mark in Admin → Events → Mark as conversion):

- `contact_form_submit_success`
- `business_inquiry_submit`
- `booking_quote_success`
- `zoho_chat_open`
- `gbp_review_click`

---

## Sitemap inventory (July 2026)

**Total: ~737 URLs** (after platform + solutions + 4 verticals × 2 locales)

| Segment                               | URLs per locale         | Notes                         |
| ------------------------------------- | ----------------------- | ----------------------------- |
| Core + corporate + pillars + vehicles | ~36                     | incl. `platform`, `solutions` |
| Solutions verticals                   | 4                       | `SOLUTION_VERTICAL_SLUGS`     |
| Industry LPs                          | 9                       | `NICHE_SLUGS`                 |
| Service areas                         | 17                      |                               |
| City × industry                       | 99                      | 11 × 9                        |
| City × vehicle                        | 66                      | 11 × 6                        |
| City × delivery intent                | 66                      | 11 × 6                        |
| Content clusters + blog               | ~90+                    |                               |
| `/ravi`                               | 1                       | root only                     |
| **≈ Total**                           | **~368/locale × 2 + 1** |                               |

Sitemap auto-includes new slugs when added to SSOT arrays — no manual URL list.

---

## Construction trades strategy (Lane B — implemented)

### Target personas & money pages

| Persona                        | Example queries                          | Live money pages                                                                                                           |
| ------------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Building materials distributor | "construction material delivery Toronto" | `/industry/construction-materials`, `/toronto/construction-materials-delivery`, `/solutions/construction`, `/medium-truck` |
| Electrical wholesaler          | "electrical distributor delivery GTA"    | `/industry/electrical-distribution`, `/toronto/electrical-delivery`                                                        |
| Plumbing supply house          | "plumbing supply delivery Mississauga"   | `/industry/plumbing-supply`, `/campaigns/plumbing-supply`                                                                  |
| General contractor             | "jobsite delivery GTA"                   | FAQ `construction-delivery`, blog `jobsite-delivery-time-windows-pod`                                                      |

### Keyword themes (indexed)

**Geographic:** GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, London, Oakville, Niagara

**Service:** jobsite delivery, same-day courier, last-mile, B2B delivery, recurring routes, proof of delivery, pallet/box truck freight

**Platform (Lane A):** dispatch software, logistics orchestration, delivery API, merchant integrations

### Paid / outbound (UTM)

Point campaigns to `/en/campaigns/{slug}` — attribution captures UTM automatically.

| Campaign slug             | Audience                   |
| ------------------------- | -------------------------- |
| `construction-materials`  | Distributors, lumber yards |
| `electrical-distribution` | Electrical wholesalers     |
| `plumbing-supply`         | Plumbing supply houses     |
| `recurring-delivery`      | B2B recurring shippers     |

Example: `utm_campaign=construction-materials&utm_source=google&utm_medium=cpc`

**Platform paid (Lane A):** Point to `/platform` or `/solutions/construction` with `utm_campaign=platform-demo`.

---

## Platform & enterprise strategy (Lane A — July 2026)

### Target personas

| Persona              | Queries / intent                                   | Money pages                             |
| -------------------- | -------------------------------------------------- | --------------------------------------- |
| VP Operations        | "dispatch software", "route optimization platform" | `/platform`, `/how-porterchain-works`   |
| CTO / integrator     | "delivery API", "logistics webhooks"               | `/developers`, `/integrations`          |
| Enterprise buyer     | "enterprise logistics software Ontario"            | `/enterprise`, `/solutions`, `/pricing` |
| Investor / diligence | "Porterchain platform"                             | `/platform`, `/company`, blog           |

### Content priorities (next 90 days)

1. **Case study amplification** — link `case-study-construction-distributor-gta` from `/solutions/construction` + homepage
2. **Developer SEO** — `/developers` ranks for "Porterchain API"; add 2 blog posts on integration patterns
3. **Comparison pages** — `/compare/*` targeting "vs courier" / "vs in-house fleet" (platform angle, not courier fluff)
4. **Cross-links** — every `/solutions/{vertical}` page links to matching `/industry/{niche}` + `/business`

---

## Local / GTA marketing (beyond on-site SEO)

| Channel                 | Status                | Action                                                       |
| ----------------------- | --------------------- | ------------------------------------------------------------ |
| Google Search Console   | ✅ Verified + sitemap | Monthly: platform queries + construction/trades + city names |
| Google Business Profile | ⏳ Claim + env URL    | Service-area business; NAP matches site                      |
| GA4 conversions         | ⏳ Admin setup        | Mark conversion events; segment Lane A vs B by landing path  |
| Google Ads              | Not started           | Lane B → campaign LPs; Lane A → platform/solutions           |
| Reviews                 | Not started           | Merchant post-delivery; `gbp_review_click` tracking          |

---

## TODO backlog

Prioritized. Check off in PRs; update this section when shipped.

### P0 — Ship with next website deploy

- [x] Add `/platform`, `/solutions`, `/solutions/{vertical}` to `sitemap-entries.ts` (2026-07-09)
- [ ] **Redeploy website** so prod sitemap picks up +10 URLs
- [ ] Resubmit sitemap in GSC after deploy
- [ ] Verify GSC indexes `/en/platform` and `/en/solutions/*` within 2 weeks

### P1 — i18n & locale quality

- [ ] Add `cityLocalSegment` copy to `fr.json` (remove EN fallback on city×vehicle/intent)
- [ ] Close `en.json` / `fr.json` root key gap (~428 keys on FR) — prioritize SEO landings first
- [ ] `IndustryLandingView` section labels → i18n (`links.*` or `industryLanding.*`)
- [ ] Document UTM conventions for sales (`utm_campaign` ↔ campaign slugs + platform campaigns)

### P2 — Google Business Profile

- [ ] Claim / verify GBP
- [ ] Set `NEXT_PUBLIC_GOOGLE_BUSINESS_PROFILE_URL` + redeploy
- [ ] GBP posts linking to `/en/platform`, `/en/toronto/van-delivery`, top trade LPs

### P3 — Analytics & conversion polish

- [ ] Mark GA4 conversion events in Admin
- [ ] GA4 explorations: Lane A (`/platform`, `/developers`) vs Lane B (`/industry`, `/campaigns`) funnels
- [ ] Wire `track()` on remaining hub CTAs (`HubIndexView`)
- [ ] Per-post OG images for blog

### P4 — Content & authority (sales-powered SEO)

- [ ] 2 new blog posts: platform integration + construction ROI (EN + FR)
- [ ] Internal links: `/platform` → top 3 industry LPs + `/developers`
- [ ] Monthly GSC review: impressions for "dispatch", "construction delivery", "API" clusters
- [ ] Quarterly SERP gap vs Ontario distributor/courier **and** logistics SaaS competitors

---

## Reference files

### Website SEO core

| File                                         | Purpose                        |
| -------------------------------------------- | ------------------------------ |
| `website/src/lib/seo/sitemap-entries.ts`     | Full sitemap generator         |
| `website/src/lib/seo/niche-landing.ts`       | Industry slug SSOT             |
| `website/src/lib/solutions-verticals.ts`     | Solutions vertical SSOT        |
| `website/src/lib/seo/city-industry-seo.ts`   | City×industry matrix           |
| `website/src/lib/seo/city-segment-seo.ts`    | City×vehicle + delivery-intent |
| `website/src/lib/seo/internal-linking.ts`    | Cross-link helpers             |
| `website/src/lib/seo/industry-home-links.ts` | Homepage → industry LP         |
| `website/src/lib/seo/schema.ts`              | JSON-LD builders               |
| `website/src/lib/seo/analytics.ts`           | Event taxonomy                 |
| `website/src/lib/seo/attribution.ts`         | UTM capture                    |

### Navigation & IA

| File                                            | Purpose                                  |
| ----------------------------------------------- | ---------------------------------------- |
| `website/src/data/navbar-navigation.ts`         | Navbar link SSOT                         |
| `website/src/data/footer-navigation.ts`         | Footer link SSOT                         |
| `website/src/components/layout/SiteNavbar.tsx`  | Nav shell + dropdowns                    |
| `website/src/components/layout/NavDropdown.tsx` | Desktop/mobile menus                     |
| `website/messages/corporate-*.json`             | `nav`, `home`, `solutions`, `developers` |
| `website/messages/site-footer-*.json`           | Footer column labels                     |

### CI guards

| Script                                   | Checklist                  |
| ---------------------------------------- | -------------------------- |
| `scripts/verify_product_vision_pages.py` | §1.1.3–1.1.7               |
| `scripts/verify_i18n_parity.py`          | §6.1.5 + EN landing purity |
| `scripts/verify_design_copy.py`          | §6.1.2–6.1.3               |

### Messages & content

| Path                                  | Purpose                                                                    |
| ------------------------------------- | -------------------------------------------------------------------------- |
| `website/messages/en.json`, `fr.json` | `nicheLanding`, `campaignLanding`, `cityLocalSegment`, `metadata.keywords` |
| `website/messages/corporate-*.json`   | Platform, solutions, developers, nav                                       |
| `website/content/blog/`               | Markdown posts (EN + FR)                                                   |

### Deploy

| File                                   | Purpose                        |
| -------------------------------------- | ------------------------------ |
| `.github/workflows/deploy-website.yml` | Website-only production deploy |
| `website/Dockerfile`                   | Build args for GA, Zoho, GBP   |

---

## Governance

- **Dual-lane discipline:** Platform copy uses orchestration/dispatch language (§1.1.2 ban list). Trades SEO copy uses vehicle fit, POD, recurring routes — not generic courier fluff.
- SEO copy: update **both** `en.json` and `fr.json` when adding `nicheLanding` / `campaignLanding` strings.
- New programmatic slug: update SSOT + messages + verify sitemap count increases.
- New corporate page: add to `navbar-navigation.ts`, `footer-navigation.ts`, and `sitemap-entries.ts` in the **same PR**.
- New blog post: EN + FR pair; link to ≥1 industry LP + 1 platform/solutions page + `/business`.
- Do not index: `/login`, `/book/continue`, `/book/success`, `/track/[id]`.
- No street address on public marketing surfaces.
- Website releases: push to `main` → **Deploy Website** workflow.

---

## Appendix — June 2026 backup (historical)

The June 2026 tarball had ~50 route types, partial sitemap, no construction trades, no platform page, minimal nav, and `/ca/en/` URL prefix. PCD ported and extended that engine; checklist work (July 2026) added platform-first positioning, full IA, developers portal, and i18n guards. This doc reflects **current production intent**, not the backup roadmap.

```
Backup:  /ca/en/industry/[slug]           →  PCD: /en/industry/[slug]
Backup:  no /platform                     →  PCD: /en/platform (Lane A)
Backup:  ~100 sitemap URLs                →  PCD: ~737 sitemap URLs
Backup:  courier-first homepage           →  PCD: platform-first hero (§1.1.3)
```
