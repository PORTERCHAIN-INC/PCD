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

Prefer `common.cta.quote` = “Get a quote” and `common.cta.requestCapacity` = “Request capacity”. Do not invent demo / tour CTAs on customer paths.

## Lead wires

| Surface                  | Admin lead source        |
| ------------------------ | ------------------------ |
| `/contact` form          | `website_contact`        |
| Blog / footer newsletter | `website_newsletter`     |
| Vehicle partner form     | `website_driver_partner` |
| Capacity Guide chat      | guide ingest → CRM       |

## Chat / WhatsApp

- Capacity Guide FAB: all pages except home (inline) and auth
- WhatsApp FAB: phone browsers only, stacked above guide FAB

## Component kits (target)

`layout/` · `marketing/` (`MarketingHero`) · `seo/` · `blog/` · `magic/` · `motion/` · `personal/` (founder contact cards only — not product UI).

Hero imports: use `@/components/marketing/MarketingHero` (re-exports corporate `HeroSection`). Legacy `sections/HowItWorks` + `sections/FAQ` removed — canonical how-it-works is `/how-porterchain-works`; FAQ uses `FaqSection` + route FAQ data.

## Perf classes

See `website/src/lib/seo/perf-budget.ts` (`business` | `matrix` | `other`). Matrix pages: no Lottie / MagicCard in hero.

Motion budget: `MOTION_BUDGET` in `website/src/lib/motion.ts` — hero ≤2 moments; marketing LCP target 1.0s (`PERF_BUDGET_LCP_MARKETING_MS`).

## Blog media

Local disk by default (`BLOG_MEDIA_DIR`). Optional CDN + R2/S3:

- API CDN: `BLOG_MEDIA_PUBLIC_BASE_URL`
- Website: `NEXT_PUBLIC_BLOG_MEDIA_CDN` (match API CDN)
- S3/R2 (optional mirror on upload): `BLOG_MEDIA_S3_ENDPOINT`, `BLOG_MEDIA_S3_BUCKET`, `BLOG_MEDIA_S3_ACCESS_KEY_ID`, `BLOG_MEDIA_S3_SECRET_ACCESS_KEY`, `BLOG_MEDIA_S3_REGION=auto`, `BLOG_MEDIA_S3_PREFIX=blog-media`

Disk remains the local fallback; when S3 is configured, uploads PUT to the bucket and public URLs use `{CDN}/{prefix}/{file}`.

## SEO content trees

- `seo/content/` — draft expansions + niche/service-area message helpers
- `seo-content/` — industry/service-area configs, FAQ/CTA/onboarding generation registries (live niches only)  
  Do not invent a third tree. Draft niches stay noindex and out of sitemap / city×industry pairs.
