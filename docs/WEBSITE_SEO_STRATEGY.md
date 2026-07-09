# Porterchain Website SEO Strategy

**Last updated:** 2026-07-08  
**Scope:** **`website/` only** — marketing site, SEO pages, blog, i18n, and public Next.js routes. Not API, worker, portals, mobile, Fleetbase, or deploy infra (except website env vars at deploy time).  
**Sources:** `/Users/ravi/Documents/porterchain backup/2026-06-25/` and live monorepo `website/`  
**Primary vertical focus:** Construction materials, electrical distribution, plumbing supply, and jobsite delivery across Ontario

This document is the single source of truth for website marketing SEO: what the June 2026 backup had, what is implemented in PCD today, what is missing, and the prioritized work list — with **construction trades** as the main growth lane.

---

## Executive summary

| Layer                                | June 2026 backup (live)                                        | Current PCD `website/`                                                                           |
| ------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| SEO framework                        | Mature programmatic engine                                     | **Ported and improved**                                                                          |
| Public route types                   | ~50                                                            | **~50+** (same surface + blog)                                                                   |
| Sitemap                              | Partial (~100 URLs; many routes omitted)                       | **Complete (~341 URLs)**                                                                         |
| `robots.txt`                         | Not in source                                                  | **Yes** (`/robots.txt`)                                                                          |
| JSON-LD                              | Organization, LocalBusiness, Service, FAQPage, Article, Review | **Same on SEO pages**                                                                            |
| hreflang                             | `en` + `fr-CA` + `x-default`                                   | `en` + `fr` + `x-default`                                                                        |
| URL prefix                           | `/ca/en/...`, `/ca/fr-ca/...`                                  | `/en/...`, `/fr/...` + 301 redirects                                                             |
| Attribution / GA4                    | UTM capture; analytics stub                                    | UTM capture + **GA4 component** (env-gated)                                                      |
| Industry niches (routable)           | 5 (food, pharma, beauty, lab)                                  | **8** (construction trades first + legacy 5)                                                     |
| Construction / electrical / plumbing | Not in backup                                                  | **Live** — industry LPs, city×industry, campaigns, FAQ, blog, success story, vehicle cross-links |

**Bottom line:** All SEO work lives in `website/`. Construction trades are the primary vertical; coffee/pharma/cosmetics remain as secondary programmatic pages.

`pnpm build` in `website/` passes. Sitemap serves **~430+ URLs** (construction expansion + blog).

---

## Investigation sources

| Artifact            | Location                                                           | Notes                                  |
| ------------------- | ------------------------------------------------------------------ | -------------------------------------- |
| Live marketing site | `porterchain backup/2026-06-25/webapp/porterchain-web-main.tar.gz` | ~1,057 files; `web/` inside tarball    |
| Ravi contact card   | `porterchain backup/ravi-contact/` + `website/src/app/ravi/`       | Ported                                 |
| Current website     | `website/src/`                                                     | App Router, `next-intl`, markdown blog |

---

## Part 1 — Backup inventory (June 2026 production)

What the live site actually shipped. Use as migration reference, not as the product roadmap — backup did **not** target construction trades.

### 1.1 Technical SEO

| Feature                     | Backup status                                                   | PCD status                                                       |
| --------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------- |
| Per-page `generateMetadata` | ✅ title, description, OG, canonical, hreflang                  | ✅ via `buildPageMetadata`                                       |
| `metadataBase`              | ✅ locale layout                                                | ✅ `[locale]/layout.tsx`                                         |
| Sitemap                     | ⚠️ Partial — omitted FAQ, guides, city×industry, blog, vehicles | ✅ Full `sitemap-entries.ts`                                     |
| `robots.txt`                | ❌ No source file                                               | ✅ `app/robots.ts`                                               |
| Middleware locale routing   | `/ca/en`, `/ca/fr-ca`                                           | `/en`, `/fr` + bypass for `/sitemap.xml`, `/robots.txt`, `/ravi` |

### 1.2 Structured data (JSON-LD)

| Schema          | Used on                               | PCD file                     |
| --------------- | ------------------------------------- | ---------------------------- |
| `Organization`  | Site-wide                             | `lib/seo/schema.ts` → layout |
| `LocalBusiness` | Site-wide (17 Ontario areas)          | Same                         |
| `Service`       | Industry, city×industry, service area | Same                         |
| `FAQPage`       | Industry, city×industry, FAQ clusters | Same                         |
| `Article`       | Guides, compare, success stories      | Same + blog (basic)          |
| `Review`        | Success stories                       | Same                         |

### 1.3 Programmatic routes (backup)

**Industry niches** (`/industry/[slug]`) — 5 slugs:

- `coffee-roasters`, `pharmacy-medical`, `cosmetics`, `chocolate`, `lab-sample-delivery`

**Service areas** (`/service-areas/[slug]`) — 17 cities:

`toronto`, `mississauga`, `brampton`, `vaughan`, `markham`, `oakville`, `burlington`, `oshawa`, `kitchener-waterloo`, `london`, `st-catharines`, `niagara`, `cambridge`, `guelph`, `hamilton`, `ajax`, `pickering`

**City × industry** (`/[city]/[industrySlug]`) — 11 cities × 5 industries = **55 pages/locale**

| City slugs                                                                                                     | Industry SEO slugs                                                                                      |
| -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| toronto, mississauga, brampton, vaughan, oakville, oshawa, kitchener, hamilton, london, st-catharines, niagara | coffee-roaster-delivery, pharmacy-delivery, cosmetics-delivery, chocolate-delivery, lab-sample-delivery |

Backup also had `/delivery/[industry]/[city]` (alternate linking pattern). PCD uses city×industry SEO path only.

**Vehicle pages:** `sedan-delivery`, `suv-delivery`, `van-delivery`, `medium-truck`

**Content clusters:**

| Cluster                | Count | Example slugs                                                            |
| ---------------------- | ----- | ------------------------------------------------------------------------ |
| FAQ                    | 14    | `delivery-pricing`, `coffee-roaster-delivery`, `pharmacy-delivery`       |
| Guides                 | 5     | `how-porterchain-works`, `merchant-onboarding-guide`                     |
| Compare                | 4     | `in-house-delivery`, `ad-hoc-courier`                                    |
| Onboarding education   | 6     | `getting-started`, `using-csv-upload`                                    |
| Integrations education | 4     | `api-order-ingestion`, `csv-delivery-uploads`                            |
| Success stories        | 3     | coffee, pharmacy, beauty                                                 |
| Campaigns              | 4     | `recurring-delivery`, `coffee-roasters`, `pharmacy-medical`, `cosmetics` |

**Pillar pages:** `local-delivery`, `how-porterchain-works`, `pricing`, `integrations`, `enterprise`

**Construction / electrical / plumbing in backup:** **None.** No trade slugs, no jobsite copy, no FAQ clusters. Industries hub grouped retail/food/healthcare in messages only.

### 1.4 Internal linking (backup pattern)

Hub-and-spoke model in `lib/internal-linking.ts`:

1. Industry page → city delivery + city×industry links
2. Service area → industry links
3. FAQ / guides / compare → industry + service area + conversion CTAs
4. Merchant CTAs with `?from={path}` attribution

PCD ported this pattern; anchor phrases exist for the **5 legacy niches only**.

### 1.5 Attribution & analytics (backup)

| Feature                 | Backup                | PCD                                             |
| ----------------------- | --------------------- | ----------------------------------------------- |
| UTM capture             | `sessionStorage`      | ✅ `lib/seo/attribution.ts`                     |
| Landing page / referrer | ✅                    | ✅ `AttributionCapture`                         |
| Event taxonomy          | ✅ `lib/analytics.ts` | ✅ Ported                                       |
| GA4 wired               | ❌ Stub only          | ✅ `GoogleAnalytics` component (needs prod env) |
| CTA `data-track` clicks | ✅                    | ⚠️ Not wired on all CTAs                        |

---

## Part 2 — Current PCD implementation (what we built)

### 2.1 Implemented ✅

| Capability                         | Location                                               | Notes                                                                       |
| ---------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------------- |
| Sitemap (~341 URLs)                | `src/app/sitemap.ts`, `lib/seo/sitemap-entries.ts`     | Includes all clusters + blog + city×industry                                |
| Robots                             | `src/app/robots.ts`                                    | Disallows `/api/`, `/login`, `/book/*`, `/track/*`                          |
| hreflang + canonical               | `lib/seo/hreflang.ts`, `page-helpers.ts`               | Per SEO landing page                                                        |
| JSON-LD                            | `lib/seo/schema.ts`, `components/seo/JsonLd.tsx`       |                                                                             |
| Industry LPs (5)                   | `app/[locale]/industry/[slug]/`                        | `IndustryLandingView`                                                       |
| Service area LPs (17)              | `app/[locale]/service-areas/[slug]/`                   | EN fallback via `service-area-content.ts`                                   |
| City×industry (55/locale)          | `app/[locale]/[city]/[industrySlug]/`                  | `CityIndustryLandingView`                                                   |
| FAQ / guides / compare / education | `app/[locale]/faq                                      | guides                                                                      | compare | ...` | `ContentClusterView` |
| Campaign LPs (4)                   | `app/[locale]/campaigns/[slug]/`                       |                                                                             |
| Success stories (3)                | `app/[locale]/success-stories/[slug]/`                 | Article + Review schema                                                     |
| Vehicle pages (4)                  | `sedan-delivery`, etc.                                 |                                                                             |
| Pillar pages                       | `local-delivery`, `pricing`, `integrations`, etc.      |                                                                             |
| Ravi contact                       | `/ravi`, `/ravi/contact.vcf`                           | OG image, vCard                                                             |
| Legacy redirects                   | `next.config.ts`                                       | `/ca/en/*` → `/en/*`                                                        |
| Nav / footer SEO links             | `site-footer-*.json`, `corporate-*.json`, `SiteNavbar` | Industries, service areas, resources                                        |
| GA4 + Search Console meta          | `GoogleAnalytics`, layout verification meta            | Set `NEXT_PUBLIC_GA_MEASUREMENT_ID`, `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION` |
| Blog                               | 12 EN + 12 FR posts, 11 categories                     | Category `construction` exists                                              |
| Homepage FAQ                       | `messages/*/faq` namespace                             | Restored after SEO merge collision                                          |
| EN fallback for partial FR         | `landing-content.ts`, `service-area-content.ts`        |                                                                             |

### 2.2 Partial / gaps ⚠️

| Item                     | Gap                                                     |
| ------------------------ | ------------------------------------------------------- |
| FR translations          | Several service-area and niche pages use EN fallback    |
| Blog SEO                 | No `buildPageMetadata` hreflang; minimal Article schema |
| CTA click tracking       | `track()` taxonomy exists; not on all landing CTAs      |
| Root `keywords` metadata | Courier/coffee/medical — no construction terms          |
| Quote-flow attribution   | `visitor-tracking.ts` separate from SEO attribution     |

### 2.3 Construction trades — where they exist today (not SEO)

| Touchpoint              |             construction              |  electrical   |  plumbing   |
| ----------------------- | :-----------------------------------: | :-----------: | :---------: |
| Homepage industry cards |                  ✅                   |      ✅       |     ❌      |
| Booking cargo types     |                  ✅                   |      ✅       |     ✅      |
| Business page copy      |                  ✅                   |      ✅       |     ❌      |
| Homepage testimonial    |                  ❌                   | ✅ (VoltLine) |     ❌      |
| Blog posts              | 1 (`construction-material-logistics`) | mentions only |     ❌      |
| `/industry/[slug]` page |                  ❌                   |      ❌       |     ❌      |
| City×industry URL       |                  ❌                   |      ❌       |     ❌      |
| Campaign LP             |                  ❌                   |      ❌       |     ❌      |
| FAQ cluster             |                  ❌                   |      ❌       |     ❌      |
| Success story           |        ❌ (business page only)        |      ❌       |     ❌      |
| Internal linking graph  |              ❌ orphaned              |  ❌ orphaned  | ❌ orphaned |
| Vehicle page keywords   |              ❌ generic               |  ❌ generic   | ❌ generic  |

**Construction is marketed in copy but not indexed as programmatic SEO.** Electrical has social proof on the homepage; plumbing is a booking label only.

---

## Part 3 — Construction trades SEO strategy (primary focus)

### 3.1 Target personas & search intent

| Persona                             | Example queries                                                                                    | Money pages                                 |
| ----------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Building materials distributor**  | "construction material delivery Toronto", "lumber delivery GTA", "drywall courier Ontario"         | Industry LP, city×industry, `/medium-truck` |
| **Electrical wholesaler**           | "electrical distributor delivery", "wire and panel courier", "electrical supply same-day delivery" | Industry LP, city×industry, business        |
| **Plumbing supply house**           | "plumbing supply delivery", "pipe and fixture courier", "plumbing wholesaler last mile"            | Industry LP, city×industry                  |
| **General contractor / site super** | "jobsite delivery GTA", "construction site courier", "material delivery to job site"               | FAQ cluster, compare, blog                  |
| **Operations manager**              | "proof of delivery construction", "pallet delivery tracking", "recurring jobsite routes"           | Guides, blog, `/business`                   |

### 3.2 Recommended niche slugs (new)

Add to `NICHE_SLUGS` in `lib/seo/niche-landing.ts`:

| Slug                      | Message key              | Positioning                                                 |
| ------------------------- | ------------------------ | ----------------------------------------------------------- |
| `construction-materials`  | `constructionMaterials`  | Lumber, drywall, steel, aggregates, general building supply |
| `electrical-distribution` | `electricalDistribution` | Electrical wholesalers, panel/wire/fixture distributors     |
| `plumbing-supply`         | `plumbingSupply`         | Plumbing wholesalers, pipe, fixtures, waterworks            |

Optional fourth (if splitting GC from distributor):

| `jobsite-delivery` | `jobsiteDelivery` | GC-focused: multi-stop sites, time windows, site access |

**City×industry SEO slugs** (add to `city-industry-seo.ts`):

- `construction-materials-delivery`
- `electrical-delivery`
- `plumbing-supply-delivery`

**New programmatic pages (minimum):**

| Asset                      | Count (EN + FR)                       |
| -------------------------- | ------------------------------------- |
| Industry LPs               | 3 niches × 2 locales = **6**          |
| City×industry              | 3 industries × 11 cities × 2 = **66** |
| Campaign LPs               | 2–3 × 2 = **4–6**                     |
| FAQ clusters               | 3 × 2 = **6**                         |
| Success story              | 1 × 2 = **2**                         |
| Blog posts (new)           | 3–5 topics × 2                        |
| **Subtotal new indexable** | **~85–90 URLs**                       |

Full sitemap would grow from ~341 to **~430 URLs**.

### 3.3 Keyword themes (construction priority)

**Geographic:** GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, London Ontario, Oakville, Niagara

**Service:** jobsite delivery, construction material courier, same-day building supply, pallet delivery, proof of delivery, recurring routes, LTL construction freight

**Industry:**

- construction material delivery, building supply courier, lumber delivery
- electrical distributor delivery, electrical wholesaler courier, panel delivery
- plumbing supply delivery, pipe and fixture courier
- heavy freight, box truck construction delivery, jobsite time windows

**Commercial:** construction delivery pricing, distributor onboarding, CSV bulk orders, delivery API for ERP

Update root layout `keywords` and construction LP meta to include these terms.

### 3.4 Content requirements per construction niche LP

Each `nicheLanding.{key}` block needs (EN + FR):

- `meta.title`, `meta.description` — city + industry long-tail
- `hero` — jobsite / warehouse / distributor angle
- `painPoints` — fleet cost, missed windows, no POD, multi-stop chaos
- `solution` — Porterchain recurring routes, tracking, vehicles (van, pickup, 16ft box)
- `workflow` — 3-step: share routes → we deliver → track/report
- `faq` — coverage, vehicle fit, POD, same-day vs recurring, site access
- `cta` — primary → `/business`, secondary → `/contact`
- `onboarding` — 3 steps for distributor ops

Cross-link every LP to:

- `/medium-truck`, `/van-delivery` (vehicle fit)
- Top 5 service areas (Toronto, Mississauga, Brampton, Hamilton, Kitchener)
- Related FAQ clusters and blog posts

### 3.5 Campaign & paid media

| Campaign slug             | Audience                   | UTM example                            |
| ------------------------- | -------------------------- | -------------------------------------- |
| `construction-materials`  | Distributors, lumber yards | `utm_campaign=construction-materials`  |
| `electrical-distribution` | Electrical wholesalers     | `utm_campaign=electrical-distribution` |
| `plumbing-supply`         | Plumbing supply houses     | `utm_campaign=plumbing-supply`         |

Point paid traffic to `/en/campaigns/{slug}` — attribution already captures UTM.

### 3.6 Blog & authority backlog (construction)

| Priority | Topic slug                                  | Pillar                                    |
| -------- | ------------------------------------------- | ----------------------------------------- |
| P0       | `construction-material-logistics`           | ✅ Exists — add internal links to new LPs |
| P1       | `electrical-wholesaler-delivery-ontario`    | Industry delivery guides                  |
| P1       | `plumbing-supply-last-mile-gta`             | Industry delivery guides                  |
| P1       | `jobsite-delivery-time-windows-pod`         | Last-mile insights                        |
| P2       | `box-truck-vs-courier-construction-freight` | Courier cost optimization                 |
| P2       | `distributor-csv-onboarding-construction`   | Onboarding                                |

Wire `buildInternalLinksForArticle()` on blog template when adding construction pages.

### 3.7 Vehicle pages — construction keyword pass

`/medium-truck` and `/van-delivery` are high-intent for materials freight but use generic copy today. Add:

- Jobsite and pallet keywords in meta + body
- Cross-links to `construction-materials` industry + Toronto/Mississauga city×industry pages
- FAQ snippet: vehicle capacity, tailgate, proof of delivery

---

## Part 4 — URL architecture

### Current (live)

```
/en/                              Home + booking
/en/business                      B2B hub
/en/industry/{niche}              5 niches (legacy verticals)
/en/service-areas/{city}          17 cities
/en/{city}/{industrySlug}         55 city×industry combos
/en/faq/{cluster}                 14 FAQ clusters
/en/guides|compare|campaigns|...   Content clusters
/en/blog/{slug}                   Editorial
/sitemap.xml, /robots.txt         Root (no locale prefix)
/ravi                             Executive contact
```

### Target (after construction expansion)

```
/en/industry/construction-materials
/en/industry/electrical-distribution
/en/industry/plumbing-supply
/en/toronto/construction-materials-delivery
/en/toronto/electrical-delivery
/en/toronto/plumbing-supply-delivery
/en/campaigns/construction-materials
/en/faq/construction-delivery
/en/faq/jobsite-delivery
/en/success-stories/construction-distributor-delivery
```

Legacy redirects remain: `/ca/en/*` → `/en/*`.

---

## Part 5 — Technical SEO standards

Every indexable page should have:

- [x] Unique title + meta description
- [x] Canonical + hreflang (`en`, `fr`, `x-default`) — SEO landings
- [ ] hreflang on all blog posts
- [x] Open Graph + Twitter on shareable pages
- [x] JSON-LD appropriate to page type
- [x] Sitemap inclusion
- [x] `robots: index, follow` on public pages
- [ ] CTA click events via `track()`

Site-wide:

- [x] `metadataBase` from site config
- [x] `<html lang={locale}>`
- [ ] Root keywords updated for construction trades
- [x] Middleware bypass for sitemap, robots, `/ravi`

---

## Part 6 — TODO list

Prioritized work items. Check off in PRs; update this section when shipped.

### P0 — Website production launch (ops)

Set these on the **website** deploy only (`env/website.env.example` → prod):

- [ ] `NEXT_PUBLIC_GA_MEASUREMENT_ID`
- [ ] `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION`
- [ ] Deploy `website/` to production
- [ ] Submit `https://porterchain.com/sitemap.xml` in Google Search Console
- [ ] Verify `/sitemap.xml` and `/robots.txt` return 200 at root

### P1 — Construction trades programmatic SEO (main focus)

**Industry foundation**

- [x] Add `construction-materials`, `electrical-distribution`, `plumbing-supply` to `NICHE_SLUGS` + message keys
- [x] Write full `nicheLanding.*` in `messages/en.json` and `messages/fr.json`
- [x] Add industry index cards + footer/nav links for 3 new niches

**City × industry**

- [x] Add 3 industry SEO slugs to `city-industry-seo.ts`
- [x] Add `industryLabels` in `cityIndustryDelivery` messages
- [x] 66 new static pages (`11 cities × 3 industries × 2 locales`)

**Internal linking**

- [x] Extend `internal-linking.ts` anchor phrases for construction trades
- [x] Add 3 construction FAQ clusters
- [x] Cross-link vehicle pages (`medium-truck`, `van-delivery`) to construction niches

**Campaigns (paid / outbound)**

- [x] Add `construction-materials`, `electrical-distribution`, `plumbing-supply` to `CAMPAIGN_SLUGS`
- [x] Write `campaignLanding.*` copy
- [ ] Document UTM conventions for sales/outbound

**Sitemap**

- [ ] Confirm `sitemap-entries.ts` auto-includes new slugs (via `NICHE_SLUGS` / `getCityIndustrySeoPairs`)
- [ ] Re-count URLs; target ~430 total

### P2 — Construction content authority

**FAQ clusters (new)**

- [x] `construction-delivery` — pricing, vehicles, POD, site access, recurring routes
- [x] `electrical-distributor-delivery` — wire/panel handling, same-day cutoffs
- [x] `jobsite-delivery` — time windows, multi-stop, GC coordination

**Success story**

- [x] `construction-distributor-jobsite-delivery` case study
- [x] Article + Review JSON-LD; link from industry LPs

**Blog**

- [x] Add internal links from construction posts via `buildBlogInternalLinks()`
- [x] Publish `electrical-wholesaler-delivery-ontario` (EN + FR)
- [x] Publish `plumbing-supply-last-mile-gta` (EN + FR)
- [x] Publish `jobsite-delivery-time-windows-pod` (EN + FR)
- [x] Wire blog template to `buildPageMetadata` + internal SEO links block

**Homepage / business alignment**

- [ ] Add plumbing to homepage `industries.items` (parity with booking widget)
- [ ] Link construction/electrical/plumbing cards to `/industry/{slug}` (not just `/business`)
- [ ] Add construction testimonial to homepage (business page has James O'Brien quote)

### P3 — Vehicle & pillar keyword optimization

- [x] Rewrite `/medium-truck` meta + body for construction materials / pallet freight
- [x] Rewrite `/van-delivery` for mid-size building supply
- [x] Add construction FAQ blocks to vehicle pages (use-case sections)
- [x] Update root layout `keywords` with construction/electrical/plumbing terms

### P4 — Platform polish (all verticals)

- [ ] Complete FR translations for partial service-area pages (remove EN fallback where possible)
- [ ] Wire `track()` on primary/secondary CTAs across `IndustryLandingView`, `HubIndexView`, `CtaSection`
- [ ] Enhance blog Article JSON-LD (publisher logo, `dateModified`, author Person)
- [ ] Unify quote-flow attribution with `lib/seo/attribution.ts`
- [ ] Add per-post OG images (frontmatter `image` or `opengraph-image.tsx`)

### P5 — Measurement & iteration

- [ ] GA4 custom dimensions: landing page, UTM source/medium/campaign, industry vertical
- [ ] Track conversions: business inquiry, contact form, booking started from SEO LPs
- [ ] Monthly GSC review: indexed pages, queries containing "construction", "electrical", "plumbing", "jobsite"
- [ ] Quarterly content gap vs competitor SERPs for Ontario distributor delivery

---

## Part 7 — Sitemap inventory (current)

| Segment                                       | URLs per locale       | Notes                                  |
| --------------------------------------------- | --------------------- | -------------------------------------- |
| Core + corporate + pillars                    | ~20                   | home, business, contact, pricing, etc. |
| Industry (5) + service areas (17)             | 23                    | **+3 when construction niches ship**   |
| City × industry                               | 55                    | **+33 when 3 trades × 11 cities ship** |
| FAQ (14) + guides (5) + compare (4)           | 23                    | **+3 construction FAQ clusters**       |
| Education (10) + campaigns (4) + vehicles (4) | 18                    | **+3 construction campaigns**          |
| Success stories (3)                           | 3                     | **+1 construction story**              |
| Blog posts (12) + categories (11)             | 23                    | Growing                                |
| `/ravi`                                       | 1                     | Root only                              |
| **Total today**                               | **~170/locale ≈ 341** |                                        |
| **Target after construction**                 | **~215/locale ≈ 430** |                                        |

---

## Part 8 — Reference files

### PCD (current)

| File                                          | Purpose                                                 |
| --------------------------------------------- | ------------------------------------------------------- |
| `website/src/lib/seo/schema.ts`               | JSON-LD builders                                        |
| `website/src/lib/seo/sitemap-entries.ts`      | Full sitemap                                            |
| `website/src/lib/seo/niche-landing.ts`        | Industry slug SSOT                                      |
| `website/src/lib/seo/city-industry-seo.ts`    | City×industry URL matrix                                |
| `website/src/lib/seo/internal-linking.ts`     | Cross-link helpers                                      |
| `website/src/lib/seo/landing-content.ts`      | Niche/campaign EN fallback                              |
| `website/src/lib/seo/service-area-content.ts` | Service area EN fallback                                |
| `website/src/lib/seo/content/faq-clusters.ts` | FAQ cluster config                                      |
| `website/src/lib/seo/attribution.ts`          | UTM capture                                             |
| `website/src/lib/seo/analytics.ts`            | Event taxonomy                                          |
| `website/src/components/seo/`                 | Landing templates, JsonLd, GA4                          |
| `website/messages/en.json`, `fr.json`         | `nicheLanding`, `serviceAreaLanding`, `campaignLanding` |
| `website/messages/site-footer-*.json`         | Footer SEO links                                        |
| `website/content/blog/`                       | Markdown posts                                          |

### Backup (tarball → `web/`)

| File                             | Purpose                      |
| -------------------------------- | ---------------------------- |
| `lib/seo.ts`                     | Original hreflang helpers    |
| `lib/schema.ts`                  | Original JSON-LD             |
| `lib/city-industry-seo.ts`       | URL matrix reference         |
| `lib/internal-linking.ts`        | Linking patterns reference   |
| `lib/seo-content/`               | Content model for generation |
| `messages/en.json`, `fr-ca.json` | Legacy copy source           |

---

## Part 9 — Governance

- SEO copy: update **both** `messages/en.json` and `messages/fr.json` in the same PR
- New programmatic slug: update `NICHE_SLUGS` / `CAMPAIGN_SLUGS` / `faq-clusters.ts` + messages + verify sitemap count
- New blog post: EN + FR pair in `content/blog/`; link to ≥1 industry LP + 1 service area + `/business`
- Do not index: `/login`, `/book/continue`, `/book/success`, `/track/[id]`
- Construction trades content must mention: vehicle fit, POD, recurring routes, Ontario coverage — avoid generic courier copy

---

## Appendix — Legacy route list (backup)

Full `app/**/page.tsx` routes from June 2026 tarball for redirect mapping:

```
/  → /ca/en
/ravi, /ravi/contact.vcf
/driver/onboarding (noindex)
/[market]/[locale]/ + all clusters listed in Part 1
/[market]/[locale]/[city]/[industrySlug]
/[market]/[locale]/delivery/[industry]/[city]
```

301 map in `website/next.config.ts` covers `/ca/en/*` and `/ca/fr-ca/*`.

---

## Appendix — Current blog inventory

| Slug (EN)                       | Category     | Construction relevance        |
| ------------------------------- | ------------ | ----------------------------- |
| construction-material-logistics | construction | **Primary** — link to new LPs |
| sla-dispatch-vs-marketplace     | logistics    | Jobsite reliability mention   |
| wholesale-distribution-gta      | wholesale    | Adjacent distributor audience |
| audit-ready-proof-of-delivery   | logistics    | POD for jobsite               |
| _(8 others)_                    | various      | Low trades relevance          |

Each EN post has an FR counterpart in `content/blog/fr/`.
