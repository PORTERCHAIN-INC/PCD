# Deployment and Indexing Checklist

**Scope:** Production website SEO/indexation  
**Audit:** [WEBSITE_SEO_STRATEGY.md](../WEBSITE_SEO_STRATEGY.md)  
**Architecture:** [SEO_AND_AI_SEARCH_ARCHITECTURE.md](./SEO_AND_AI_SEARCH_ARCHITECTURE.md)

---

## Pre-deploy gates

```bash
pnpm validate:website-seo
pnpm validate:developer-portal
pnpm --filter @porterchain/website lint
pnpm --filter @porterchain/website build
```

Deploy workflow (`.github/workflows/deploy-website.yml`) runs SEO + developer portal validation, lint, website prettier check, and advisory `pnpm audit --prod` before the Docker build.

---

## Public form security (contact / quote)

| Control          | Status                       | Notes                                                                                |
| ---------------- | ---------------------------- | ------------------------------------------------------------------------------------ |
| CSRF             | API / same-origin form posts | Public inquiry posts go through API routes — do not expose open CORS write endpoints |
| Rate limiting    | API-side                     | Burst abuse should hit API rate limits; monitor 429s on inquiry endpoints            |
| Spam / honeypot  | Partial                      | Prefer server-side validation + rate limits over client-only checks                  |
| PII minimization | Required                     | Collect only fields needed for a capacity quote                                      |
| Consent copy     | Present on forms             | Must stay aligned with `/privacy` and `/cookies`                                     |

Phone/email clicks fire `phone_click` / `email_click` via `TrackedContactLink` and contact hero `LinkButton` track events.

---

## Legacy command list (still valid)

```bash
# Metadata helpers on slug pages
python3 scripts/verify_website_seo_metadata.py

# Programmatic EN + publication gates
python3 scripts/verify_programmatic_en_playbook.py
python3 scripts/verify_w6b_industry_publication.py
python3 scripts/verify_city_local_segment_playbook.py
python3 scripts/verify_wave9_seo.py

# Marketing claims + SEO waves
python3 scripts/verify_marketing_claims.py

# Full product-vision suite (superset)
pnpm validate:product-vision

# Build
pnpm --filter @porterchain/website lint
pnpm --filter @porterchain/website build
```

Consider keeping `validate:website-seo` as the website deploy gate (already wired).

```json
"validate:website-seo": "python3 scripts/verify_website_seo_metadata.py && …"
```

### Additional recommended

```bash
pnpm validate:design          # i18n parity
pnpm validate:ai-governance   # no false AI marketing
```

---

## Environment variables

Set in Doppler / deploy workflow for production website:

| Variable                                         | Required    | SEO impact                                                                                |
| ------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_SITE_URL`                           | ✅          | `https://porterchain.com` — canonical base, schema `@id`, sitemap URLs                    |
| `NEXT_PUBLIC_APP_ENV`                            | ✅          | Must be `production` (not `staging`/`preview`) for index                                  |
| `NODE_ENV`                                       | ✅          | `production` at build                                                                     |
| GA4 measurement ID                               | ✅          | Analytics conversions                                                                     |
| GBP / social URLs                                | Recommended | Organization `sameAs`, LocalBusiness `hasMap`                                             |
| Zoho SalesIQ                                     | Optional    | Chat conversion events                                                                    |
| `NEXT_PUBLIC_GTM_ID`                             | Optional    | When set, marketing pixels should live in GTM (code skips direct Ads/Meta/LinkedIn/UET/X) |
| `NEXT_PUBLIC_GOOGLE_ADS_ID` / `_QUOTE_LABEL`     | Optional    | Ads conversion (consent + env)                                                            |
| `NEXT_PUBLIC_MICROSOFT_UET_ID`                   | Optional    | Microsoft Ads UET                                                                         |
| `NEXT_PUBLIC_LINKEDIN_PARTNER_ID`                | Optional    | LinkedIn Insight                                                                          |
| `NEXT_PUBLIC_META_PIXEL_ID`                      | Optional    | Meta Pixel                                                                                |
| `NEXT_PUBLIC_TWITTER_PIXEL_ID`                   | Optional    | X Pixel                                                                                   |
| `NEXT_PUBLIC_CLARITY_ID`                         | Optional    | Microsoft Clarity (experience category)                                                   |
| `NEXT_PUBLIC_HOTJAR_ID`                          | Optional    | Hotjar — skipped if Clarity set                                                           |
| `NEXT_PUBLIC_BING_SITE_VERIFICATION`             | Optional    | Bing meta verify                                                                          |
| `NEXT_PUBLIC_YANDEX_SITE_VERIFICATION`           | Optional    | Yandex meta verify                                                                        |
| `INDEXNOW_KEY`                                   | Optional    | IndexNow ping + `/api/marketing/indexnow-key`                                             |
| `META_CAPI_ACCESS_TOKEN` / `LINKEDIN_CAPI_TOKEN` | Optional    | Server CAPI stubs                                                                         |
| `MARKETING_EVENT_WEBHOOK_URL`                    | Optional    | CRM/Zapier conversion mirror                                                              |

CMP: first-party banner + Google Consent Mode v2 ships default-denied. Enable marketing cookies in production only after Legal sign-off.

**Staging/preview:** `NEXT_PUBLIC_APP_ENV=staging` forces `noindex` via `hreflang.ts` — verify before sharing preview URLs.

Source: `@porterchain/config/monorepo-env.mjs` → `websitePublicEnv()`.

---

## Build and deploy

```bash
pnpm --filter @porterchain/website build
```

Deploy via `.github/workflows/deploy-website.yml` (or current prod pipeline).

Post-deploy smoke:

```bash
curl -sI https://porterchain.com/robots.txt
curl -s https://porterchain.com/sitemap.xml | head
curl -sI https://porterchain.com/en/business | grep -i x-robots
```

---

## Google Search Console

### Property

- **Domain property:** `porterchain.com` (preferred)
- Apex canonical — `www` redirects to apex via Caddy

### Sitemap submission

Submit sitemap index (includes all partitions via robots):

```
https://porterchain.com/sitemap.xml
```

Optional: verify each partition resolves:

- `/sitemap/static.xml`
- `/sitemap/industry.xml`
- `/sitemap/service.xml`
- `/sitemap/vehicle.xml`
- `/sitemap/location.xml`
- `/sitemap/resource.xml`
- `/sitemap/article.xml`
- `/sitemap/case-study.xml`
- `/sitemap/developer.xml`

After partition wave deploy: **Resubmit** sitemap index in GSC (same URL — Google re-fetches child sitemaps).

### URL inspection

Sample URLs after deploy:

- `/en/` — Organization + WebSite schema
- `/en/business` — Service + FAQ
- `/en/industry/construction-materials` — industry template
- `/en/toronto/construction-materials-delivery` — matrix page
- `/en/compare/in-house-delivery` — compare cluster

Check: “URL is on Google”, valid canonical, no unintended noindex.

---

## Bing Webmaster Tools

1. Add site `https://porterchain.com`
2. Verify via DNS or GSC import
3. Submit same sitemap: `https://porterchain.com/sitemap.xml`
4. Enable IndexNow if configured in future wave

---

## Indexing policy checks

| Check                  | Expected                                     |
| ---------------------- | -------------------------------------------- |
| Production robots meta | `index, follow` on public hubs               |
| Staging                | `noindex, follow`                            |
| `/robots.txt` disallow | `/api/`, login, book continue/success, track |
| `/llms.txt`            | 200 at root                                  |
| Legacy `/ca/en/*`      | 301 to `/en/*`                               |

---

## CDN / cache

Invalidate or wait for TTL after deploy:

- `/robots.txt`
- `/sitemap.xml` and `/sitemap/*.xml`
- `/llms.txt`
- `/opengraph-image`

`next.config.ts` sets `Cache-Control` on sitemap and robots.

---

## Analytics post-deploy

1. GA4 Realtime — confirm page views on prod
2. Trigger `contact_form_submit_success` on test submission (test property or filtered)
3. Confirm conversion events marked in GA4 Admin match [ANALYTICS_EVENT_TAXONOMY.md](./ANALYTICS_EVENT_TAXONOMY.md)
4. Verify `web_vital` events arriving within 24h

---

## Rollback

See [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md Appendix B](../WEBSITE_SEO_STRATEGY.md#b-rollback-procedure).

---

## 30-day monitoring

See [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md Appendix D](../WEBSITE_SEO_STRATEGY.md#d-post-deploy-monitoring-30-days).

---

## Sign-off

| Step                                     | Owner       | Done |
| ---------------------------------------- | ----------- | ---- |
| CI green (`validate:website-seo` subset) | Engineering | ☐    |
| Prod env vars verified                   | DevOps      | ☐    |
| GSC sitemap submitted                    | Growth/SEO  | ☐    |
| Bing sitemap submitted                   | Growth/SEO  | ☐    |
| Sample URL inspection pass               | Growth/SEO  | ☐    |
| GA4 conversions marked                   | Growth      | ☐    |
| Manual checklist (audit Appendix C)      | QA          | ☐    |

Log completion date in [WEBSITE_GTM_EXECUTION_PLAN.md](../WEBSITE_GTM_EXECUTION_PLAN.md).
