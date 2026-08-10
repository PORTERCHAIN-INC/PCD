# Website Gap Implementation Log

**Wave date:** 2026-07-22  
**Audit:** [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md](./PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md)  
**Deferred:** [DEFERRED_AND_OWNER_INPUT_REQUIRED.md](./DEFERRED_AND_OWNER_INPUT_REQUIRED.md)

---

## Summary

Authority/SEO implementation wave centralizing redirects, partitioning sitemaps, adding staging noindex, OG defaults, JSON-LD `@id` graph helpers, publishable content model, service intents, AI search assets (`llms.txt`, `AnswerBlock`), and documentation deliverables.

---

## 2026-07-22 — Changes

### Infrastructure / config

| File                               | Change                                                                     | Tag      |
| ---------------------------------- | -------------------------------------------------------------------------- | -------- |
| `website/src/lib/seo/redirects.ts` | **Added** — central redirect SSOT with typed entries + notes               | Existing |
| `website/next.config.ts`           | Redirects delegated to `toNextRedirects()`; removed inline redirect blocks | Existing |
| `website/src/app/sitemap.ts`       | Multi-sitemap via `generateSitemaps()` + partition id                      | Existing |
| `website/src/app/robots.ts`        | Lists sitemap index + 9 partition URLs                                     | Existing |

### Metadata / canonicalization

| File                                  | Change                                                                              | Tag      |
| ------------------------------------- | ----------------------------------------------------------------------------------- | -------- |
| `website/src/lib/seo/hreflang.ts`     | `defaultOpenGraphImages()`, staging `shouldIndexInEnvironment()`, Twitter/OG images | Existing |
| `website/src/app/opengraph-image.tsx` | **Added** — root OG image route (1200×630)                                          | Existing |
| `website/src/lib/seo/page-helpers.ts` | (existing) programmatic metadata helpers — referenced by wave page updates          | Existing |
| Multiple `[locale]/*/page.tsx`        | Migrated to shared metadata helpers (layout, hub pages, trust subpages)             | Existing |

### Sitemap / content gates

| File                                             | Change                                                                    | Tag      |
| ------------------------------------------------ | ------------------------------------------------------------------------- | -------- |
| `website/src/lib/seo/sitemap-entries.ts`         | Partition builders, FR programmatic gates, export `SITEMAP_PARTITION_IDS` | Existing |
| `website/src/lib/seo/content/publishable.ts`     | **Added** — `PublishableContent`, `isPublished()`                         | Existing |
| `website/src/lib/seo/content/service-intents.ts` | **Added** — intent → canonical route map                                  | Existing |
| `website/src/lib/seo/content/research.ts`        | **Added** — draft research scaffold (noindex)                             | Deferred |

### Structured data

| File                                  | Change                                                                                           | Tag      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ | -------- |
| `website/src/lib/seo/schema.ts`       | `@id` helpers (`organizationId`, `websiteId`, `serviceEntityId`), WebSite schema, publisher link | Partial  |
| `website/src/app/[locale]/layout.tsx` | Organization + WebSite JSON-LD on all locale pages                                               | Existing |

### AI search / AEO

| File                                                | Change                                                     | Tag      |
| --------------------------------------------------- | ---------------------------------------------------------- | -------- |
| `website/public/llms.txt`                           | **Added** — curated public URL index for AI systems        | Existing |
| `website/src/components/seo/AnswerBlock.tsx`        | **Added** — concise Q&A block component                    | Existing |
| `website/src/components/home/HomeAnswerSection.tsx` | Wired on homepage with EN/FR `corporate.home.answers` keys | Existing |
| `website/src/app/[locale]/not-found.tsx`            | **Added** — custom localized 404                           | Existing |
| `website/src/components/layout/SkipLink.tsx`        | **Added** — WCAG skip link → `#main-content`               | Existing |

### Trust / EEAT scaffolds (noindex)

| File                                                           | Change                               | Tag      |
| -------------------------------------------------------------- | ------------------------------------ | -------- |
| `website/src/components/trust/TrustScaffoldPage.tsx`           | Reusable noindex trust page scaffold | Existing |
| `website/src/app/[locale]/accessibility/page.tsx`              | Accessibility statement scaffold     | Deferred |
| `website/src/app/[locale]/trust/editorial-policy/page.tsx`     | Editorial policy scaffold            | Deferred |
| `website/src/app/[locale]/trust/research-methodology/page.tsx` | Research methodology scaffold        | Deferred |
| `website/src/app/[locale]/trust/corrections/page.tsx`          | Corrections policy scaffold          | Deferred |
| `website/src/app/[locale]/trust/security/page.tsx`             | Security overview scaffold           | Deferred |
| `website/src/app/[locale]/research/page.tsx`                   | Draft research hub (noindex)         | Deferred |

### Navigation / IA

| File                                    | Change                                                               | Tag      |
| --------------------------------------- | -------------------------------------------------------------------- | -------- |
| `website/src/data/navbar-navigation.ts` | Vehicles dropdown, Technology (`/platform`), Developers in Resources | Existing |
| `website/messages/corporate-en.json`    | `vehiclesMenu`, home answers, trust scaffold copy                    | Existing |
| `website/messages/corporate-fr.json`    | FR parity for nav, answers, trust scaffolds                          | Partial  |

### Content models / gap-fill

| File                                              | Change                                                     | Tag      |
| ------------------------------------------------- | ---------------------------------------------------------- | -------- |
| `website/src/lib/seo/content/success-stories.ts`  | Extended with `PublishableContent` + approval fields       | Existing |
| `website/src/lib/seo/content/comparison-pages.ts` | Added `same-day-vs-scheduled`, `cargo-van-vs-sprinter-van` | Partial  |
| `website/src/lib/seo/analytics.ts`                | Added phone/email click + page conversion events           | Partial  |

### CI / verify scripts

| File                                       | Change                                         | Tag      |
| ------------------------------------------ | ---------------------------------------------- | -------- |
| `package.json`                             | **Added** `validate:website-seo` script bundle | Existing |
| `.github/workflows/deploy-website.yml`     | Pre-build `validate:website-seo` + lint gates  | Existing |
| `scripts/verify_website_redirects.py`      | **Added**                                      | Existing |
| `scripts/verify_website_sitemap.py`        | **Added**                                      | Existing |
| `scripts/verify_website_robots.py`         | **Added**                                      | Existing |
| `scripts/verify_website_schema.py`         | **Added**                                      | Existing |
| `scripts/verify_website_internal_links.py` | **Added**                                      | Existing |
| `scripts/verify_llms_txt.py`               | **Added**                                      | Existing |
| `scripts/verify_website_a11y_smoke.py`     | **Added**                                      | Existing |
| `scripts/verify_website_seo_metadata.py`   | Extended index-page + OG image checks          | Existing |

### i18n / UX (collateral)

| File                                                | Change                               | Tag     |
| --------------------------------------------------- | ------------------------------------ | ------- |
| `website/messages/en.json`                          | Copy updates for SEO/portal surfaces | Partial |
| `website/messages/fr.json`                          | FR parity updates                    | Partial |
| `website/messages/corporate-en.json`                | Corporate copy additions             | Partial |
| `website/messages/corporate-fr.json`                | FR corporate copy                    | Partial |
| `website/src/app/[locale]/login/page.tsx`           | Login page updates                   | Partial |
| `website/src/components/portal/LoginBrandPanel.tsx` | Brand panel refresh                  | Partial |

### Documentation (this wave)

| File                                          | Status            |
| --------------------------------------------- | ----------------- |
| `docs/PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md` | Added             |
| `docs/SEO_AND_AI_SEARCH_ARCHITECTURE.md`      | Added             |
| `docs/CONTENT_MODEL_AND_TAXONOMY.md`          | Added             |
| `docs/STRUCTURED_DATA_MAP.md`                 | Added             |
| `docs/INTERNAL_LINKING_MAP.md`                | Added             |
| `docs/ANALYTICS_EVENT_TAXONOMY.md`            | Added             |
| `docs/CONTENT_EVIDENCE_POLICY.md`             | Added             |
| `docs/DEPLOYMENT_AND_INDEXING_CHECKLIST.md`   | Added             |
| `docs/WEBSITE_GAP_IMPLEMENTATION_LOG.md`      | Added (this file) |
| `docs/DEFERRED_AND_OWNER_INPUT_REQUIRED.md`   | Added             |

---

## Classification summary (wave)

| Tag      | Count (approx.)                                              |
| -------- | ------------------------------------------------------------ |
| Existing | 18 file changes shipped                                      |
| Partial  | FR parity, schema `@id` page adoption, layout migrations     |
| Missing  | Cookie CMP, phone/email click wiring in UI components        |
| Deferred | Research reports, legal trust scaffold sign-off before index |

---

## Verification run (2026-07-22)

Recommended commands after merge:

```bash
pnpm validate:website-seo
pnpm --filter @porterchain/website build
pnpm --filter @porterchain/website lint
pnpm validate:product-vision
```

| Gate                                       | Result               | Date       |
| ------------------------------------------ | -------------------- | ---------- |
| `pnpm validate:website-seo`                | PASS                 | 2026-07-22 |
| `pnpm --filter @porterchain/website build` | PASS                 | 2026-07-22 |
| `pnpm --filter @porterchain/website lint`  | PASS (warnings only) | 2026-07-22 |
| GSC sitemap resubmit                       | _pending_            |            |
| Bing Webmaster sitemap                     | _pending_            |            |

---

## Next wave candidates

1. Promote draft niches/boroughs to index after verified local copy
2. FR translations for new guides/comparisons (`seo-programmatic-fr.json`)
3. Interactive quote/vehicle calculators
4. Cookie consent CMP — legal input required
5. Expand AnswerBlock to business + top industry pages
6. Public status UI (`status.porterchain.com`) per STATUS_PAGE.md

Track deferrals in [DEFERRED_AND_OWNER_INPUT_REQUIRED.md](./DEFERRED_AND_OWNER_INPUT_REQUIRED.md).

---

## 2026-07-22 — Gap-close wave (pending + soft gaps)

| Area                | Change                                                                       |
| ------------------- | ---------------------------------------------------------------------------- |
| Conversion          | `TrackedContactLink`, contact hero phone/email events, `ContentViewBeacon`   |
| Guides              | 10 authority pages (5 gap-fill)                                              |
| Comparisons         | 9 comparison pages (3 gap-fill)                                              |
| Developer authority | `WEBHOOKS_IDEMPOTENCY_RATE_LIMITS.md` + developer-docs slug; verify extended |
| Draft expansion     | 5 draft niches + 6 draft service areas (noindex / non-CORE)                  |
| Schema              | HowTo, Corporation, Dataset builders; Service `@id`; guide HowTo emit        |
| Trust scaffolds     | founder, insurance, service-standards                                        |
| CI                  | deploy: developer-portal, prettier website, advisory audit                   |

### Verification

- [x] `pnpm validate:website-seo` PASS
- [x] `pnpm validate:developer-portal` PASS
- [x] `pnpm --filter @porterchain/website build` PASS

---

## Template for future entries

```markdown
## YYYY-MM-DD — {wave name}

### Summary

One paragraph.

| File   | Change      | Tag                                      |
| ------ | ----------- | ---------------------------------------- |
| `path` | description | Existing/Partial/Missing/Defect/Deferred |

### Verification

- [ ] gate commands
- [ ] GSC/Bing actions
```
