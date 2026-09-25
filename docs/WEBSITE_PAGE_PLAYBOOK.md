# Website page playbook

**Type:** execution SSOT for website organisation · **Updated:** 2026-09-24

Use this before adding pages or rewriting copy. Charter: [PORTERCHAIN_CHARTER.md](PORTERCHAIN_CHARTER.md).

## Template families

| Family       | Job                     | Max sections         | Motion        | Example routes                                       |
| ------------ | ----------------------- | -------------------- | ------------- | ---------------------------------------------------- |
| `hub`        | Brand + choose path     | 6                    | hero + reveal | `/`, `/business`, `/solutions`                       |
| `landing`    | One vertical / product  | 6                    | reveal        | `/enterprise`, `/local-delivery`, `/vehicle-partner` |
| `seo-matrix` | Programmatic city×niche | template only        | none/light    | `/industry/*`, city industry, service-areas          |
| `editorial`  | Blog reading            | hub + article chrome | none          | `/blog`, `/blog/[slug]`, authors                     |
| `legal`      | Trust / policy          | scaffold             | none          | `/trust/*`, privacy, terms                           |
| `utility`    | Convert / auth / track  | minimal              | none          | `/quote`→sign-up, `/track`, `/contact`, sign-in      |

## Section grammar (hub + landing)

1. Hero — brand + one headline + one support + CTA group + one visual
2. Problem / proof — one job
3. How capacity works — one job
4. Niche or fleet — only if needed
5. Trust / FAQ — one job
6. Closer CTA — quote / request capacity

No duplicate same-day / POD / overflow line after the hero already said it.

## Message ownership

| Namespace        | File                                          | Owns                                                     |
| ---------------- | --------------------------------------------- | -------------------------------------------------------- |
| root             | `messages/{locale}.json`                      | home, nav chrome, shared product trust, **`common.cta`** |
| `businessPage`   | `business-{locale}.json`                      | `/business` only                                         |
| `corporate`      | `corporate-{locale}.json`                     | company, contact, careers shells                         |
| `blog`           | `blog-{locale}.json`                          | blog chrome (not post body)                              |
| `siteFooter`     | `site-footer-{locale}.json`                   | footer                                                   |
| `legal`          | `legal-{locale}.json`                         | legal copy                                               |
| `vehiclePartner` | `vehicle-partner-{locale}.json`               | vehicle-partner landing                                  |
| SEO TS           | `website/src/lib/seo/content` + `seo-content` | programmatic bodies                                      |

Blog **bodies** live in Postgres via admin CMS (`content_engine.BlogService`), not messages JSON.

## CTA lexicon (single source)

**Done.** Customer quote/capacity buttons use `common.cta` via `useTranslations` / `getTranslations`, or `quoteCtaLabel` / `QUOTE_CTA` from `website/src/lib/cta.ts` for non-i18n SEO modules.

- `common.cta.quote` = “Get a quote” / FR “Obtenir une soumission”
- `common.cta.requestCapacity` = “Request capacity” / FR “Demander de la capacité”

Do not invent demo / tour CTAs on customer paths. Careers, trust (non-claims), and vehicle-partner keep role-specific labels.

## Component kits

**Done.** Top-level kits under `website/src/components/`:

`layout/` · `marketing/` (incl. `MarketingHero`, `MarketingCloser`, home/business/corporate/solutions/…) · `seo/` · `blog/` · `magic/` · `motion/` · `personal/` · `ui/` · `maps/` · `portal/` · `providers/` (+ `i18n/` · `integrations/`).

Canonical imports:

- `@/components/marketing/MarketingHero` — default = link/CTA hero (`HeroSection`); named = `BusinessQuoteHero`, `VehiclePartnerHero`, `CareersHero`, `ContactHero`
- `@/components/marketing/MarketingCloser` — default = `CtaSection`; named = `BusinessQuoteCloser`, `BusinessStickyCloser`, `CareersCloser`
- `@/components/marketing/MarketingProof` — ProductTrust, HubTrustStrip, TrustScaffold, TrustDocuments, WhyChoose, TrustedBy
- `@/components/marketing/MarketingFaq` — default FaqSection; named `BusinessFaq`

Dead home `marketing/sections/*` dump removed (only `Hero` + `HeroCopy` remain for home fleet layout).

## Perf classes

See `website/src/lib/seo/perf-budget.ts` (`business` | `matrix` | `other`). Matrix pages: no Lottie / MagicCard in hero.

Motion budget: `MOTION_BUDGET` in `website/src/lib/motion.ts` — hero ≤2 moments; marketing LCP target 1.0s (`PERF_BUDGET_LCP_MARKETING_MS`).

## Blog media

**Code complete.** Local disk by default (`BLOG_MEDIA_DIR`). Optional CDN + R2/S3 wired in API (`blog_media_s3.py`) + Doppler upload script (`infrastructure/deploy/scripts/upload-blog-to-doppler.sh`).

- API CDN: `BLOG_MEDIA_PUBLIC_BASE_URL`
- Website: `NEXT_PUBLIC_BLOG_MEDIA_CDN` (match API CDN)
- S3/R2 (optional mirror on upload): `BLOG_MEDIA_S3_ENDPOINT`, `BLOG_MEDIA_S3_BUCKET`, `BLOG_MEDIA_S3_ACCESS_KEY_ID`, `BLOG_MEDIA_S3_SECRET_ACCESS_KEY`, `BLOG_MEDIA_S3_REGION=auto`, `BLOG_MEDIA_S3_PREFIX=blog-media`

Disk remains the local fallback; when S3 is configured, uploads PUT to the bucket and public URLs use `{CDN}/{prefix}/{file}`.

**Ops (bucket credentials only):** create Cloudflare R2 (or S3) bucket, set the Doppler `pcd/prd` keys above, re-run the upload script. Empty placeholders are intentional until the bucket exists.

## SEO content trees

**Done — ownership locked** in `website/src/lib/seo/OWNERSHIP.ts`:

- `seo-content/` — programmatic registries (KEYWORDS, industries, service-areas, campaigns, variants)
- `seo/content/` — editorial longform (authority, compare, capabilities, FAQ clusters, research, drafts)

Do not invent a third tree. Draft niches stay noindex and out of sitemap / city×industry pairs.

## Blog authors

**Done.** Postgres `blog_authors` (admin CRUD + public list) seeded from `@porterchain/types` `BLOG_AUTHORS`. Website prefers `/v1/public/blog/authors` with static fallback. Ids must match `BlogPost.author_id`.

## Scheduled publish

**Done.** Drafts may set `scheduled_publish_at`. Worker queue mode drains due posts every ~60s (`publish_due_posts` → status published + website revalidate).

## Draft preview

**Done.** Admin `GET /v1/admin/blog/posts/{id}/preview-url` issues HMAC token (uses `WEBSITE_REVALIDATE_SECRET`). Website `/[locale]/blog/preview/[slug]?token=` loads via public preview API. Noindex. Requires secret set in API + Doppler.
