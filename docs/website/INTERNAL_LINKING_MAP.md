# Internal Linking Map

**Module:** `website/src/lib/seo/internal-linking.ts`  
**Content taxonomy:** [CONTENT_MODEL_AND_TAXONOMY.md](./CONTENT_MODEL_AND_TAXONOMY.md)  
**Architecture:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md)

---

## Design principles

1. **Max 5 curated links** on SEO detail pages (`MAX_DETAIL_PAGE_LINKS = 5`)
2. **Lane B → Lane A bridge** on every niche page (`buildProductLinksForNiche`)
3. **City ↔ industry ↔ service area** triangle for programmatic matrix
4. **Intent FAQ hubs** for high-commercial-intent clusters
5. **Navbar + footer** provide stable IA; in-body links add contextual depth

---

## Hub map (internal-linking.ts)

### Primary city slugs

```typescript
export const PRIMARY_CITY_SLUGS = [
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "oakville",
  "oshawa",
  "kitchener-waterloo",
  "hamilton",
  "london",
  "st-catharines",
  "niagara",
];
```

Used for city delivery links, vehicle links, and industry×city matrix.

### Industry slugs for city links

```typescript
export const INDUSTRY_SLUGS_FOR_CITY_LINKS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
  "ecommerce",
  "coffee-roasters",
  "pharmacy-medical",
  "cosmetics",
  "chocolate",
  "lab-sample-delivery",
];
```

### Intent FAQ hubs

```typescript
export const INTENT_HUB_FAQ_SLUGS = [
  "same-day-retail-distribution",
  "fleet-overflow-wholesale-delivery",
];
```

Linked via `buildIntentHubLinks()`.

---

## Link builder functions

| Function                                  | Used on              | Output                                            |
| ----------------------------------------- | -------------------- | ------------------------------------------------- |
| `buildCityDeliveryLinksForIndustryPage()` | Industry niche pages | City×industry URLs with anchor phrases            |
| `buildLocalDeliveryCityLinks()`           | Local delivery hub   | Service area links per city                       |
| `buildVehicleLinksForCityPage()`          | City landing pages   | Up to 4 vehicle×city links                        |
| `buildIndustryPageLinksForCityPage()`     | City pages           | Industry hub links                                |
| `buildIndustryDeliveryLinksForCityPage()` | Service area pages   | City×industry matrix links                        |
| `buildProductLinksForNiche()`             | Industry pages       | Platform + solutions vertical + industry overview |
| `buildProductLinksForIndustrySeoSlug()`   | City×industry pages  | Same, resolved from SEO slug                      |
| `buildIntentHubLinks()`                   | Business, industry   | FAQ intent hubs                                   |
| `buildInternalLinksForArticle()`          | Blog posts           | Industries + service areas (max 12)               |

### Anchor phrase map

`ANCHOR_PHRASE_BY_INDUSTRY_KEY` — descriptive anchors (e.g. “Construction materials delivery Toronto”) rather than generic “learn more”.

### Niche → solutions vertical

```typescript
// Partial map in internal-linking.ts
"construction-materials" → "construction"
"pharmacy-medical" → "medical"
"ecommerce" → "wholesale"
```

---

## Navbar IA

**File:** `website/src/data/navbar-navigation.ts`  
**Labels:** `messages/*/corporate.nav`

| Item            | Type     | Href                                                    |
| --------------- | -------- | ------------------------------------------------------- |
| Business        | link     | `/business`                                             |
| Solutions       | dropdown | `/solutions` + 4 verticals + industries + service areas |
| Pricing         | link     | `/pricing`                                              |
| Contact / quote | link     | `/contact?intent=quote`                                 |
| Company         | dropdown | about, careers, contact, vehicle partner                |
| Resources       | dropdown | blog, FAQ, guides, track, how-it-works                  |

**Primary CTA in navbar:** quote (`bookNow` i18n key) → `/contact?intent=quote`.

Platform is **not** top-level nav — reached via footer, home, and SEO bridge links (Lane B → Lane A).

---

## Footer policy

**File:** `website/src/data/footer-navigation.ts`  
**Renderer:** `website/src/components/layout/OrganizedFooterLinks.tsx`

Five columns (`footerSectionOrder`):

| Section       | Purpose          | Key links                                                              |
| ------------- | ---------------- | ---------------------------------------------------------------------- |
| **products**  | Buy capacity     | business, solutions, how-it-works, pricing, get quote, track           |
| **solutions** | Fit by vertical  | industry hub, top 3 trades, service areas, enterprise                  |
| **company**   | Trust + partners | about, contact, careers, vehicle partner, **trust**                    |
| **resources** | Depth + dev      | blog, FAQ, guides, platform, integrations, developers, customer portal |
| **legal**     | Compliance       | privacy, terms, cookies                                                |

### Footer rules

1. **Legal links only in `legal` column** — not duplicated in company
2. **Trust center** in company column — `/trust` (SLA/DPA/MSA subpages linked from trust hub)
3. **Platform** in resources — Lane A discovery without crowding navbar
4. **External portals** use sentinel hrefs (`__CUSTOMER_PORTAL__`, `__DRIVER_PORTAL__`) resolved in component
5. **Get quote** duplicates navbar CTA intentionally — footer is last-chance conversion

i18n labels via `SiteFooter` translation keys — paths stay internal in `footer-navigation.ts`.

---

## Cross-lane bridging (Lane B → Lane A)

Every industry niche page must include `buildProductLinksForNiche()` output:

1. Platform — “How Porterchain operates” (`platform(locale, { from })`)
2. Solutions vertical (when mapped)
3. Parent industry overview

Analytics: `seo_bridge_click`, `platform_explore` — [ANALYTICS_EVENT_TAXONOMY.md](./ANALYTICS_EVENT_TAXONOMY.md).

---

## Content module links

Comparison and authority pages declare:

- `industrySlugs[]` → links to `/industry/{slug}`
- `serviceAreaSlugs[]` → links to `/service-areas/{slug}`
- `extraLinks[]` → onboarding, pricing, integrations, etc.

Blog posts use `blog-seo.ts` → `getIndustrySlugsForPost()` for related industries.

---

## Slug mapping tables

| Map                        | Purpose                             |
| -------------------------- | ----------------------------------- |
| `NICHE_TO_INDUSTRY_SEO`    | Niche slug → city×industry SEO slug |
| `SERVICE_AREA_TO_CITY_SEO` | Service area → city SEO slug        |
| `CITY_SEO_TO_SERVICE_AREA` | Inverse for link building           |
| `INDUSTRY_SEO_TO_NICHE`    | Reverse lookup for product links    |

Defined in `internal-linking.ts` and `city-industry-seo.ts`.

---

## Anti-patterns

- Do not exceed `MAX_DETAIL_PAGE_LINKS` on money pages without playbook exception
- Do not link to draft/noindex content
- Do not create orphan matrix URLs — every city×segment page should link back to service area + industry hub
- Avoid competitor names in compare page links (compare content policy)

---

## Verification

- `scripts/verify_wave9_seo.py` — user-intent linking wave
- `scripts/verify_programmatic_en_playbook.py` — EN programmatic link coverage
- Manual: crawl sample industry page → confirm 5 or fewer curated links + platform bridge
