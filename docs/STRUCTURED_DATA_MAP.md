# Structured Data Map

**Module:** `website/src/lib/seo/schema.ts`  
**Architecture:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md)  
**Audit:** [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md §7](./PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md#7-structured-data)

---

## @id graph

Base URL from `siteConfig.baseUrl` (trailing slash stripped).

| Entity           | Helper              | @id value               |
| ---------------- | ------------------- | ----------------------- |
| Organization     | `organizationId()`  | `{base}/#organization`  |
| WebSite          | `websiteId()`       | `{base}/#website`       |
| Service (global) | `serviceEntityId()` | `{base}/#service`       |
| LocalBusiness    | inline in builder   | `{base}/#localbusiness` |

### Graph relationships

```
WebSite (#website)
  └── publisher → Organization (#organization)

LocalBusiness (#localbusiness)
  └── sameAs → GBP/social (when configured)

Service (per-page, optional @id)
  └── provider → Organization (inline, not always @id linked)

WebSite.inLanguage: ["en-CA", "fr-CA"]
```

Root layout emits Organization + WebSite:

```tsx
// website/src/app/[locale]/layout.tsx
<JsonLd data={buildOrganizationSchema()} />
<JsonLd data={buildWebSiteSchema()} />
```

Home additionally emits LocalBusiness via `HomeDeliverySchema.tsx`.

---

## Exported types

| Type                        | Schema.org @type                 |
| --------------------------- | -------------------------------- |
| `OrganizationSchema`        | Organization                     |
| `WebSiteSchema`             | WebSite                          |
| `LocalBusinessSchema`       | LocalBusiness, DeliveryService   |
| `ServiceSchema`             | Service                          |
| `SoftwareApplicationSchema` | SoftwareApplication              |
| `FAQPageSchema`             | FAQPage                          |
| `ArticleSchema`             | Article                          |
| `ReviewSchema`              | Review                           |
| `BreadcrumbListSchema`      | BreadcrumbList                   |
| `ItemListSchema`            | ItemList                         |
| `SpeakableWebPageSchema`    | WebPage + SpeakableSpecification |

---

## Builder functions

| Function                                                   | Purpose                                             |
| ---------------------------------------------------------- | --------------------------------------------------- |
| `buildOrganizationSchema()`                                | Site-wide org — logo, slogan, knowsAbout, sameAs    |
| `buildWebSiteSchema()`                                     | Site entity with publisher @id                      |
| `buildLocalBusinessSchema()`                               | Contact/GBP — phone, hours, areaServed, serviceType |
| `buildServiceSchema({ name, description, geoSlug, … })`    | Page-specific delivery service                      |
| `buildSoftwareApplicationSchema()`                         | Platform / Lane A product                           |
| `buildFAQPageSchema(items)`                                | FAQ rich results (null if empty)                    |
| `buildArticleSchema({ headline, authorPerson, … })`        | Guides, success stories                             |
| `buildReviewSchema({ reviewBody, … })`                     | Permissioned testimonials                           |
| `buildBreadcrumbListSchema(items)`                         | Breadcrumb trail                                    |
| `buildSpeakableWebPageSchema({ name, url, cssSelectors })` | Voice / AEO                                         |

---

## Geographic constants

- `SCHEMA_SERVICE_AREAS` — 18 Ontario/GTA Place objects for `areaServed`
- `SCHEMA_AREA_SERVED_NAMES` — name-only fallback list
- `SCHEMA_DELIVERY_SERVICE_TYPES` — Courier, same-day, recurring, local, parcel

Hyperlocal pages pass `geoSlug` → `getHyperlocalGeo()` for Place + GeoCoordinates.

---

## Per-page schema usage

| Page / component                           | JSON-LD emitted                             |
| ------------------------------------------ | ------------------------------------------- |
| `[locale]/layout.tsx`                      | Organization, WebSite                       |
| `HomeDeliverySchema.tsx` (home)            | Organization, LocalBusiness                 |
| `[locale]/business/page.tsx`               | Service, FAQPage                            |
| `[locale]/industry/page.tsx`               | Service (hub)                               |
| `IndustryLandingView.tsx`                  | Service, FAQPage (when FAQ present)         |
| `CityIndustryLandingView.tsx`              | Service (hyperlocal), FAQPage               |
| `[locale]/service-areas/[slug]/page.tsx`   | Service, FAQPage                            |
| `ContentClusterView.tsx`                   | Service, FAQPage (FAQ/guides/compare shell) |
| `[locale]/success-stories/[slug]/page.tsx` | Article, Review (if permissioned)           |
| Platform / developers (select)             | SoftwareApplication                         |
| FAQ speakable pages                        | Speakable WebPage (where wired)             |
| Vehicle partner landing                    | FAQPage                                     |

### Pages typically **without** dedicated Service schema

- Legal: privacy, terms, cookies
- Login / auth
- Blog index (posts may get Article via post template)
- Track (utility — not a service landing)

---

## E-E-A-T fields in schema

| Field               | Where                                                      |
| ------------------- | ---------------------------------------------------------- |
| `authorPerson`      | `buildArticleSchema()` — Person with worksFor Organization |
| `publisher.logo`    | Article schema                                             |
| `knowsAbout`        | Organization — delivery verticals                          |
| `sameAs` / `hasMap` | LocalBusiness when GBP URLs configured                     |
| `Review`            | Success stories with `permissioned: true` only             |

Align with [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md) — no Review schema for unpermissioned quotes.

---

## Rendering

JSON-LD injected via shared `JsonLd` component (typically in `@/components/seo/JsonLd` or page-level). Multiple schemas passed as array where supported.

---

## Validation

Manual:

1. [Google Rich Results Test](https://search.google.com/test/rich-results) on sample URLs
2. GSC → Enhancements → FAQ, Organization

Automated: no dedicated JSON-LD unit tests yet — **Partial** coverage. Consider adding snapshot test for `buildOrganizationSchema()` output in future wave.

---

## Extension guidelines

1. Prefer reusing builders over inline JSON-LD in pages
2. Link entities via `@id` when adding new site-wide types
3. Use `buildServiceSchema()` for all delivery-capacity pages — keep `serviceType` aligned with `SCHEMA_DELIVERY_SERVICE_TYPES`
4. Do not add aggregateRating without verified third-party source
5. Update this map when adding new page types
