# PorterChain Website Authority Audit

**Date:** 2026-07-22  
**Scope:** `website/` marketing site — SEO, authority, AI-search readiness, conversion instrumentation  
**Related docs:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md) · [STRUCTURED_DATA_MAP.md](./STRUCTURED_DATA_MAP.md) · [CONTENT_MODEL_AND_TAXONOMY.md](./CONTENT_MODEL_AND_TAXONOMY.md) · [DEPLOYMENT_AND_INDEXING_CHECKLIST.md](./DEPLOYMENT_AND_INDEXING_CHECKLIST.md) · [WEBSITE_GAP_IMPLEMENTATION_LOG.md](./WEBSITE_GAP_IMPLEMENTATION_LOG.md)

---

## 1. Executive summary

PorterChain runs a **dual-lane** public website: Lane A (platform / capacity network positioning) and Lane B (programmatic industry × city × vehicle SEO). The July 2026 authority wave centralizes redirects, partitions sitemaps, adds staging noindex guards, OG image defaults, `@id` JSON-LD graph nodes, `PublishableContent` gates, service-intent routing, `llms.txt`, and `AnswerBlock` for AEO.

| Area                                | Status              | Notes                                                                     |
| ----------------------------------- | ------------------- | ------------------------------------------------------------------------- |
| Metadata / hreflang                 | **Existing**        | `website/src/lib/seo/hreflang.ts`, `page-helpers.ts`                      |
| Sitemap partitions                  | **Existing** (wave) | 9 partitions via `generateSitemaps()`                                     |
| Redirects SSOT                      | **Existing** (wave) | `website/src/lib/seo/redirects.ts`                                        |
| Structured data graph               | **Partial**         | `#organization`, `#website` live; `#service` typed, page adoption partial |
| FR programmatic parity              | **Partial**         | `messages/seo-programmatic-fr.json` gate                                  |
| Research / benchmarks               | **Deferred**        | `content/research.ts` draft-only                                          |
| Cookie consent banner               | **Missing**         | `/cookies` page exists; no CMP                                            |
| `validate:website-seo` script alias | **Partial**         | Gates exist under `validate:product-vision`                               |

**Primary CTA:** get a quote / request capacity (`/contact?intent=quote`, `/business`) — not demo-first.

---

## 2. Discovery inventory

### 2.1 SEO module (`website/src/lib/seo/`)

| Path                   | Role                                                 |
| ---------------------- | ---------------------------------------------------- |
| `config.ts`            | `siteConfig`, locale helpers                         |
| `hreflang.ts`          | Canonical, alternates, OG/Twitter, staging noindex   |
| `redirects.ts`         | Central redirect registry → `next.config.ts`         |
| `sitemap-entries.ts`   | Partition builders + publication gates               |
| `schema.ts`            | JSON-LD types and builders                           |
| `routes.ts`            | Locale path helpers                                  |
| `page-helpers.ts`      | `buildPageMetadata`, `buildProgrammaticPageMetadata` |
| `internal-linking.ts`  | Hub links, city/industry curation                    |
| `analytics.ts`         | Event taxonomy + GA4 conversion list                 |
| `attribution.ts`       | UTM / `from=` session attribution                    |
| `content/*`            | Publishable models, intents, comparisons, guides     |
| `perf-budget.ts`       | CWV RUM thresholds                                   |
| `web-vitals-report.ts` | Client RUM → analytics                               |

### 2.2 App routes

- Pages: `website/src/app/[locale]/`
- Sitemap: `website/src/app/sitemap.ts`
- Robots: `website/src/app/robots.ts`
- OG image: `website/src/app/opengraph-image.tsx`
- AI index: `website/public/llms.txt`

### 2.3 IA data

- Navbar: `website/src/data/navbar-navigation.ts`
- Footer: `website/src/data/footer-navigation.ts`

### 2.4 i18n

- UI: `website/messages/en.json`, `fr.json`
- Programmatic FR: `website/messages/seo-programmatic-fr.json`
- Blog: `website/content/blog/{en,fr}/`

---

## 3. Metadata

**Implementation:** `buildSeoMetadata()` in `hreflang.ts` is the single metadata builder.

| Field                   | Source                                                   | Status                            |
| ----------------------- | -------------------------------------------------------- | --------------------------------- |
| `title` / `description` | Per-page `generateMetadata`                              | Existing                          |
| `metadataBase`          | `siteConfig.baseUrl` from `config.ts`                    | Existing                          |
| `alternates.canonical`  | `buildCanonicalPath()`                                   | Existing                          |
| `alternates.languages`  | `buildAlternateLanguages()` — `en`, `fr-CA`, `x-default` | Existing                          |
| Open Graph              | type, locale (`en_CA` / `fr_CA`), images                 | Existing (wave: default OG route) |
| Twitter                 | `summary_large_image`                                    | Existing (wave)                   |
| `robots.index`          | Content flag **and** environment guard                   | Existing (wave)                   |

Programmatic pages use `buildProgrammaticPageMetadata()` — index only when localized body exists (`locale === "en" || localized`).

**Defect watch:** Slug pages must use helpers — enforced by `scripts/verify_website_seo_metadata.py`.

See [SEO_AND_AI_SEARCH_ARCHITECTURE.md § Metadata](./SEO_AND_AI_SEARCH_ARCHITECTURE.md#metadata-and-canonicalization).

---

## 4. Canonicalization

| Rule              | Implementation                                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Locale prefix     | `/en/...`, `/fr/...` via `localePath()` in `routes.ts`                                                                                    |
| Trailing slash    | Consistent path segments (no trailing slash in builders)                                                                                  |
| Duplicate routes  | Service intents map to existing hubs — [CONTENT_MODEL_AND_TAXONOMY.md § Service intents](./CONTENT_MODEL_AND_TAXONOMY.md#service-intents) |
| Legacy URLs       | 301 via `WEBSITE_REDIRECTS` — [§6 Redirects](#6-redirects)                                                                                |
| `canonicalSlug`   | Optional on `PublishableContent` for alias slugs                                                                                          |
| Staging / preview | `shouldIndexInEnvironment()` forces `noindex` when `NEXT_PUBLIC_APP_ENV` is `staging` or `preview`                                        |

---

## 5. Sitemap and robots

### Sitemap

- **Index:** `/sitemap.xml` (Next.js sitemap index from `generateSitemaps()`)
- **Partitions:** `static`, `industry`, `service`, `vehicle`, `location`, `resource`, `article`, `case-study`, `developer`
- **Builder:** `website/src/lib/seo/sitemap-entries.ts`
- **Route:** `website/src/app/sitemap.ts` — `force-static`, `revalidate: 86400`

Publication gates (FR niche, service area, city segment, vehicle) mirror metadata index rules.

### Robots

- **File:** `website/src/app/robots.ts`
- **Allow:** `/`
- **Disallow:** `/api/`, `/*/login`, `/*/book/continue`, `/*/book/success`, `/*/track/`
- **Sitemaps:** Index + all 9 partition URLs

Detail: [SEO_AND_AI_SEARCH_ARCHITECTURE.md § Sitemap partitions](./SEO_AND_AI_SEARCH_ARCHITECTURE.md#sitemap-partitions).

---

## 6. Redirects

**SSOT:** `website/src/lib/seo/redirects.ts` → `toNextRedirects()` consumed by `website/next.config.ts`.

| Group                | Example                                                          | Type |
| -------------------- | ---------------------------------------------------------------- | ---- |
| Legacy market prefix | `/ca/en/*` → `/en/*`                                             | 301  |
| Retired corporate    | `/en/overview` → `/en/business`                                  | 301  |
| Guide consolidation  | `/en/guides/how-porterchain-works` → `/en/how-porterchain-works` | 301  |
| Vehicle slug rename  | `/en/van-delivery` → `/en/trade-van-delivery`                    | 301  |
| Education hub        | `/en/onboarding-education` → `/en/guides`                        | 301  |

Each entry supports optional `note` for audit trail.

---

## 7. Structured data

**Module:** `website/src/lib/seo/schema.ts`

| Schema                          | `@id` / usage                                        |
| ------------------------------- | ---------------------------------------------------- |
| Organization                    | `#organization` — root layout                        |
| WebSite                         | `#website` — root layout, links to publisher         |
| LocalBusiness + DeliveryService | `#localbusiness` — home via `HomeDeliverySchema.tsx` |
| Service                         | Per-page (no global `@id` yet)                       |
| FAQPage                         | FAQ clusters, industry, business pages               |
| Article / Review                | Success stories (permissioned)                       |
| Speakable WebPage               | Voice / AEO selectors                                |
| SoftwareApplication             | Platform lane                                        |

Full map: [STRUCTURED_DATA_MAP.md](./STRUCTURED_DATA_MAP.md).

---

## 8. Content architecture

Dual-lane model documented in [CONTENT_MODEL_AND_TAXONOMY.md](./CONTENT_MODEL_AND_TAXONOMY.md):

- **Hub pages:** `/business`, `/local-delivery`, `/industry`, `/service-areas`, `/platform`, `/solutions`
- **Matrix pages:** `/{city}/{industry-or-vehicle}` — gated by `city-segment-publication.ts`, `vehicle-publication.ts`
- **Resource clusters:** FAQ, guides, compare, success stories, blog
- **Service intents:** Mapped to canonical routes — no duplicate `/services/*` tree

Internal linking policy: [INTERNAL_LINKING_MAP.md](./INTERNAL_LINKING_MAP.md).

---

## 9. E-E-A-T and trust

| Signal             | Status   | Path / note                                                                                        |
| ------------------ | -------- | -------------------------------------------------------------------------------------------------- |
| Company / contact  | Existing | `/company`, `/contact`                                                                             |
| Trust center       | Partial  | `/trust`, `/trust/sla`, `/trust/dpa`, `/trust/msa`, `/trust/subprocessors` — legal review required |
| Success stories    | Partial  | `content/success-stories.ts` — `permissioned` flag for metrics                                     |
| Research reports   | Deferred | `content/research.ts` — draft, noindex                                                             |
| Author attribution | Partial  | `authorId` on publishable types; blog authors                                                      |
| GBP / sameAs       | Existing | `buildGoogleSameAsLinks()` when env configured                                                     |
| Evidence policy    | Existing | [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md)                                         |

---

## 10. Conversion

| Surface             | CTA                     | Analytics event                             |
| ------------------- | ----------------------- | ------------------------------------------- |
| Navbar              | `/contact?intent=quote` | `cta_click`                                 |
| Business page       | Inquiry form            | `business_inquiry_submit`                   |
| Contact             | Form                    | `contact_form_submit_success`               |
| Booking widget      | Quote flow              | `booking_quote_success`, `booking_continue` |
| SEO bridge (Lane B) | Platform link           | `seo_bridge_click`                          |
| WhatsApp / Zoho     | Chat                    | `whatsapp_chat_click`, `zoho_chat_open`     |

Taxonomy: [ANALYTICS_EVENT_TAXONOMY.md](./ANALYTICS_EVENT_TAXONOMY.md).

---

## 11. Local SEO

| Element            | Implementation                                     |
| ------------------ | -------------------------------------------------- |
| Service area pages | `service-areas/[slug]` + `service-area-content.ts` |
| City × industry    | `[city]/[industrySlug]` + hyperlocal geo in schema |
| Schema areaServed  | `SCHEMA_SERVICE_AREAS` in `schema.ts`              |
| GBP links          | `GoogleBusinessProfileLink.tsx`                    |
| Primary cities     | `PRIMARY_CITY_SLUGS` in `internal-linking.ts`      |
| FR service areas   | Index/sitemap skipped for `/fr/service-areas` hub  |

---

## 12. Analytics

- **Events:** `website/src/lib/seo/analytics.ts` — `ANALYTICS_EVENTS`
- **Attribution:** `attribution.ts` — sessionStorage, UTM, `from=`
- **Conversions:** `GA4_CONVERSION_EVENTS` — mark in GA4 Admin
- **RUM:** `web-vitals-report.ts` + `perf-budget.ts` → `web_vital`, `web_vital_budget_exceeded`

---

## 13. Performance

| Control        | Location                                                 |
| -------------- | -------------------------------------------------------- |
| CWV budgets    | `perf-budget.ts` — LCP 2500 ms, INP 200/500 ms, CLS 0.1  |
| Route classes  | `business`, `matrix`, `other` for budget context         |
| Image formats  | `next.config.ts` — AVIF/WebP                             |
| Sitemap cache  | `Cache-Control` headers on `/sitemap.xml`, `/robots.txt` |
| Static sitemap | `force-static` + 24h revalidate                          |

---

## 14. Accessibility

| Area          | Status                                                                  |
| ------------- | ----------------------------------------------------------------------- |
| Booking a11y  | `pnpm validate:booking-a11y`                                            |
| AnswerBlock   | Semantic `<dl>` — `AnswerBlock.tsx`                                     |
| Navbar        | `aria-label` on nav, mobile menu                                        |
| Speakable FAQ | CSS selectors for voice search — `.speakable-faq-q`, `.speakable-faq-a` |
| Login page    | Wave updates to `LoginBrandPanel.tsx`                                   |

---

## 15. Security

From `website/next.config.ts`:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- Robots disallow on auth/booking paths
- Staging noindex prevents preview leakage

---

## 16. AI search (GEO / AEO / llms.txt)

| Asset            | Path                                         | Purpose                            |
| ---------------- | -------------------------------------------- | ---------------------------------- |
| `llms.txt`       | `website/public/llms.txt`                    | Curated URL index for AI crawlers  |
| `AnswerBlock`    | `website/src/components/seo/AnswerBlock.tsx` | Direct Q&A on money pages          |
| Speakable schema | `buildSpeakableWebPageSchema()`              | Voice / snippet targeting          |
| FAQ schema       | `buildFAQPageSchema()`                       | Rich results where full FAQ exists |

Architecture detail: [SEO_AND_AI_SEARCH_ARCHITECTURE.md § AI search](./SEO_AND_AI_SEARCH_ARCHITECTURE.md#ai-search-geo--aeo).

---

## 17. Content gaps

| Gap                                           | Priority | Owner                                                                                  |
| --------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| FR programmatic parity (compare, FAQ, guides) | P1       | Content + i18n                                                                         |
| Research benchmark report                     | P2       | Ops data + founder approval                                                            |
| Cookie consent CMP                            | P1       | Legal — [DEFERRED_AND_OWNER_INPUT_REQUIRED.md](./DEFERRED_AND_OWNER_INPUT_REQUIRED.md) |
| Trust page legal copy                         | P0       | Legal                                                                                  |
| `#service` graph `@id` on all service pages   | P2       | Engineering                                                                            |
| Dedicated service-intent landing pages        | P3       | IA review before new routes                                                            |

---

## 18. CI and testing

### Recommended gate: `validate:website-seo`

Composite command (documented target; today run via `validate:product-vision` subset):

```bash
python3 scripts/verify_website_seo_metadata.py
python3 scripts/verify_programmatic_en_playbook.py
python3 scripts/verify_wave9_seo.py
python3 scripts/verify_w6b_industry_publication.py
python3 scripts/verify_city_local_segment_playbook.py
pnpm --filter @porterchain/website build
```

Also relevant: `validate:design` (i18n parity), `validate:marketing-claims`, `verify_no_false_ai_marketing.py`.

Pre-deploy: [DEPLOYMENT_AND_INDEXING_CHECKLIST.md](./DEPLOYMENT_AND_INDEXING_CHECKLIST.md).

---

## 19. Classification tags

Use these tags in audit tables and PR descriptions:

| Tag          | Meaning                                     |
| ------------ | ------------------------------------------- |
| **Existing** | Shipped and verified in repo                |
| **Partial**  | Implemented but incomplete or env-dependent |
| **Missing**  | Not implemented; gap documented             |
| **Defect**   | Implemented incorrectly; needs fix          |
| **Deferred** | Intentionally postponed; owner assigned     |

---

## 20. Coverage matrix

| Capability         | EN       | FR    | Sitemap    | Schema         | Index gate                   | Tag      |
| ------------------ | -------- | ----- | ---------- | -------------- | ---------------------------- | -------- |
| Static hubs        | ✅       | ✅    | static     | Org/WebSite    | env + page                   | Existing |
| Industry niches    | ✅       | gated | industry   | Service+FAQ    | `isPublishableNiche`         | Partial  |
| Service areas      | ✅       | gated | location   | Service+FAQ    | `isPublishableServiceArea`   | Partial  |
| City × segment     | ✅       | gated | location   | Service        | `isPublishableCitySegment`   | Partial  |
| Vehicles           | ✅       | gated | vehicle    | Service        | `shouldIndexVehicleRoute`    | Partial  |
| FAQ clusters       | ✅       | gated | resource   | FAQPage        | FR slug in programmatic JSON | Partial  |
| Guides             | ✅       | gated | resource   | Article        | FR slug gate                 | Partial  |
| Compare            | ✅       | gated | resource   | —              | FR slug gate                 | Partial  |
| Success stories    | ✅       | gated | case-study | Article+Review | permissioned metrics         | Partial  |
| Blog               | ✅       | ✅    | article    | —              | published posts              | Existing |
| Developers docs    | ✅       | ✅    | developer  | —              | always                       | Existing |
| Research           | scaffold | —     | —          | —              | draft/noindex                | Deferred |
| llms.txt           | ✅       | links | —          | —              | n/a                          | Existing |
| Staging noindex    | ✅       | ✅    | —          | —              | env guard                    | Existing |
| Redirects SSOT     | ✅       | ✅    | —          | —              | n/a                          | Existing |
| Partition sitemaps | ✅       | —     | all        | —              | n/a                          | Existing |
| Cookie CMP         | —        | —     | —          | —              | n/a                          | Missing  |

---

## Appendices

### A. Changed-files template

Use for each implementation wave PR:

```markdown
## SEO / authority wave — changed files

| File                                     | Change type | Audit section |
| ---------------------------------------- | ----------- | ------------- |
| `website/src/lib/seo/redirects.ts`       | Added       | §6            |
| `website/src/lib/seo/sitemap-entries.ts` | Modified    | §5            |
| ...                                      | ...         | ...           |

## Classification summary

- Existing: N
- Partial: N
- Missing: N
- Deferred: N
```

Current wave log: [WEBSITE_GAP_IMPLEMENTATION_LOG.md](./WEBSITE_GAP_IMPLEMENTATION_LOG.md).

### B. Rollback procedure

1. Revert the deployment commit or roll back the website image/tag in deploy workflow.
2. Restore `next.config.ts` redirects if `redirects.ts` caused routing issues — inline redirects were removed in favor of SSOT.
3. Resubmit prior sitemap in GSC if partition URLs cause crawl errors (unlikely — index still exposes `/sitemap.xml`).
4. Clear CDN cache for `/sitemap.xml`, `/robots.txt`, `/llms.txt`.
5. Verify `NEXT_PUBLIC_APP_ENV=production` on prod so noindex guard is not active.

### C. Manual verification checklist

- [ ] `curl -sI https://porterchain.com/robots.txt` — lists index + 9 partitions
- [ ] `curl -s https://porterchain.com/sitemap.xml` — valid sitemap index
- [ ] Sample partition: `/sitemap/static.xml`, `/sitemap/location.xml`
- [ ] Legacy redirect: `/ca/en/business` → `/en/business` (301)
- [ ] Vehicle redirect: `/en/van-delivery` → `/en/trade-van-delivery`
- [ ] Canonical on `/en/industry/construction-materials` matches locale path
- [ ] hreflang alternates present (`en`, `fr-CA`, `x-default`)
- [ ] OG image: `/opengraph-image` returns 1200×630 PNG
- [ ] `/llms.txt` served at root
- [ ] Staging host returns `noindex` in page robots meta
- [ ] JSON-LD `@id` for Organization and WebSite on homepage
- [ ] GSC URL inspection — no duplicate canonical errors on sample matrix URL

### D. Post-deploy monitoring (30 days)

| Signal          | Tool                  | Action threshold                                    |
| --------------- | --------------------- | --------------------------------------------------- |
| Index coverage  | GSC                   | >5% drop in indexed pages                           |
| Crawl errors    | GSC                   | New 404s on redirected slugs                        |
| Core Web Vitals | GA4 `web_vital`       | INP poor >25% on `matrix` routes                    |
| Conversions     | GA4                   | `quote_request`, `business_inquiry_submit` baseline |
| Rich results    | GSC Enhancements      | FAQ/Organization regressions                        |
| Staging leakage | `site:staging` search | Any indexed staging URL → fix env                   |

### E. Completion report template (10 sections)

1. **Executive summary** — scope, dates, overall readiness score
2. **Shipped changes** — link to implementation log
3. **Coverage matrix delta** — tags before/after
4. **Indexation status** — GSC indexed count, sitemap submitted
5. **Structured data** — rich result status
6. **Content / E-E-A-T** — published vs deferred
7. **Conversion / analytics** — events firing, GA4 conversions marked
8. **Performance** — CWV field data snapshot
9. **Open gaps** — link to DEFERRED doc
10. **Sign-off** — engineering, content, legal (if trust pages touched)

### F. Database migrations

**N/A** — website SEO authority work is static Next.js content and metadata only. No Postgres schema changes.

---

**Maintainers:** Update this audit after each SEO wave. Cross-check with [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md) for strategic context; this doc is the operational audit SSOT.
