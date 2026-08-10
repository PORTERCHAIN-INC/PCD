# Content Model and Taxonomy

**Scope:** Programmatic and editorial content types under `website/src/lib/seo/content/`  
**Architecture:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md)  
**Evidence rules:** [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md)

---

## PublishableContent

**File:** `website/src/lib/seo/content/publishable.ts`

Shared gate for any indexable content module:

```typescript
export type ContentStatus = "draft" | "review" | "published";

export type PublishableContent = {
  slug: string;
  status: ContentStatus;
  index: boolean;
  authorId?: string;
  reviewerId?: string;
  publishedAt?: string;
  updatedAt?: string;
  schemaType?: string;
  sources?: string[];
  canonicalSlug?: string;
};

export function isPublished(content): boolean {
  return content.status === "published" && content.index;
}
```

### Wiring

| Consumer              | Usage                                     |
| --------------------- | ----------------------------------------- |
| `page-helpers.ts`     | `index` → `buildProgrammaticPageMetadata` |
| `sitemap-entries.ts`  | Skip URLs when not publishable            |
| `content/research.ts` | Draft reports stay noindex                |

**Rule:** Never set `index: true` without `status: "published"` and evidence review per [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md).

---

## Service intents

**File:** `website/src/lib/seo/content/service-intents.ts`

Maps commercial delivery intents to **existing** canonical routes — no parallel `/services/*` tree.

```typescript
export type ServiceIntentSlug =
  | "same-day-business-delivery"
  | "urgent-delivery"
  | "scheduled-delivery"
  | … ;

export type ServiceIntentRoute = {
  slug: ServiceIntentSlug;
  pathSegment: string;      // e.g. "local-delivery", "business"
  faqClusterSlug?: string;  // optional FAQ hub link
  index: boolean;
};
```

### Intent → route examples

| Intent                           | Canonical path segment            | FAQ cluster                         |
| -------------------------------- | --------------------------------- | ----------------------------------- |
| `same-day-business-delivery`     | `local-delivery`                  | `same-day-delivery`                 |
| `fleet-overflow`                 | `business`                        | `fleet-overflow-wholesale-delivery` |
| `construction-material-delivery` | `industry/construction-materials` | `construction-delivery`             |
| `api-delivery-booking`           | `developers`                      | `api-integrations`                  |
| `live-delivery-tracking`         | `track`                           | —                                   |

Use `getServiceIntentRoute(slug)` for lookups. New intents require IA review before adding routes.

---

## Industry model

**Primary files:**

- `website/src/lib/seo/niche-landing.ts` — `NICHE_SLUGS`, message keys
- `website/src/lib/seo/landing-content.ts` — `isPublishableNiche()`
- `website/src/lib/seo/seo-content/industries.ts` — copy templates
- `website/src/app/[locale]/industry/[slug]/page.tsx` — route

### Niche slugs (9)

| Slug                      | Lane B focus       |
| ------------------------- | ------------------ |
| `construction-materials`  | Primary vertical   |
| `electrical-distribution` | Primary vertical   |
| `plumbing-supply`         | Primary vertical   |
| `coffee-roasters`         | Legacy niche       |
| `pharmacy-medical`        | Regulated delivery |
| `cosmetics`               | Legacy niche       |
| `chocolate`               | Legacy niche       |
| `lab-sample-delivery`     | Legacy niche       |
| `ecommerce`               | Wholesale overflow |

Industry hub: `/industry`. Sitemap partition: `industry`.

FR publication: requires body in `messages/fr.json` niche landing + `isPublishableNiche()`.

---

## Vehicle model

**Primary files:**

- `website/src/lib/seo/vehicle-publication.ts` — `INDEXABLE_VEHICLE_SEGMENTS`, `shouldIndexVehicleRoute()`
- `website/src/lib/seo/vehicle-page.tsx` — shared page shell
- `website/src/lib/seo/city-segment-seo.ts` — city × vehicle matrix

### Vehicle segments

Examples: `trade-van-delivery`, `cargo-van-delivery`, `box-truck-delivery`, `pickup-truck-delivery`, `sedan-delivery`, `suv-delivery`.

Legacy slugs redirect via `redirects.ts` (`van-delivery` → `trade-van-delivery`, `medium-truck` → `box-truck-delivery`).

Sitemap partition: `vehicle`. City matrix URLs: `/{city}/{vehicle-segment}` in `location` partition.

---

## Location model

**Layers:**

1. **Service area hub** — `/service-areas` + `/service-areas/{slug}`
   - `service-areas.ts`, `service-area-content.ts`, `isPublishableServiceArea()`
   - Core areas only in sitemap (`isCoreServiceArea()`)

2. **City × industry** — `/{city}/{industrySeoSlug}`
   - `city-industry-seo.ts`, `city-industry-delivery.ts`
   - Gated by `isPublishableCitySegment()` in `city-segment-publication.ts`

3. **City × vehicle** — `/{city}/{vehicleSegment}`
   - Same publication gate

4. **Hyperlocal schema** — `hyperlocal-geo.ts` feeds `buildServiceSchema({ geoSlug })`

Primary cities: see `PRIMARY_CITY_SLUGS` in `internal-linking.ts`.

---

## Blog

**Content:** `website/content/blog/{en,fr}/*.md`  
**SEO helper:** `website/src/lib/seo/blog-seo.ts`

- `getIndustrySlugsForPost()` — maps category/tags → industry internal links
- `buildInternalLinksForArticle()` — curated footer links on posts
- Sitemap: `article` partition via `getAllPosts()` / `getAllPostSlugs()`
- Categories: `website/src/data/blog-categories.ts` → `/blog/category/{category}`

Blog posts use frontmatter dates for `lastModified` in sitemap.

---

## Comparisons

**File:** `website/src/lib/seo/content/comparison-pages.ts`

```typescript
export type ComparisonPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  alternativeLabel: string;
  comparisonRows: ComparisonRow[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  extraLinks?: …;
};
```

- Route: `/compare/{slug}`
- **Policy:** No competitor naming — alternatives are categories (in-house, ad hoc courier, spreadsheet dispatch)
- FR: index only when slug exists in `messages/seo-programmatic-fr.json` → `compare` namespace
- Sitemap: `resource` partition

---

## Guides (authority pages)

**File:** `website/src/lib/seo/content/authority-pages.ts`

```typescript
export type AuthorityPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  sections: AuthoritySection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  extraLinks?: …;
};
```

- Route: `/guides/{slug}` (except `how-porterchain-works` → top-level `/how-porterchain-works`)
- Redirect: `/guides/how-porterchain-works` → `/how-porterchain-works` in `redirects.ts`
- Sitemap: `resource` partition; canonical how-it-works also in `static`

Related education (EN-only index):

- `content/onboarding-education.ts`
- `content/integrations-education.ts`
- Hub redirects to `/guides` for index paths

---

## FAQ clusters

**File:** `website/src/lib/seo/content/faq-clusters.ts`

- Route: `/faq/{slug}`
- Schema: `FAQPage` via `buildFAQPageSchema()`
- Intent hubs linked from `INTENT_HUB_FAQ_SLUGS` in `internal-linking.ts`

---

## Success stories (case studies)

**File:** `website/src/lib/seo/content/success-stories.ts`

```typescript
export type SuccessStory = {
  slug: string;
  …
  outcomeMetric?: string;
  permissioned?: boolean;  // required for Review schema + metric display
};
```

- Route: `/success-stories/{slug}`
- Sitemap: `case-study` partition
- Schema: Article + optional Review when `permissioned: true`

---

## Research (deferred)

**File:** `website/src/lib/seo/content/research.ts`

Extends `PublishableContent` with methodology fields. All entries start `draft` + `index: false` until operational data exists. See [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md).

---

## Solutions verticals

**File:** `website/src/lib/solutions-verticals.ts`

Lane A verticals: `wholesale`, `medical`, `food-beverage`, `construction` under `/solutions/{vertical}`. Linked from navbar and `buildProductLinksForNiche()`.

---

## Taxonomy summary table

| Type          | Route pattern             | Content module        | Sitemap partition |
| ------------- | ------------------------- | --------------------- | ----------------- |
| Static hub    | `/{page}`                 | i18n messages         | `static`          |
| Industry      | `/industry/{slug}`        | niche landing         | `industry`        |
| Service area  | `/service-areas/{slug}`   | service-area-content  | `location`        |
| City matrix   | `/{city}/{segment}`       | programmatic messages | `location`        |
| Vehicle       | `/{segment}`              | vehicle messages      | `vehicle`         |
| FAQ           | `/faq/{slug}`             | faq-clusters          | `resource`        |
| Guide         | `/guides/{slug}`          | authority-pages       | `resource`        |
| Compare       | `/compare/{slug}`         | comparison-pages      | `resource`        |
| Case study    | `/success-stories/{slug}` | success-stories       | `case-study`      |
| Blog          | `/blog/{slug}`            | markdown              | `article`         |
| Developer doc | `/developers/docs/{slug}` | developer-docs        | `developer`       |

---

## Internal linking

Content modules declare `industrySlugs` and `serviceAreaSlugs` for related links. Central hub rules: [INTERNAL_LINKING_MAP.md](./INTERNAL_LINKING_MAP.md).
