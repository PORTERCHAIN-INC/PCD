# SEO and AI Search Architecture

**Scope:** `website/src/lib/seo/*` and related app routes  
**Audit cross-ref:** [WEBSITE_SEO_STRATEGY.md](../WEBSITE_SEO_STRATEGY.md)  
**Structured data:** [STRUCTURED_DATA_MAP.md](./STRUCTURED_DATA_MAP.md)

---

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│  website/src/app/[locale]/*  (pages, generateMetadata)      │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   page-helpers.ts    hreflang.ts      schema.ts
   (metadata wrap)   (canonical,       (JSON-LD)
                      hreflang, OG)
         │                 │                 │
         └────────┬────────┴────────┬────────┘
                  ▼                 ▼
            config.ts          routes.ts
            (baseUrl)          (localePath)
                  │
    ┌─────────────┼─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
sitemap-      redirects.ts  internal-     analytics.ts
entries.ts    → next.config  linking.ts    + attribution.ts
```

---

## Module reference

| Module                       | Responsibility                                                     |
| ---------------------------- | ------------------------------------------------------------------ |
| `config.ts`                  | `siteConfig.name`, `baseUrl`, locale validation                    |
| `routes.ts`                  | `localePath`, slug builders (`industrySlug`, `cityIndustrySeo`, …) |
| `hreflang.ts`                | Metadata assembly — canonical, alternates, robots, OG/Twitter      |
| `page-helpers.ts`            | Thin wrappers for page `generateMetadata` exports                  |
| `sitemap-entries.ts`         | Partitioned URL lists with publication gates                       |
| `redirects.ts`               | Historical slug 301/308 registry                                   |
| `schema.ts`                  | JSON-LD builders and `@id` helpers                                 |
| `internal-linking.ts`        | Curated cross-links between SEO hubs                               |
| `analytics.ts`               | Event names, GA4 conversion list, provider hook                    |
| `attribution.ts`             | Session attribution for leads and events                           |
| `content/publishable.ts`     | Shared draft/index gates                                           |
| `content/service-intents.ts` | Commercial intent → canonical route map                            |

Programmatic content loaders (`landing-content.ts`, `service-area-content.ts`, `city-segment-publication.ts`, `vehicle-publication.ts`) sit alongside and feed both metadata and sitemap inclusion.

---

## Metadata and canonicalization

### Entry points

Pages should call one of:

- `buildPageMetadata(locale, pathSegment, title, description, { index? })`
- `buildProgrammaticPageMetadata(locale, pathSegment, title, description, localized)`

Both delegate to `buildSeoMetadata()` in `hreflang.ts`.

### Canonical and hreflang

```typescript
// hreflang.ts — simplified flow
buildCanonicalPath(locale, pathSegment); // → /en/industry/foo
buildAlternateLanguages(locale, pathSegment); // → { en, fr-CA, x-default }
```

`HREFLANG_LOCALE_MAP`: `en` → `en`, `fr` → `fr-CA`. `x-default` always points to English.

### Open Graph and Twitter

- Default image from `defaultOpenGraphImages(title)` → `{baseUrl}/opengraph-image`
- Route implementation: `website/src/app/opengraph-image.tsx` (1200×630 edge PNG)
- Twitter card: `summary_large_image`

### Staging noindex

`shouldIndexInEnvironment(requestedIndex)` in `hreflang.ts`:

- Returns `false` when `NEXT_PUBLIC_APP_ENV` or `NODE_ENV` is `staging` or `preview`
- Otherwise respects page-level `index` flag

This prevents preview deployments from entering the index even if content flags say `index: true`.

---

## Sitemap partitions

Next.js 16 multi-sitemap via `generateSitemaps()` in `website/src/app/sitemap.ts`.

| Partition ID | Builder                          | Typical URLs                               |
| ------------ | -------------------------------- | ------------------------------------------ |
| `static`     | `buildStaticSitemapEntries()`    | Home, business, legal, platform, solutions |
| `industry`   | `buildIndustrySitemapEntries()`  | `/industry/{niche}`                        |
| `service`    | `buildServiceSitemapEntries()`   | `/local-delivery`                          |
| `vehicle`    | `buildVehicleSitemapEntries()`   | `/cargo-van-delivery`, …                   |
| `location`   | `buildLocationSitemapEntries()`  | Service areas + city×segment matrix        |
| `resource`   | `buildResourceSitemapEntries()`  | FAQ, guides, compare, education            |
| `article`    | `buildArticleSitemapEntries()`   | Blog posts (async)                         |
| `case-study` | `buildCaseStudySitemapEntries()` | Success stories                            |
| `developer`  | `buildDeveloperSitemapEntries()` | `/developers/docs/*`                       |

Constants: `SITEMAP_PARTITION_IDS`, `SITEMAP_PARTITION_IDS` exported from `sitemap-entries.ts`.

`robots.ts` advertises the index URL plus each partition:

```
/sitemap.xml
/sitemap/static.xml
/sitemap/industry.xml
…
```

`buildSitemap()` remains for validation and backwards compatibility (combines all partitions).

### Publication gates (sitemap ↔ metadata parity)

| Gate function                | Applies to                                 |
| ---------------------------- | ------------------------------------------ |
| `isPublishableNiche()`       | Industry pages (FR)                        |
| `isPublishableServiceArea()` | Service area pages (FR)                    |
| `isPublishableCitySegment()` | City × industry/vehicle matrix             |
| `shouldIndexVehicleRoute()`  | Vehicle segment pages                      |
| `hasFrProgrammaticSlug()`    | FAQ, guides, compare, success stories (FR) |
| `skipFrenchEnOnlyContent()`  | Onboarding/integrations education          |

---

## Redirects

Single source of truth: `website/src/lib/seo/redirects.ts`.

```typescript
export const WEBSITE_REDIRECTS: WebsiteRedirect[];
export function toNextRedirects(): NextConfig redirects shape;
```

Consumed by `website/next.config.ts`:

```typescript
async redirects() {
  return toNextRedirects();
}
```

Do not add inline redirects in `next.config.ts` — extend `WEBSITE_REDIRECTS` with a `note` for audit trail.

---

## AI search (GEO / AEO)

### llms.txt

- **Path:** `website/public/llms.txt`
- **URL:** `https://porterchain.com/llms.txt`
- **Purpose:** Navigation aid for AI systems — canonical URLs by section (company, services, industries, vehicles, areas, developers, resources, legal, FR entry points)
- **Policy:** Explicit “Do not index or cite” block for portals, staging, secrets

Maintain when adding major hubs or retiring routes. Not a substitute for on-page content.

### AnswerBlock

- **Component:** `website/src/components/seo/AnswerBlock.tsx`
- **Usage:** Concise Q&A near top of money pages (home, business, industry)
- **Example consumer:** `website/src/components/home/HomeAnswerSection.tsx`
- **Schema note:** FAQ JSON-LD is emitted separately when full FAQ sections exist — AnswerBlock is for human + AEO readability, not automatic FAQ schema

### Speakable schema

`buildSpeakableWebPageSchema()` in `schema.ts` targets CSS selectors:

- `.speakable-faq-q`
- `.speakable-faq-a`

Used on FAQ-heavy pages for voice search and snippet extraction.

### Service intents (AEO routing)

`content/service-intents.ts` maps commercial queries to existing canonical URLs — prevents duplicate thin pages and gives AI systems a stable answer target. See [CONTENT_MODEL_AND_TAXONOMY.md](./CONTENT_MODEL_AND_TAXONOMY.md).

---

## Analytics integration

Events flow: UI component → `track(ANALYTICS_EVENTS.*)` → provider (gtag) with merged `attribution.ts` payload.

See [ANALYTICS_EVENT_TAXONOMY.md](./ANALYTICS_EVENT_TAXONOMY.md).

---

## Performance hooks

- `perf-budget.ts` — CWV thresholds by route class
- `web-vitals-report.ts` — reports to analytics on exceedance

---

## Environment variables

| Variable                           | Effect on SEO                                     |
| ---------------------------------- | ------------------------------------------------- |
| `NEXT_PUBLIC_SITE_URL` / `siteUrl` | `metadataBase`, canonical URLs, schema `@id` base |
| `NEXT_PUBLIC_APP_ENV`              | `staging`/`preview` → global noindex              |
| GBP / social env                   | `sameAs` in Organization schema when configured   |

Full deploy list: [DEPLOYMENT_AND_INDEXING_CHECKLIST.md](./DEPLOYMENT_AND_INDEXING_CHECKLIST.md).

---

## Adding a new SEO page (checklist)

1. Add route under `website/src/app/[locale]/…`
2. Use `buildPageMetadata` or `buildProgrammaticPageMetadata`
3. Add to appropriate sitemap partition builder (with FR gate if programmatic)
4. Wire internal links via `internal-linking.ts` helpers
5. Add JSON-LD if FAQ/Service/Article applies — [STRUCTURED_DATA_MAP.md](./STRUCTURED_DATA_MAP.md)
6. Extend `llms.txt` if major hub
7. Run metadata guard: `python3 scripts/verify_website_seo_metadata.py`
8. Log in [WEBSITE_GTM_EXECUTION_PLAN.md](../WEBSITE_GTM_EXECUTION_PLAN.md)

---

## Related strategy docs

- [WEBSITE_SEO_STRATEGY.md](../WEBSITE_SEO_STRATEGY.md) — dual-lane growth strategy
- [WEBSITE_CONTENT_AND_SEO_PLAYBOOK.md](./WEBSITE_CONTENT_AND_SEO_PLAYBOOK.md) — content playbook
- [INTERNAL_LINKING_MAP.md](./INTERNAL_LINKING_MAP.md) — hub linking rules
